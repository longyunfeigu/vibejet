# input: FileAssetApplicationService + 记录时序的内存 fake UoW/存储
# output: confirm_direct_upload 三段式事务边界测试（存储调用不得发生在事务内）
# pos: 后端测试 - 文件直传确认的事务纪律验证（PERF-02）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""confirm_direct_upload transaction discipline tests.

数据库事务不得跨存储网络调用（get_metadata HEAD）：
tx-1 读取+归属校验 → 无事务取存储元数据 → tx-2 应用并激活。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from application.services.file_asset_service import FileAssetApplicationService
from application.utils.time import utcnow
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
        return self._items.get(asset_id)

    async def get_by_key(self, key: str, include_deleted: bool = False):
        return next((a for a in self._items.values() if a.key == key), None)

    async def update(self, asset: FileAsset) -> FileAsset:
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
    def __init__(self, events: list[str]) -> None:
        self._events = events

    def public_url(self, key: str) -> str:
        return f"https://public.example/{key}"

    async def get_metadata(self, key: str) -> _Meta:
        self._events.append("storage.get_metadata")
        return _Meta()


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
