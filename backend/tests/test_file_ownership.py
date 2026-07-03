# input: FileAssetApplicationService + 内存 fake 仓储/存储 + files/storage 路由 test app
# output: Epic-1 Story 1.3 文件归属验收测试
# pos: 后端测试 - files/storage 端点归属闭环验证（列表过滤、越权 404、complete 归属）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""File asset ownership tests (Epic 1, Story 1.3)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from api.dependencies import get_current_user, get_file_asset_service
from application.dto import UserDTO
from application.services.file_asset_service import FileAssetApplicationService
from core.exceptions import register_exception_handlers
from domain.common.exceptions import FileAssetNotFoundException
from domain.file_asset.entity import FileAsset


class _FakeFileAssetRepo:
    def __init__(self):
        self._items: dict[int, FileAsset] = {}
        self._next_id = 1

    def seed(self, **kwargs) -> FileAsset:
        from application.utils.time import utcnow

        now = utcnow()
        asset = FileAsset(
            id=self._next_id,
            key=kwargs.pop("key", f"k-{self._next_id}"),
            created_at=now,
            updated_at=now,
            **kwargs,
        )
        self._items[asset.id] = asset
        self._next_id += 1
        return asset

    async def get_by_id(self, asset_id: int, include_deleted: bool = False):
        asset = self._items.get(asset_id)
        if asset is None:
            return None
        if not include_deleted and asset.is_deleted():
            return None
        return asset

    async def get_by_key(self, key: str, include_deleted: bool = False):
        for asset in self._items.values():
            if asset.key == key and (include_deleted or not asset.is_deleted()):
                return asset
        return None

    async def list(self, *, owner_id=None, kind=None, status=None, skip=0, limit=20):
        rows = [
            a
            for a in self._items.values()
            if not a.is_deleted()
            and (owner_id is None or a.owner_id == owner_id)
            and (kind is None or a.kind == kind)
            and (status is None or a.status == status)
        ]
        return rows[skip : skip + limit]

    async def count(self, *, owner_id=None, kind=None, status=None):
        return len(await self.list(owner_id=owner_id, kind=kind, status=status, limit=10**9))

    async def update(self, asset: FileAsset) -> FileAsset:
        self._items[asset.id] = asset
        return asset


class _FakeUoW:
    def __init__(self, repo: _FakeFileAssetRepo):
        self.file_asset_repository = repo

    def __call__(self, **kwargs):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def commit(self):
        return None


@dataclass
class _Presigned:
    url: str = "https://signed.example/x"
    expires_in: int = 600


@dataclass
class _Meta:
    size: int = 10
    etag: str = "etag"
    content_type: str = "text/plain"
    custom_metadata: Optional[dict] = None


class _FakeStorage:
    def public_url(self, key: str) -> str:
        return f"https://public.example/{key}"

    async def get_metadata(self, key: str) -> _Meta:
        return _Meta()

    async def generate_presigned_url(self, **kwargs) -> _Presigned:
        return _Presigned()


def _service() -> tuple[FileAssetApplicationService, _FakeFileAssetRepo]:
    repo = _FakeFileAssetRepo()
    service = FileAssetApplicationService(uow_factory=_FakeUoW(repo), storage=_FakeStorage())
    return service, repo


# ---------------------------------------------------------------------------
# service 层：归属断言
# ---------------------------------------------------------------------------


async def test_owner_full_access_service_level() -> None:
    service, repo = _service()
    asset = repo.seed(owner_id=1, status="active")

    got = await service.get_asset_raw(asset.id, owner_id=1)
    assert got.id == asset.id

    by_key = await service.get_asset_by_key_raw(asset.key, owner_id=1)
    assert by_key.id == asset.id

    deleted = await service.soft_delete(asset.id, owner_id=1)
    assert deleted.status == "deleted"


async def test_non_owner_404_service_level() -> None:
    service, repo = _service()
    asset = repo.seed(owner_id=1, status="active")

    with pytest.raises(FileAssetNotFoundException):
        await service.get_asset_raw(asset.id, owner_id=2)
    with pytest.raises(FileAssetNotFoundException):
        await service.get_asset_by_key_raw(asset.key, owner_id=2)
    with pytest.raises(FileAssetNotFoundException):
        await service.soft_delete(asset.id, owner_id=2)
    # 断言失败未产生副作用
    assert repo._items[asset.id].status == "active"


async def test_by_key_non_owner_404_matches_not_found_details() -> None:
    # I2：非 owner 与不存在的 404 必须同 details，不泄露资产存在性/内部 asset_id
    service, repo = _service()
    asset = repo.seed(owner_id=1, status="active", key="uploads/secret.pdf")

    with pytest.raises(FileAssetNotFoundException) as non_owner:
        await service.get_asset_by_key_raw(asset.key, owner_id=2)
    with pytest.raises(FileAssetNotFoundException) as missing:
        await service.get_asset_by_key_raw("uploads/does-not-exist.pdf", owner_id=2)

    # 两者都只带 key、不带 asset_id
    assert "asset_id" not in non_owner.value.details
    assert non_owner.value.details == {"key": "uploads/secret.pdf"}
    assert "asset_id" not in missing.value.details


async def test_legacy_null_owner_asset_unreachable() -> None:
    service, repo = _service()
    asset = repo.seed(owner_id=None, status="active")

    for uid in (1, 2):
        with pytest.raises(FileAssetNotFoundException):
            await service.get_asset_raw(asset.id, owner_id=uid)


async def test_complete_non_owner_404_and_status_unchanged() -> None:
    service, repo = _service()
    pending = repo.seed(owner_id=1, status="pending")

    with pytest.raises(FileAssetNotFoundException):
        await service.confirm_direct_upload(asset_id=pending.id, owner_id=2)
    assert repo._items[pending.id].status == "pending"

    # owner 确认成功（presign → complete 全链路的 service 侧）
    dto = await service.confirm_direct_upload(asset_id=pending.id, owner_id=1)
    assert dto.status == "active"


# ---------------------------------------------------------------------------
# route 层：files 路由传递 current_user + storage/complete
# ---------------------------------------------------------------------------


def _app(service: FileAssetApplicationService, user_id: int) -> FastAPI:
    from api.routes.files import router as files_router
    from api.routes.storage import router as storage_router

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(files_router, prefix="/api/v1")
    app.include_router(storage_router, prefix="/api/v1")
    app.dependency_overrides[get_file_asset_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: UserDTO(
        id=user_id, username=f"u{user_id}", email=f"u{user_id}@example.com"
    )
    return app


@pytest.mark.asyncio
async def test_routes_list_scoped_and_non_owner_404() -> None:
    service, repo = _service()
    mine = repo.seed(owner_id=2, status="active", original_filename="mine.txt")
    theirs = repo.seed(owner_id=1, status="active", original_filename="theirs.txt")

    app = _app(service, user_id=2)
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 列表只见自己的
        resp = await client.get("/api/v1/files")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 1
        assert data["items"][0]["id"] == mine.id

        # owner 详情 / 预览 / 下载 / 删除全通
        assert (await client.get(f"/api/v1/files/{mine.id}")).status_code == 200
        assert (
            await client.post(f"/api/v1/files/{mine.id}/preview-url", json={"expires_in": 300})
        ).status_code == 200
        assert (
            await client.post(f"/api/v1/files/{mine.id}/download-url", json={"expires_in": 300})
        ).status_code == 200

        # 越权 → 404
        assert (await client.get(f"/api/v1/files/{theirs.id}")).status_code == 404
        assert (
            await client.post(f"/api/v1/files/{theirs.id}/preview-url", json={"expires_in": 300})
        ).status_code == 404
        assert (
            await client.post(f"/api/v1/files/{theirs.id}/download-url", json={"expires_in": 300})
        ).status_code == 404
        assert (await client.delete(f"/api/v1/files/{theirs.id}")).status_code == 404
        assert repo._items[theirs.id].status == "active"

        # owner 删除自己的成功
        assert (await client.delete(f"/api/v1/files/{mine.id}")).status_code == 200


@pytest.mark.asyncio
async def test_presign_complete_flow_route_level() -> None:
    service, repo = _service()
    pending = repo.seed(owner_id=1, status="pending")

    # B(user 2) 确认 A 的 pending 资产 → 404 且状态不变
    app_b = _app(service, user_id=2)
    async with AsyncClient(app=app_b, base_url="http://test") as client:
        resp = await client.post("/api/v1/storage/complete", json={"id": pending.id})
        assert resp.status_code == 404
        assert repo._items[pending.id].status == "pending"

    # A(user 1) 自己确认 → 激活
    app_a = _app(service, user_id=1)
    async with AsyncClient(app=app_a, base_url="http://test") as client:
        resp = await client.post("/api/v1/storage/complete", json={"id": pending.id})
        assert resp.status_code == 200
        assert repo._items[pending.id].status == "active"
