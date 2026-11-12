"""Presign 幂等重放只对仍 pending 的资产重签上传链接。

Given 客户端用同一 Idempotency-Key 重放 presign
When 资产仍 pending → 重签链接（key/content_type/声明大小取库里的资产）
When 资产已确认（active）或已删除 → 409 FILE_UPLOAD_CLOSED，不签发任何写链接
（否则重放即可在确认期复核之后覆盖对象）。
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Optional

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.dependencies import get_current_user, get_file_asset_service, get_idempotency_service
from api.routes.storage import router as storage_router
from application.dto import UserDTO
from application.ports.storage import PresignedURL, StorageInfo
from application.services.file_asset_service import FileAssetApplicationService
from application.services.idempotency_service import IdempotencyService
from core.exceptions import register_exception_handlers
from domain.common.exceptions import FileAssetNotFoundException, FileUploadClosedException
from domain.file_asset.entity import FileAsset
from shared.codes import BusinessCode
from tests.test_idempotency_presign import InMemoryIdempotencyStore


class _Repo:
    def __init__(self) -> None:
        self.items: dict[int, FileAsset] = {}

    async def create(self, asset: FileAsset) -> FileAsset:
        stored = replace(asset, id=len(self.items) + 1)
        self.items[stored.id] = stored
        return stored

    async def get_by_id(self, asset_id: int, include_deleted: bool = False):
        asset = self.items.get(asset_id)
        if asset is not None and asset.is_deleted() and not include_deleted:
            return None
        return asset

    async def get_by_key(self, key: str, include_deleted: bool = False):
        return next((a for a in self.items.values() if a.key == key), None)

    async def update(self, asset: FileAsset) -> FileAsset:
        self.items[asset.id] = asset
        return asset

    async def update_if_not_deleted(self, asset: FileAsset) -> FileAsset:
        self.items[asset.id] = asset
        return asset


class _UoW:
    def __init__(self, repo: _Repo) -> None:
        self.file_asset_repository = repo

    def __call__(self, **kwargs: Any) -> "_UoW":
        return self

    async def __aenter__(self) -> "_UoW":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def commit(self) -> None:
        return None


@dataclass
class _Meta:
    size: int
    etag: str = "etag-1"
    content_type: Optional[str] = "text/plain"
    custom_metadata: Optional[dict] = None


class _Storage:
    def __init__(self) -> None:
        self.presign_calls: list[dict[str, Any]] = []

    def info(self) -> StorageInfo:
        return StorageInfo(type="s3", bucket="bucket-a", region="us-east-1")

    def public_url(self, key: str) -> str:
        return f"https://public.example/{key}"

    async def generate_presigned_url(self, **kwargs: Any) -> PresignedURL:
        self.presign_calls.append(kwargs)
        n = len(self.presign_calls)
        return PresignedURL(url=f"https://s3.example/put/{n}", method=kwargs["method"])

    async def get_metadata(self, key: str) -> _Meta:
        return _Meta(size=5)

    async def delete(self, key: str) -> bool:
        return True


_PAYLOAD = {
    "filename": "a.txt",
    "mime_type": "text/plain",
    "size_bytes": 5,
    "kind": "uploads",
    "method": "PUT",
    "expires_in": 600,
}
_HEADERS = {"Idempotency-Key": "replay-0001"}


def _app() -> tuple[FastAPI, _Repo, _Storage]:
    repo = _Repo()
    storage = _Storage()
    service = FileAssetApplicationService(uow_factory=_UoW(repo), storage=storage)
    idem = IdempotencyService(
        store=InMemoryIdempotencyStore(), lock_ttl_seconds=5, result_ttl_seconds=60
    )

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(storage_router, prefix="/api/v1")
    app.dependency_overrides[get_file_asset_service] = lambda: service
    app.dependency_overrides[get_idempotency_service] = lambda: idem
    app.dependency_overrides[get_current_user] = lambda: UserDTO(
        id=1, username="u1", email="u1@example.com"
    )
    return app, repo, storage


async def test_replay_while_pending_mints_url_from_stored_asset() -> None:
    app, repo, storage = _app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r1 = await client.post("/api/v1/storage/presign-upload", json=_PAYLOAD, headers=_HEADERS)
        r2 = await client.post("/api/v1/storage/presign-upload", json=_PAYLOAD, headers=_HEADERS)

    assert r1.status_code == 200, r1.json()
    assert r2.status_code == 200, r2.json()
    assert r2.json()["data"]["file"]["id"] == r1.json()["data"]["file"]["id"]
    assert r2.json()["data"]["upload"]["url"] == "https://s3.example/put/2"

    asset = repo.items[r1.json()["data"]["file"]["id"]]
    first, replay = storage.presign_calls
    # 首签与重签都把声明大小下传给存储（S3 PUT 据此签 Content-Length）
    assert first["content_length"] == 5
    assert replay["key"] == asset.key
    assert replay["content_type"] == asset.content_type
    assert replay["content_length"] == 5


async def test_replay_after_confirm_is_409_without_url() -> None:
    app, repo, storage = _app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r1 = await client.post("/api/v1/storage/presign-upload", json=_PAYLOAD, headers=_HEADERS)
        asset_id = r1.json()["data"]["file"]["id"]
        done = await client.post("/api/v1/storage/complete", json={"id": asset_id})
        replay = await client.post(
            "/api/v1/storage/presign-upload", json=_PAYLOAD, headers=_HEADERS
        )

    assert done.status_code == 200, done.json()
    assert repo.items[asset_id].status == "active"

    assert replay.status_code == 409
    body = replay.json()
    assert body["code"] == BusinessCode.FILE_UPLOAD_CLOSED
    assert body["error"]["message_key"] == "file.upload_closed"
    assert body["data"] is None
    # 只有首签那一次：确认后的重放没有向存储要任何写链接
    assert len(storage.presign_calls) == 1


async def test_replay_after_delete_is_409_without_url() -> None:
    app, repo, storage = _app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r1 = await client.post("/api/v1/storage/presign-upload", json=_PAYLOAD, headers=_HEADERS)
        asset_id = r1.json()["data"]["file"]["id"]
        repo.items[asset_id].mark_deleted()
        replay = await client.post(
            "/api/v1/storage/presign-upload", json=_PAYLOAD, headers=_HEADERS
        )

    assert replay.status_code == 409
    assert replay.json()["code"] == BusinessCode.FILE_UPLOAD_CLOSED
    assert len(storage.presign_calls) == 1


async def test_generate_upload_presign_is_owner_scoped() -> None:
    repo = _Repo()
    storage = _Storage()
    service = FileAssetApplicationService(uow_factory=_UoW(repo), storage=storage)
    summary, _ = await service.presign_upload(
        user_id=1, filename="a.txt", mime_type="text/plain", size_bytes=5, kind="uploads"
    )

    with pytest.raises(FileAssetNotFoundException):
        await service.generate_upload_presign(
            asset_id=summary.id, owner_id=2, method="PUT", expires_in=600
        )
    assert len(storage.presign_calls) == 1


async def test_generate_upload_presign_rejects_active_asset() -> None:
    repo = _Repo()
    storage = _Storage()
    service = FileAssetApplicationService(uow_factory=_UoW(repo), storage=storage)
    summary, _ = await service.presign_upload(
        user_id=1, filename="a.txt", mime_type="text/plain", size_bytes=5, kind="uploads"
    )
    repo.items[summary.id].mark_active()

    with pytest.raises(FileUploadClosedException):
        await service.generate_upload_presign(
            asset_id=summary.id, owner_id=1, method="PUT", expires_in=600
        )
    assert len(storage.presign_calls) == 1
