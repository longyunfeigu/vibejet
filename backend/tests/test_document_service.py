# input: DocumentApplicationService 及内存 fake（UoW/parser/storage）
# output: 文档服务编排测试（建档/解析成功/失败/重解析/内容读取）
# pos: 后端测试 - 文档应用服务用例验证（不触数据库与网络）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Tests for DocumentApplicationService using in-memory fakes."""

from __future__ import annotations

from typing import Optional

import pytest

from application.dto import CreateDocumentDTO
from application.ports.document_parser import DocumentParserError, ParsedDocument
from application.ports.unit_of_work import AbstractUnitOfWork
from application.services.document_service import DocumentApplicationService
from domain.common.exceptions import DomainValidationException, FileAssetNotFoundException
from domain.document import (
    Document,
    DocumentAlreadyProcessingException,
    DocumentNotFoundException,
    DocumentNotReadyException,
)
from domain.file_asset import FileAsset

# ── fakes ───────────────────────────────────────────────────────────


class FakeDocumentRepository:
    def __init__(self) -> None:
        self.items: dict[int, Document] = {}
        self._next_id = 1
        self._claims: dict[int, object] = {}

    async def create(self, document: Document) -> Document:
        document.id = self._next_id
        self._next_id += 1
        self.items[document.id] = document
        return document

    async def update(self, document: Document) -> Document:
        if document.id not in self.items:
            raise DocumentNotFoundException(document.id)
        self.items[document.id] = document
        return document

    async def get_by_id(self, document_id: int, *, include_deleted: bool = False):
        doc = self.items.get(document_id)
        if doc is None:
            return None
        if not include_deleted and doc.deleted_at is not None:
            return None
        return doc

    async def try_mark_parsing(self, document_id: int):
        from application.utils.time import utcnow

        doc = self.items.get(document_id)
        # 与 SQL 实现对齐：仅 pending 可认领
        if doc is None or doc.deleted_at is not None or doc.status != "pending":
            return None
        doc.status = "parsing"
        doc.error_code = None
        doc.error_message = None
        doc.updated_at = utcnow()
        self._claims[document_id] = doc.updated_at
        return doc

    async def update_if_claimed(self, document: Document, *, claimed_at) -> bool:
        stored = self.items.get(document.id)
        if stored is None or stored.deleted_at is not None:
            return False
        if self._claims.get(document.id) != claimed_at:
            return False
        self.items[document.id] = document
        return True

    async def list(self, **kwargs):
        return list(self.items.values())

    async def count(self, **kwargs):
        return len(self.items)


class FakeFileAssetRepository:
    def __init__(self) -> None:
        self.items: dict[int, FileAsset] = {}

    async def get_by_id(self, asset_id: int, *, include_deleted: bool = False):
        return self.items.get(asset_id)


class FakeUnitOfWork(AbstractUnitOfWork):
    """Shared-state fake：所有实例共享同一份仓储，模拟跨事务可见性。

    继承端口基类以复用真实退出语义（干净退出即提交，异常回滚）。
    """

    def __init__(self, documents: FakeDocumentRepository, assets: FakeFileAssetRepository):
        super().__init__()
        self.document_repository = documents
        self.file_asset_repository = assets
        self.committed = False

    async def commit(self):
        self.committed = True

    async def rollback(self):
        return None


class FakeParser:
    name = "fake"

    def __init__(
        self, *, result: Optional[ParsedDocument] = None, error: Optional[Exception] = None
    ):
        self.result = result
        self.error = error
        self.calls: list[dict] = []

    async def parse(self, data: bytes, *, content_type=None, filename=None) -> ParsedDocument:
        self.calls.append({"data": data, "content_type": content_type, "filename": filename})
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


class FakeStorage:
    def __init__(self, blobs: Optional[dict[str, bytes]] = None):
        self.blobs = blobs or {}

    async def download(self, key: str) -> bytes:
        return self.blobs[key]


def _build_service(
    *,
    parser: FakeParser,
    blobs: Optional[dict[str, bytes]] = None,
) -> tuple[DocumentApplicationService, FakeDocumentRepository, FakeFileAssetRepository]:
    documents = FakeDocumentRepository()
    assets = FakeFileAssetRepository()
    service = DocumentApplicationService(
        uow_factory=lambda **kwargs: FakeUnitOfWork(documents, assets),
        parser=parser,
        storage=FakeStorage(blobs),
    )
    return service, documents, assets


def _seed_asset(
    assets: FakeFileAssetRepository, asset_id: int = 10, owner_id=None
) -> FileAsset:
    asset = FileAsset(
        id=asset_id,
        owner_id=owner_id,
        key=f"uploads/{asset_id}.pdf",
        original_filename="report.pdf",
        content_type="application/pdf",
        status="active",
    )
    assets.items[asset_id] = asset
    return asset


# ── 建档 ────────────────────────────────────────────────────────────


async def test_create_document_snapshots_file_asset_fields() -> None:
    service, _, assets = _build_service(parser=FakeParser())
    _seed_asset(assets, owner_id=7)

    dto = await service.create_document(CreateDocumentDTO(file_asset_id=10), owner_id=7)

    assert dto.status == "pending"
    assert dto.owner_id == 7
    assert dto.title == "report.pdf"
    assert dto.source_filename == "report.pdf"
    assert dto.content_type == "application/pdf"


async def test_create_document_rejects_missing_file_asset() -> None:
    service, _, _ = _build_service(parser=FakeParser())
    with pytest.raises(FileAssetNotFoundException):
        await service.create_document(CreateDocumentDTO(file_asset_id=99), owner_id=None)


async def test_create_document_rejects_other_users_file_asset() -> None:
    # 安全回归：不能从他人文件建文档（否则可经 /content 读到他人文件内容）
    service, docs, assets = _build_service(parser=FakeParser())
    _seed_asset(assets, owner_id=1)

    with pytest.raises(FileAssetNotFoundException):
        await service.create_document(CreateDocumentDTO(file_asset_id=10), owner_id=2)
    assert docs.items == {}


async def test_create_document_rejects_non_active_file_asset() -> None:
    # pending（直传未 confirm）资产的对象可能不存在，入口快速失败优于解析期模糊报错
    service, docs, assets = _build_service(parser=FakeParser())
    asset = _seed_asset(assets)
    asset.status = "pending"

    with pytest.raises(DomainValidationException):
        await service.create_document(CreateDocumentDTO(file_asset_id=10), owner_id=None)
    assert docs.items == {}


# ── 解析流程 ────────────────────────────────────────────────────────


async def test_process_document_happy_path() -> None:
    parser = FakeParser(result=ParsedDocument(markdown="# Parsed", metadata={"pages": 2}))
    service, documents, assets = _build_service(
        parser=parser, blobs={"uploads/10.pdf": b"%PDF-bytes"}
    )
    _seed_asset(assets)
    dto = await service.create_document(CreateDocumentDTO(file_asset_id=10), owner_id=None)

    await service.process_document(dto.id)

    doc = documents.items[dto.id]
    assert doc.status == "ready"
    assert doc.content_md == "# Parsed"
    assert doc.parser == "fake"
    assert doc.metadata["pages"] == 2
    # 解析输入来自存储下载
    assert parser.calls[0]["data"] == b"%PDF-bytes"
    assert parser.calls[0]["filename"] == "report.pdf"


async def test_process_document_parser_error_marks_failed() -> None:
    parser = FakeParser(
        error=DocumentParserError(code="document.parse.empty_content", message="no text")
    )
    service, documents, assets = _build_service(
        parser=parser, blobs={"uploads/10.pdf": b"%PDF-scanned"}
    )
    _seed_asset(assets)
    dto = await service.create_document(CreateDocumentDTO(file_asset_id=10), owner_id=None)

    await service.process_document(dto.id)

    doc = documents.items[dto.id]
    assert doc.status == "failed"
    assert doc.error_code == "document.parse.empty_content"
    assert doc.error_message == "no text"


async def test_process_document_unexpected_error_marks_failed() -> None:
    parser = FakeParser(error=RuntimeError("boom"))
    service, documents, assets = _build_service(parser=parser, blobs={"uploads/10.pdf": b"x"})
    _seed_asset(assets)
    dto = await service.create_document(CreateDocumentDTO(file_asset_id=10), owner_id=None)

    await service.process_document(dto.id)

    doc = documents.items[dto.id]
    assert doc.status == "failed"
    assert doc.error_code == "document.parse.internal_error"


async def test_process_document_skips_when_already_parsing() -> None:
    parser = FakeParser(result=ParsedDocument(markdown="# x"))
    service, documents, assets = _build_service(parser=parser, blobs={"uploads/10.pdf": b"x"})
    _seed_asset(assets)
    dto = await service.create_document(CreateDocumentDTO(file_asset_id=10), owner_id=None)
    documents.items[dto.id].status = "parsing"

    await service.process_document(dto.id)

    assert documents.items[dto.id].status == "parsing"
    assert parser.calls == []


async def test_process_document_too_large_marks_failed(monkeypatch) -> None:
    from core.config import settings

    parser = FakeParser(result=ParsedDocument(markdown="# x"))
    service, documents, assets = _build_service(
        parser=parser, blobs={"uploads/10.pdf": b"0123456789"}
    )
    _seed_asset(assets)
    dto = await service.create_document(CreateDocumentDTO(file_asset_id=10), owner_id=None)

    monkeypatch.setattr(settings.document, "max_parse_bytes", 5)
    await service.process_document(dto.id)

    doc = documents.items[dto.id]
    assert doc.status == "failed"
    assert doc.error_code == "document.parse.too_large"
    assert parser.calls == []


async def test_process_document_missing_file_asset_marks_failed() -> None:
    parser = FakeParser(result=ParsedDocument(markdown="# x"))
    service, documents, assets = _build_service(parser=parser)
    _seed_asset(assets)
    dto = await service.create_document(CreateDocumentDTO(file_asset_id=10), owner_id=None)
    del assets.items[10]  # 建档后文件资产被删除

    await service.process_document(dto.id)

    doc = documents.items[dto.id]
    assert doc.status == "failed"
    assert doc.error_code == "document.parse.file_asset_missing"


# ── 内容读取与重解析 ────────────────────────────────────────────────


async def test_get_document_content_requires_ready() -> None:
    parser = FakeParser(result=ParsedDocument(markdown="# Done"))
    service, documents, assets = _build_service(parser=parser, blobs={"uploads/10.pdf": b"x"})
    _seed_asset(assets, owner_id=7)
    dto = await service.create_document(CreateDocumentDTO(file_asset_id=10), owner_id=7)

    with pytest.raises(DocumentNotReadyException):
        await service.get_document_content(dto.id, owner_id=7)

    await service.process_document(dto.id)
    content = await service.get_document_content(dto.id, owner_id=7)
    assert content.markdown == "# Done"
    assert content.parser == "fake"


async def test_reset_for_reparse_rejected_while_parsing() -> None:
    service, documents, assets = _build_service(parser=FakeParser())
    _seed_asset(assets, owner_id=7)
    dto = await service.create_document(CreateDocumentDTO(file_asset_id=10), owner_id=7)
    documents.items[dto.id].status = "parsing"

    with pytest.raises(DocumentAlreadyProcessingException):
        await service.reset_for_reparse(dto.id, owner_id=7)


async def test_reset_for_reparse_clears_previous_result() -> None:
    parser = FakeParser(result=ParsedDocument(markdown="# v1"))
    service, documents, assets = _build_service(parser=parser, blobs={"uploads/10.pdf": b"x"})
    _seed_asset(assets, owner_id=7)
    dto = await service.create_document(CreateDocumentDTO(file_asset_id=10), owner_id=7)
    await service.process_document(dto.id)
    assert documents.items[dto.id].status == "ready"

    reset = await service.reset_for_reparse(dto.id, owner_id=7)
    assert reset.status == "pending"
    assert documents.items[dto.id].content_md is None


async def test_get_document_not_found() -> None:
    service, _, _ = _build_service(parser=FakeParser())
    with pytest.raises(DocumentNotFoundException):
        await service.get_document(123, owner_id=7)


async def test_process_document_rejects_oversize_before_download(monkeypatch) -> None:
    """asset.size 超限时在 download 之前拦截（FakeStorage 为空，若尝试下载会 KeyError）。"""
    from core.config import settings

    parser = FakeParser(result=ParsedDocument(markdown="# x"))
    service, documents, assets = _build_service(parser=parser)  # 无 blob
    asset = _seed_asset(assets)
    asset.size = 100
    dto = await service.create_document(CreateDocumentDTO(file_asset_id=10), owner_id=None)

    monkeypatch.setattr(settings.document, "max_parse_bytes", 5)
    await service.process_document(dto.id)

    doc = documents.items[dto.id]
    assert doc.status == "failed"
    assert doc.error_code == "document.parse.too_large"
    assert parser.calls == []


async def test_zombie_result_discarded_after_stale_recovery() -> None:
    """旧任务认领后，stale 恢复 + 新任务重新认领；旧任务结果落盘必须被丢弃。"""
    parser = FakeParser(result=ParsedDocument(markdown="# old"))
    service, documents, assets = _build_service(parser=parser, blobs={"uploads/10.pdf": b"x"})
    _seed_asset(assets)
    dto = await service.create_document(CreateDocumentDTO(file_asset_id=10), owner_id=None)

    # 旧任务认领
    old_doc = await documents.try_mark_parsing(dto.id)
    old_claim = old_doc.updated_at

    # stale 恢复 + 新任务重新认领（claims 被覆盖）
    old_doc.status = "pending"
    new_doc = await documents.try_mark_parsing(dto.id)
    assert new_doc is not None

    # 旧任务迟到的落盘被拒绝
    old_doc.mark_ready(content_md="# zombie", parser="fake")
    assert await documents.update_if_claimed(old_doc, claimed_at=old_claim) is False
