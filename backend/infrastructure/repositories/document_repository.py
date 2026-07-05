# input: SQLAlchemy AsyncSession, DocumentModel ORM
# output: SQLAlchemyDocumentRepository 仓储实现
# pos: 基础设施层 - 文档聚合仓储 SQLAlchemy 实现；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""SQLAlchemy-backed repository for documents."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from domain.document import Document, DocumentNotFoundException, DocumentRepository
from infrastructure.models.document import DocumentModel
from infrastructure.repositories.base_repository import execute_targeted_update
from infrastructure.repositories.mixins import SoftDeleteFilterMixin


class SQLAlchemyDocumentRepository(SoftDeleteFilterMixin, DocumentRepository):
    """Persist document aggregates using SQLAlchemy ORM."""

    model_class = DocumentModel

    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, model: DocumentModel, *, include_content: bool = True) -> Document:
        # include_content=False 用于列表路径：content_md 被 defer，
        # 触碰该属性会在 async 下惰性加载报错，且列表 DTO 本就不含正文
        return Document(
            id=model.id,
            owner_id=model.owner_id,
            file_asset_id=model.file_asset_id,
            title=model.title,
            source_filename=model.source_filename,
            content_type=model.content_type,
            parser=model.parser,
            status=model.status,
            content_md=model.content_md if include_content else None,
            error_code=model.error_code,
            error_message=model.error_message,
            metadata=dict(model.extra_metadata or {}),
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )

    def _apply_filters(
        self,
        query,
        *,
        owner_id: Optional[int] = None,
        file_asset_id: Optional[int] = None,
        status: Optional[str] = None,
    ):
        query = super()._apply_filters(query)  # mixin: excludes soft-deleted
        if owner_id is not None:
            query = query.where(DocumentModel.owner_id == owner_id)
        if file_asset_id is not None:
            query = query.where(DocumentModel.file_asset_id == file_asset_id)
        if status:
            query = query.where(DocumentModel.status == status)
        return query

    async def create(self, document: Document) -> Document:
        model = DocumentModel(
            owner_id=document.owner_id,
            file_asset_id=document.file_asset_id,
            title=document.title,
            source_filename=document.source_filename,
            content_type=document.content_type,
            parser=document.parser,
            status=document.status,
            content_md=document.content_md,
            error_code=document.error_code,
            error_message=document.error_message,
            extra_metadata=document.metadata or {},
            created_at=document.created_at,
            updated_at=document.updated_at,
            deleted_at=document.deleted_at,
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def update(self, document: Document) -> Document:
        # 注意：list() 返回的实体不携带正文（content_md=None），不得用于 update 回写
        await execute_targeted_update(
            self.session,
            DocumentModel,
            document.id,
            {
                "owner_id": document.owner_id,
                "file_asset_id": document.file_asset_id,
                "title": document.title,
                "source_filename": document.source_filename,
                "content_type": document.content_type,
                "parser": document.parser,
                "status": document.status,
                "content_md": document.content_md,
                "error_code": document.error_code,
                "error_message": document.error_message,
                "extra_metadata": document.metadata or {},
                "updated_at": document.updated_at,
                "deleted_at": document.deleted_at,
            },
            not_found=lambda: DocumentNotFoundException(document.id),
        )
        return document

    async def try_mark_parsing(self, document_id: int) -> Optional[Document]:
        """原子 check-and-set：仅 pending 可认领（条件 UPDATE，规避 check-then-act 竞态）。

        收紧到 pending 同时挡住并发认领与"排队任务在前序完成后从 ready 再次认领"。
        """
        # UPDATE ... RETURNING：认领与读回合并为一次往返（PG/现代 SQLite 均支持）
        result = await self.session.execute(
            update(DocumentModel)
            .where(
                DocumentModel.id == document_id,
                DocumentModel.status == "pending",
                DocumentModel.deleted_at.is_(None),
            )
            .values(
                status="parsing",
                error_code=None,
                error_message=None,
                updated_at=datetime.now(timezone.utc),
            )
            .returning(DocumentModel)
            .execution_options(synchronize_session=False)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def update_if_claimed(self, document: Document, *, claimed_at) -> bool:
        """条件落盘：行仍属于本次认领（status=parsing 且 updated_at 未被他人改写）才更新。"""
        result = await self.session.execute(
            update(DocumentModel)
            .where(
                DocumentModel.id == document.id,
                DocumentModel.status == "parsing",
                DocumentModel.updated_at == claimed_at,
                DocumentModel.deleted_at.is_(None),
            )
            .values(
                title=document.title,
                parser=document.parser,
                status=document.status,
                content_md=document.content_md,
                error_code=document.error_code,
                error_message=document.error_message,
                extra_metadata=document.metadata or {},
                updated_at=document.updated_at,
            )
        )
        return (result.rowcount or 0) == 1

    async def get_by_id(
        self, document_id: int, *, include_deleted: bool = False
    ) -> Optional[Document]:
        query = select(DocumentModel).where(DocumentModel.id == document_id)
        if not include_deleted:
            query = self._filter_active(query)
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list(
        self,
        *,
        owner_id: Optional[int] = None,
        file_asset_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Document]:
        # 列表不加载 Markdown 正文：content_md 无界大、列表 DTO 不含正文
        # （正文走 /content 端点单独加载）；error_message 属列表 DTO 字段，保留
        query = select(DocumentModel).options(defer(DocumentModel.content_md))
        query = self._apply_filters(
            query,
            owner_id=owner_id,
            file_asset_id=file_asset_id,
            status=status,
        )
        query = query.order_by(
            DocumentModel.created_at.desc(),
            DocumentModel.id.desc(),
        )
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._to_entity(model, include_content=False) for model in models]

    async def count(
        self,
        *,
        owner_id: Optional[int] = None,
        file_asset_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> int:
        query = select(func.count()).select_from(DocumentModel)
        query = self._apply_filters(
            query,
            owner_id=owner_id,
            file_asset_id=file_asset_id,
            status=status,
        )
        result = await self.session.execute(query)
        return int(result.scalar() or 0)
