"""confirm_direct_upload tests.

- 事务纪律：数据库事务不得跨存储网络调用（get_metadata HEAD）：
  tx-1 读取+归属校验 → 无事务取存储元数据 → tx-2 应用并激活。
- 策略复核（Given 客户端声明的 size/type 合规 When 存储里的真实对象不合规 Then 4xx +
  删对象 + 资产软删）；对象未上传 → 409；tx-2 期间被并发删除 → 404 且不复活。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pytest

from application.ports.storage import StorageObjectNotFoundError
from application.services.file_asset_service import FileAssetApplicationService
from application.utils.time import utcnow
from core.config import settings
from domain.common.exceptions import (
    DomainValidationException,
    FileAssetNotFoundException,
    FileNotUploadedException,
    FileTooLargeException,
    UnsupportedMimeTypeException,
)
from domain.file_asset.entity import FileAsset


class _Repo:
    def __init__(self) -> None:
        self._items: dict[int, FileAsset] = {}

    def seed(self, **kwargs) -> FileAsset:
        now = utcnow()
        asset = FileAsset(
            id=len(self._items) + 1,
            key=kwargs.pop("key", "uploads/x.bin"),
            created_at=now,
            updated_at=now,
            **kwargs,
        )
        self._items[asset.id] = asset
        return asset

    async def get_by_id(self, asset_id: int, include_deleted: bool = False):
        asset = self._items.get(asset_id)
        if asset is not None and asset.is_deleted() and not include_deleted:
            return None
        return asset

    async def get_by_key(self, key: str, include_deleted: bool = False):
        return next((a for a in self._items.values() if a.key == key), None)

    async def update(self, asset: FileAsset) -> FileAsset:
        self._items[asset.id] = asset
        return asset

    async def update_if_not_deleted(self, asset: FileAsset) -> FileAsset:
        # 模拟 WHERE deleted_at IS NULL：库里的行（非调用方手里的实体）已被软删 → 0 行
        stored = self._items.get(asset.id)
        if stored is None or stored.deleted_at is not None:
            raise FileAssetNotFoundException(asset.id)
        self._items[asset.id] = asset
        return asset


class _RecordingUoW:
    """记录 enter/exit 时序与工厂 kwargs 的 fake UoW（工厂即实例自身）。"""

    def __init__(self, repo: _Repo, events: list[str]) -> None:
        self.file_asset_repository = repo
        self._events = events
        self.factory_kwargs: list[dict] = []

    def __call__(self, **kwargs):
        self.factory_kwargs.append(kwargs)
        return self

    async def __aenter__(self):
        self._events.append("uow_enter")
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._events.append("uow_exit")
        return None

    async def commit(self) -> None:
        return None


@dataclass
class _Meta:
    size: int = 42
    etag: str = "etag-42"
    content_type: Optional[str] = "application/octet-stream"
    custom_metadata: Optional[dict] = None


class _RecordingStorage:
    def __init__(self, events: list[str], meta: Optional[_Meta] = None) -> None:
        self._events = events
        self._meta = meta or _Meta()
        self.deleted: list[str] = []
        self.missing = False

    def public_url(self, key: str) -> str:
        return f"https://public.example/{key}"

    async def get_metadata(self, key: str) -> _Meta:
        self._events.append("storage.get_metadata")
        if self.missing:
            raise StorageObjectNotFoundError(key)
        return self._meta

    async def delete(self, key: str) -> bool:
        self.deleted.append(key)
        return True


async def test_confirm_keeps_storage_call_outside_any_transaction() -> None:
    events: list[str] = []
    repo = _Repo()
    asset = repo.seed(owner_id=1, status="pending")
    uow = _RecordingUoW(repo, events)
    service = FileAssetApplicationService(uow_factory=uow, storage=_RecordingStorage(events))

    dto = await service.confirm_direct_upload(asset_id=asset.id, owner_id=1)

    # 元数据已应用、资产已激活（行为不变）
    assert dto.status == "active"
    assert dto.size == 42
    assert dto.etag == "etag-42"
    assert dto.url == f"https://public.example/{asset.key}"

    # 存储调用发生时没有开启中的事务（其前 enter/exit 配平）
    i = events.index("storage.get_metadata")
    assert events[:i].count("uow_enter") == events[:i].count("uow_exit")
    # 结构 = 只读加载事务 + 写入事务
    assert events.count("uow_enter") == 2
    # tx-1 是只读事务
    assert uow.factory_kwargs[0].get("readonly") is True


def _setup(meta: Optional[_Meta] = None, **seed):
    events: list[str] = []
    repo = _Repo()
    asset = repo.seed(owner_id=1, status="pending", **seed)
    storage = _RecordingStorage(events, meta)
    service = FileAssetApplicationService(uow_factory=_RecordingUoW(repo, events), storage=storage)
    return service, repo, storage, asset


async def test_confirm_compliant_upload_with_declared_size_activates() -> None:
    service, repo, storage, asset = _setup(
        _Meta(size=42, content_type="image/png"),
        metadata={"expected_size": 42},
        content_type="image/png",
    )

    dto = await service.confirm_direct_upload(asset_id=asset.id, owner_id=1)

    assert dto.status == "active" and dto.size == 42
    assert storage.deleted == []


async def test_confirm_rejects_object_larger_than_presign_max(monkeypatch) -> None:
    monkeypatch.setattr(settings.storage, "presign_max_size", 100)
    service, repo, storage, asset = _setup(_Meta(size=101))

    with pytest.raises(FileTooLargeException):
        await service.confirm_direct_upload(asset_id=asset.id, owner_id=1)

    assert storage.deleted == [asset.key]
    assert repo._items[asset.id].status == "deleted"
    assert repo._items[asset.id].deleted_at is not None


async def test_confirm_rejects_object_larger_than_declared_size() -> None:
    # 声明 10 字节（presign 校验通过），实际传了 42 字节
    service, repo, storage, asset = _setup(_Meta(size=42), metadata={"expected_size": 10})

    with pytest.raises(FileTooLargeException) as exc_info:
        await service.confirm_direct_upload(asset_id=asset.id, owner_id=1)

    assert exc_info.value.details == {"size": 42, "max_size": 10}
    assert storage.deleted == [asset.key]
    assert repo._items[asset.id].status == "deleted"


async def test_confirm_rejects_object_smaller_than_declared_size() -> None:
    service, repo, storage, asset = _setup(_Meta(size=5), metadata={"expected_size": 42})

    with pytest.raises(DomainValidationException):
        await service.confirm_direct_upload(asset_id=asset.id, owner_id=1)

    assert storage.deleted == [asset.key]
    assert repo._items[asset.id].status == "deleted"


async def test_confirm_rejects_content_type_outside_presign_allowlist(monkeypatch) -> None:
    monkeypatch.setattr(settings.storage, "presign_content_types", ["image/png"])
    # 声明 image/png（presign 放行），实际对象是 text/html
    service, repo, storage, asset = _setup(
        _Meta(content_type="text/html"), content_type="image/png"
    )

    with pytest.raises(UnsupportedMimeTypeException):
        await service.confirm_direct_upload(asset_id=asset.id, owner_id=1)

    assert storage.deleted == [asset.key]
    assert repo._items[asset.id].status == "deleted"


async def test_confirm_allowlist_ignores_content_type_parameters(monkeypatch) -> None:
    monkeypatch.setattr(settings.storage, "presign_content_types", ["text/plain"])
    service, _, storage, asset = _setup(_Meta(content_type="text/plain; charset=utf-8"))

    dto = await service.confirm_direct_upload(asset_id=asset.id, owner_id=1)

    assert dto.status == "active"
    assert storage.deleted == []


async def test_confirm_rejection_survives_storage_delete_failure(monkeypatch) -> None:
    monkeypatch.setattr(settings.storage, "presign_max_size", 10)
    service, repo, storage, asset = _setup(_Meta(size=11))

    async def _boom(key: str) -> bool:
        raise RuntimeError("storage down")

    storage.delete = _boom  # type: ignore[method-assign]

    with pytest.raises(FileTooLargeException):
        await service.confirm_direct_upload(asset_id=asset.id, owner_id=1)
    assert repo._items[asset.id].status == "deleted"


async def test_confirm_before_object_uploaded_raises_not_uploaded() -> None:
    service, repo, storage, asset = _setup()
    storage.missing = True

    with pytest.raises(FileNotUploadedException):
        await service.confirm_direct_upload(asset_id=asset.id, owner_id=1)

    # 资产保持 pending，客户端上传完成后可重试
    assert repo._items[asset.id].status == "pending"
    assert storage.deleted == []


async def test_confirm_does_not_resurrect_asset_deleted_during_confirm() -> None:
    service, repo, storage, asset = _setup()
    original_get = repo.get_by_id
    calls = {"n": 0}

    async def _get_then_concurrent_delete(asset_id: int, include_deleted: bool = False):
        calls["n"] += 1
        found = await original_get(asset_id, include_deleted)
        if calls["n"] == 2 and found is not None:
            # tx-2 读到 pending 后、写入前，另一个请求把它软删并提交
            deleted = FileAsset(**{**found.__dict__})
            deleted.mark_deleted()
            repo._items[asset_id] = deleted
            return FileAsset(**{**found.__dict__})
        return found

    repo.get_by_id = _get_then_concurrent_delete  # type: ignore[method-assign]

    with pytest.raises(FileAssetNotFoundException):
        await service.confirm_direct_upload(asset_id=asset.id, owner_id=1)

    assert repo._items[asset.id].status == "deleted"
    assert repo._items[asset.id].deleted_at is not None


async def test_complete_route_renders_409_when_object_not_uploaded() -> None:
    """POST /storage/complete 在对象未落盘时是 409 业务错误，而不是 500。"""
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from api.dependencies import get_current_user, get_file_asset_service
    from api.routes.storage import router as storage_router
    from application.dto import UserDTO
    from core.exceptions import register_exception_handlers
    from shared.codes import BusinessCode

    service, _, storage, asset = _setup()
    storage.missing = True

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(storage_router, prefix="/api/v1")
    app.dependency_overrides[get_file_asset_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: UserDTO(
        id=1, username="u1", email="u1@example.com"
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/storage/complete", json={"id": asset.id})

    assert resp.status_code == 409
    body = resp.json()
    assert body["code"] == BusinessCode.FILE_NOT_UPLOADED
    assert body["error"]["message_key"] == "file.not_uploaded"
