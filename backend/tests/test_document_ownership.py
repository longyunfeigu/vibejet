# input: DocumentApplicationService + 内存 fake 仓储 + documents 路由 test app
# output: Epic-1 Story 1.4 文档归属验收测试
# pos: 后端测试 - documents 端点归属闭环验证（列表过滤、越权 404、后台 worker 不受影响）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Document ownership tests (Epic 1, Story 1.4)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from api.dependencies import get_current_user, get_document_service
from application.dto import UserDTO
from application.services.document_service import DocumentApplicationService
from application.utils.time import utcnow
from core.exceptions import register_exception_handlers
from domain.document.entity import Document
from domain.document.exceptions import DocumentNotFoundException


class _FakeDocumentRepo:
    def __init__(self):
        self._items: dict[int, Document] = {}
        self._next_id = 1

    def seed(self, **kwargs) -> Document:
        now = utcnow()
        doc = Document(
            id=self._next_id,
            file_asset_id=kwargs.pop("file_asset_id", 1),
            created_at=now,
            updated_at=now,
            **kwargs,
        )
        self._items[doc.id] = doc
        self._next_id += 1
        return doc

    async def get_by_id(self, document_id: int, include_deleted: bool = False):
        doc = self._items.get(document_id)
        if doc is None:
            return None
        if not include_deleted and doc.deleted_at is not None:
            return None
        return doc

    async def list(self, *, owner_id=None, file_asset_id=None, status=None, skip=0, limit=20):
        rows = [
            d
            for d in self._items.values()
            if d.deleted_at is None
            and (owner_id is None or d.owner_id == owner_id)
            and (file_asset_id is None or d.file_asset_id == file_asset_id)
            and (status is None or d.status == status)
        ]
        return rows[skip : skip + limit]

    async def count(self, *, owner_id=None, file_asset_id=None, status=None):
        return len(
            await self.list(
                owner_id=owner_id, file_asset_id=file_asset_id, status=status, limit=10**9
            )
        )

    async def update(self, doc: Document) -> Document:
        self._items[doc.id] = doc
        return doc


class _FakeUoW:
    def __init__(self, repo: _FakeDocumentRepo):
        self.document_repository = repo

    def __call__(self, **kwargs):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def commit(self):
        return None


def _service() -> tuple[DocumentApplicationService, _FakeDocumentRepo]:
    repo = _FakeDocumentRepo()
    # parser/storage 仅后台解析路径使用，本文件不触达，给占位对象即可
    service = DocumentApplicationService(
        uow_factory=_FakeUoW(repo), parser=object(), storage=object()
    )
    return service, repo


async def test_owner_full_access() -> None:
    service, repo = _service()
    doc = repo.seed(owner_id=1, status="ready", content_md="# hi", parser="markitdown")

    assert (await service.get_document(doc.id, owner_id=1)).id == doc.id
    assert (await service.get_document_content(doc.id, owner_id=1)).markdown == "# hi"
    reset = await service.reset_for_reparse(doc.id, owner_id=1)
    assert reset.status == "pending"
    deleted = await service.soft_delete(doc.id, owner_id=1)
    assert deleted.id == doc.id


async def test_non_owner_404_on_all_route_facing_methods() -> None:
    service, repo = _service()
    doc = repo.seed(owner_id=1, status="ready", content_md="# hi", parser="markitdown")

    for call in (
        lambda: service.get_document(doc.id, owner_id=2),
        lambda: service.get_document_content(doc.id, owner_id=2),
        lambda: service.reset_for_reparse(doc.id, owner_id=2),
        lambda: service.soft_delete(doc.id, owner_id=2),
    ):
        with pytest.raises(DocumentNotFoundException):
            await call()
    # 无副作用
    assert repo._items[doc.id].status == "ready"
    assert repo._items[doc.id].deleted_at is None


async def test_legacy_null_owner_document_unreachable() -> None:
    service, repo = _service()
    doc = repo.seed(owner_id=None, status="ready", content_md="x", parser="markitdown")

    with pytest.raises(DocumentNotFoundException):
        await service.get_document(doc.id, owner_id=1)


async def test_list_scoped_by_owner_route_level() -> None:
    service, repo = _service()
    mine = repo.seed(owner_id=2, status="ready", content_md="x", parser="markitdown")
    repo.seed(owner_id=1, status="ready", content_md="y", parser="markitdown")

    from api.routes.documents import router as documents_router

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(documents_router, prefix="/api/v1")
    app.dependency_overrides[get_document_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: UserDTO(
        id=2, username="bob", email="bob@example.com"
    )

    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/api/v1/documents")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 1
        assert data["items"][0]["id"] == mine.id
