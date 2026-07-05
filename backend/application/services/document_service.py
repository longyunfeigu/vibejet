# input: DocumentUnitOfWork, DocumentParserPort, StoragePort, Document/FileAsset 领域实体
# output: DocumentApplicationService 文档解析生命周期编排
# pos: 应用层服务 - 文档建档/异步解析/查询/重解析编排（外部 I/O 在事务外执行）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Application layer orchestration for the document parse lifecycle.

``process_document`` is the async worker entry point. It is transport-agnostic:
the API layer schedules it via FastAPI ``BackgroundTasks`` today, and a Celery
task can call the same method unchanged. External I/O (storage download, parser
call) deliberately happens OUTSIDE any DB transaction; state transitions are
persisted in two short transactions before and after the slow work.
"""

from __future__ import annotations

from typing import Callable, Optional, Protocol, Tuple

from application.dto import CreateDocumentDTO, DocumentContentDTO, DocumentDTO
from application.ports.document_parser import DocumentParserError, DocumentParserPort
from application.ports.storage import StoragePort
from application.utils.time import utcnow
from core.config import settings
from core.logging_config import get_logger
from domain.document import (
    Document,
    DocumentNotFoundException,
    DocumentNotReadyException,
)
from domain.document.repository import DocumentRepository
from domain.common.exceptions import (
    DomainValidationException,
    FileAssetNotFoundException,
    FileTooLargeException,
)
from domain.file_asset.repository import FileAssetRepository

logger = get_logger(__name__)


class DocumentUnitOfWork(Protocol):
    @property
    def document_repository(self) -> DocumentRepository: ...

    @property
    def file_asset_repository(self) -> FileAssetRepository: ...

    async def __aenter__(self) -> "DocumentUnitOfWork": ...

    async def __aexit__(self, exc_type, exc, tb) -> None: ...

    async def commit(self) -> None: ...


class DocumentApplicationService:
    """High-level document workflows bridging API and domain layers."""

    def __init__(
        self,
        uow_factory: Callable[..., DocumentUnitOfWork],
        *,
        parser: DocumentParserPort,
        storage: StoragePort,
    ) -> None:
        self._uow_factory = uow_factory
        self._parser = parser
        self._storage = storage

    # ── 建档 ────────────────────────────────────────────────────────

    async def create_document(
        self, dto: CreateDocumentDTO, *, owner_id: Optional[int]
    ) -> DocumentDTO:
        async with self._uow_factory() as uow:
            asset = await uow.file_asset_repository.get_by_id(dto.file_asset_id)
            # 归属断言：不能从他人文件建文档，否则解析后可经 /content 读到他人文件内容
            # （跨用户内容泄露）。越权与不存在同 404，不泄露资产存在性。
            if asset is None or asset.is_deleted() or not asset.belongs_to(owner_id):
                raise FileAssetNotFoundException(dto.file_asset_id)
            # active 校验在归属断言之后：只对 owner 报此错，不泄露他人资产状态。
            # pending（直传未 confirm）资产对象可能不存在，建档只会得到模糊的解析失败，
            # 不如在入口快速失败
            if asset.status != "active":
                raise DomainValidationException(
                    "文件资产尚未激活（直传需先调用 /storage/complete）",
                    field="file_asset_id",
                    details={"file_asset_id": dto.file_asset_id, "asset_status": asset.status},
                    message_key="validation.failed",
                    format_params={"reason": "file asset not active"},
                )

            now = utcnow()
            doc = Document(
                id=None,
                owner_id=owner_id,
                file_asset_id=dto.file_asset_id,
                title=dto.title or asset.original_filename,
                source_filename=asset.original_filename,
                content_type=asset.content_type,
                status="pending",
                created_at=now,
                updated_at=now,
            )
            created = await uow.document_repository.create(doc)
            return DocumentDTO.model_validate(created)

    # ── 异步解析（worker 入口） ──────────────────────────────────────

    async def process_document(self, document_id: int) -> None:
        """Parse one document: pending → parsing → ready/failed.

        Background-task entry: errors are persisted to the document record
        (failed + error_code), never raised to a requester.
        """
        # 事务1：原子认领（条件 UPDATE）pending → parsing，并取出 storage key。
        # 并发/排队重复调度同一文档时只有一个 worker 能认领成功，避免重复解析/重复计费。
        async with self._uow_factory() as uow:
            doc = await uow.document_repository.try_mark_parsing(document_id)
            if doc is None:
                logger.warning("document_process_claim_failed", document_id=document_id)
                return
            asset = await uow.file_asset_repository.get_by_id(doc.file_asset_id)
        # 认领 token：落盘时校验行仍属于本次认领，防止 stale 恢复后僵尸任务覆写新结果
        claimed_at = doc.updated_at

        parser_name = self._parser.name
        max_bytes = int(settings.document.max_parse_bytes or 0)
        try:
            if asset is None:
                raise DocumentParserError(
                    code="document.parse.file_asset_missing",
                    message=f"关联的文件资产不存在: {doc.file_asset_id}",
                )
            # 下载前先用文件资产元数据拦截超大文件，避免整对象读入内存后才发现超限
            if max_bytes and asset.size and asset.size > max_bytes:
                raise FileTooLargeException(size=asset.size, max_size=max_bytes)

            # 事务外：下载 + 解析（慢 I/O 不占数据库连接/事务）
            data = await self._storage.download(asset.key)
            # 兜底：防 size 元数据失真
            if max_bytes and len(data) > max_bytes:
                raise FileTooLargeException(size=len(data), max_size=max_bytes)

            parsed = await self._parser.parse(
                data,
                content_type=doc.content_type,
                filename=doc.source_filename,
            )
        except DocumentParserError as exc:
            logger.warning(
                "document_parse_failed",
                document_id=document_id,
                parser=parser_name,
                error_code=exc.code,
                error=exc.message,
            )
            doc.mark_failed(error_code=exc.code, error_message=exc.message, parser=parser_name)
            await self._finalize(doc, claimed_at=claimed_at)
            return
        except FileTooLargeException as exc:
            doc.mark_failed(
                error_code="document.parse.too_large",
                error_message=exc.message,
                parser=parser_name,
            )
            await self._finalize(doc, claimed_at=claimed_at)
            return
        except Exception as exc:  # noqa: BLE001 - worker 入口必须兜底记录
            logger.error(
                "document_parse_unexpected_error",
                document_id=document_id,
                parser=parser_name,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            doc.mark_failed(
                error_code="document.parse.internal_error",
                # error_message 会经 DocumentDTO 暴露给 API，不落 str(exc)
                # （可能含存储端点/路径等内部细节），细节只进结构化日志
                error_message="internal error, see server logs",
                parser=parser_name,
            )
            await self._finalize(doc, claimed_at=claimed_at)
            return

        # 事务2：落盘解析产物
        doc.mark_ready(content_md=parsed.markdown, parser=parser_name, metadata=parsed.metadata)
        if await self._finalize(doc, claimed_at=claimed_at):
            logger.info(
                "document_parse_ready",
                document_id=document_id,
                parser=parser_name,
                chars=len(parsed.markdown),
            )

    async def _finalize(self, doc: Document, *, claimed_at) -> bool:
        """条件落盘：认领已失效（stale 恢复后被新任务接管/已软删）则丢弃本次结果。"""
        async with self._uow_factory() as uow:
            updated = await uow.document_repository.update_if_claimed(doc, claimed_at=claimed_at)
        if not updated:
            logger.warning(
                "document_parse_result_discarded",
                document_id=doc.id,
                parser=self._parser.name,
                reason="claim_superseded_or_deleted",
            )
        return updated

    # ── 查询 ────────────────────────────────────────────────────────

    @staticmethod
    async def _get_owned(uow, document_id: int, owner_id: int) -> Document:
        """加载文档并断言归属；不存在与越权同样抛 404（不泄露存在性）。"""
        doc = await uow.document_repository.get_by_id(document_id)
        if doc is None or not doc.belongs_to(owner_id):
            raise DocumentNotFoundException(document_id)
        return doc

    async def get_document(self, document_id: int, *, owner_id: int) -> DocumentDTO:
        async with self._uow_factory(readonly=True) as uow:
            doc = await self._get_owned(uow, document_id, owner_id)
            return DocumentDTO.model_validate(doc)

    async def get_document_content(
        self, document_id: int, *, owner_id: int
    ) -> DocumentContentDTO:
        async with self._uow_factory(readonly=True) as uow:
            # 归属断言先于 NotReady：不向非 owner 泄露解析状态
            doc = await self._get_owned(uow, document_id, owner_id)
            if not doc.is_ready():
                raise DocumentNotReadyException(document_id, status=doc.status)
            assert doc.id is not None  # 已持久化实体必有 id
            return DocumentContentDTO(
                id=doc.id,
                status=doc.status,
                parser=doc.parser,
                markdown=doc.content_md or "",
            )

    async def list_documents(
        self,
        *,
        owner_id: Optional[int] = None,
        file_asset_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[list[DocumentDTO], int]:
        async with self._uow_factory(readonly=True) as uow:
            items = await uow.document_repository.list(
                owner_id=owner_id,
                file_asset_id=file_asset_id,
                status=status,
                skip=skip,
                limit=limit,
            )
            total = await uow.document_repository.count(
                owner_id=owner_id,
                file_asset_id=file_asset_id,
                status=status,
            )
            return [DocumentDTO.model_validate(d) for d in items], total

    # ── 重解析与删除 ────────────────────────────────────────────────

    async def reset_for_reparse(self, document_id: int, *, owner_id: int) -> DocumentDTO:
        """ready/failed → pending；parsing 中抛 AlreadyProcessing，
        但超过 parsing_stale_seconds 的孤儿任务允许强制恢复。调度由 API 层负责。"""
        async with self._uow_factory() as uow:
            doc = await self._get_owned(uow, document_id, owner_id)
            doc.reset_for_reparse(
                parsing_stale_after_seconds=settings.document.parsing_stale_seconds
            )
            updated = await uow.document_repository.update(doc)
            return DocumentDTO.model_validate(updated)

    async def soft_delete(self, document_id: int, *, owner_id: int) -> DocumentDTO:
        async with self._uow_factory() as uow:
            doc = await self._get_owned(uow, document_id, owner_id)
            doc.soft_delete()
            updated = await uow.document_repository.update(doc)
            return DocumentDTO.model_validate(updated)
