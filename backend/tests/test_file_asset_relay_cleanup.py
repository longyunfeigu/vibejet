# input: FileAssetApplicationService + fake StoragePort/失败 UoW
# output: relay 上传 DB 写入失败时孤儿对象 best-effort 清理测试
# pos: 后端测试 - 文件资产 relay 上传补偿路径验证；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Tests for relay upload orphan-object compensation (audit P1-2).

存储 upload 成功后 DB upsert 失败：UoW 只回滚 DB，已上传对象会变孤儿。
服务必须 best-effort 删除该对象；删除失败只告警，不掩盖原始异常。
"""

from __future__ import annotations

from typing import AsyncIterator, Optional

import pytest

from application.ports.storage import PresignedURL, StorageInfo, UploadOutcome
from application.services.file_asset_service import FileAssetApplicationService


class _FakeStorage:
    def __init__(self, *, delete_raises: bool = False):
        self.deleted_keys: list[str] = []
        self._delete_raises = delete_raises

    def info(self) -> StorageInfo:
        return StorageInfo(type="local", bucket=None, region=None)

    async def delete(self, key: str) -> bool:
        if self._delete_raises:
            raise RuntimeError("storage unavailable")
        self.deleted_keys.append(key)
        return True

    async def download(self, key: str) -> bytes:  # pragma: no cover
        raise NotImplementedError

    async def get_metadata(self, key: str):  # pragma: no cover
        raise NotImplementedError

    async def upload(
        self,
        data: bytes,
        key: str,
        metadata: Optional[dict] = None,
        content_type: Optional[str] = None,
    ) -> UploadOutcome:
        return UploadOutcome(key=key, etag="etag-1", size=len(data), content_type=content_type)

    async def upload_stream(
        self,
        stream: AsyncIterator[bytes],
        key: str,
        metadata: Optional[dict] = None,
        content_type: Optional[str] = None,
    ) -> UploadOutcome:
        size = 0
        async for chunk in stream:
            size += len(chunk)
        return UploadOutcome(key=key, etag="etag-1", size=size, content_type=content_type)

    async def generate_presigned_url(self, key: str, **kwargs) -> PresignedURL:  # pragma: no cover
        raise NotImplementedError

    def public_url(self, key: str) -> Optional[str]:
        return f"https://cdn.test/{key}"


class _ExplodingUoW:
    """进入事务即失败，模拟 DB 不可用/约束冲突。"""

    file_asset_repository = None

    async def __aenter__(self) -> "_ExplodingUoW":
        raise RuntimeError("db down")

    async def __aexit__(self, exc_type, exc, tb) -> None:  # pragma: no cover
        return None

    async def commit(self) -> None:  # pragma: no cover
        return None


async def _byte_stream() -> AsyncIterator[bytes]:
    yield b"hello"


async def test_relay_upload_cleans_orphan_object_when_db_fails() -> None:
    storage = _FakeStorage()
    service = FileAssetApplicationService(uow_factory=_ExplodingUoW, storage=storage)

    with pytest.raises(RuntimeError, match="db down"):
        await service.relay_upload(user_id=1, file_bytes=b"hello", filename="a.txt", kind="doc")

    assert len(storage.deleted_keys) == 1


async def test_relay_upload_stream_cleans_orphan_object_when_db_fails() -> None:
    storage = _FakeStorage()
    service = FileAssetApplicationService(uow_factory=_ExplodingUoW, storage=storage)

    with pytest.raises(RuntimeError, match="db down"):
        await service.relay_upload_stream(
            user_id=1, file_stream=_byte_stream(), filename="a.txt", kind="doc"
        )

    assert len(storage.deleted_keys) == 1


async def test_relay_upload_cleanup_failure_does_not_mask_original_error() -> None:
    storage = _FakeStorage(delete_raises=True)
    service = FileAssetApplicationService(uow_factory=_ExplodingUoW, storage=storage)

    # 原始 DB 异常必须冒出来，而不是清理时的 "storage unavailable"
    with pytest.raises(RuntimeError, match="db down"):
        await service.relay_upload(user_id=1, file_bytes=b"hello", filename="a.txt", kind="doc")
