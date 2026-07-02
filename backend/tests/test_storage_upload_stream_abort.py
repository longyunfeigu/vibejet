# input: StorageProviderPortAdapter + fake AdvancedStorageProvider
# output: 流式上传中断路径的 multipart abort 补偿测试
# pos: 后端测试 - 存储端口适配器 multipart 生命周期验证；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Tests for multipart abort on interrupted streaming uploads (audit批次C).

multipart 已开启后源流抛异常（超限截断/断连），不 abort 会在对象存储侧
留下长期挂起的 multipart 会话；适配器必须 best-effort abort 并重抛原异常。
"""

from __future__ import annotations

from typing import AsyncIterator, Optional

import pytest

from infrastructure.adapters.storage_port import StorageProviderPortAdapter
from infrastructure.external.storage.models import UploadResult

_PART = 5 * 1024 * 1024  # adapter 的分片/触发阈值


class _FakeAdvancedProvider:
    """满足 AdvancedStorageProvider runtime 协议的最小 fake。"""

    def __init__(self) -> None:
        self.started: list[str] = []
        self.aborted: list[tuple[str, str]] = []
        self.completed: list[str] = []
        self.parts_uploaded = 0

    # --- multipart ---
    async def multipart_upload_start(self, key: str, content_type: Optional[str] = None) -> str:
        self.started.append(key)
        return "upload-1"

    async def multipart_upload_part(
        self, key: str, upload_id: str, part_number: int, data: bytes
    ) -> str:
        self.parts_uploaded += 1
        return f"etag-{part_number}"

    async def multipart_upload_complete(self, upload_id: str, key: str, parts: list[dict]):
        self.completed.append(upload_id)
        return UploadResult(key=key, etag="final", size=0)

    async def multipart_upload_abort(self, upload_id: str, key: str) -> None:
        self.aborted.append((upload_id, key))

    # --- base protocol stubs（isinstance runtime 检查需要方法存在）---
    async def upload(self, data, key, metadata=None, content_type=None):
        return UploadResult(key=key, etag="small", size=len(data))

    async def download(self, key: str) -> bytes:  # pragma: no cover
        raise NotImplementedError

    async def stream_download(self, key: str, chunk_size: int = 8192):  # pragma: no cover
        raise NotImplementedError

    async def delete(self, key: str) -> bool:  # pragma: no cover
        return True

    async def exists(self, key: str) -> bool:  # pragma: no cover
        return False

    async def list_objects(self, prefix: str = "", limit: int = 1000):  # pragma: no cover
        return []

    async def get_metadata(self, key: str):  # pragma: no cover
        raise NotImplementedError

    async def generate_presigned_url(self, *args, **kwargs):  # pragma: no cover
        raise NotImplementedError

    async def copy(self, source_key: str, dest_key: str) -> bool:  # pragma: no cover
        return True

    async def move(self, source_key: str, dest_key: str) -> bool:  # pragma: no cover
        return True

    def public_url(self, key: str) -> Optional[str]:
        return None

    async def health_check(self) -> bool:  # pragma: no cover
        return True

    async def batch_upload(self, files, metadata=None):  # pragma: no cover
        return []

    async def batch_delete(self, keys):  # pragma: no cover
        return {}

    async def create_directory(self, path: str) -> bool:  # pragma: no cover
        return True

    async def delete_directory(
        self, path: str, recursive: bool = False
    ) -> bool:  # pragma: no cover
        return True


async def _exploding_stream() -> AsyncIterator[bytes]:
    # 先送满一个分片触发 multipart，再中断
    yield b"x" * _PART
    raise RuntimeError("client disconnected")


async def _small_stream() -> AsyncIterator[bytes]:
    yield b"hello"


async def test_stream_interruption_aborts_multipart() -> None:
    provider = _FakeAdvancedProvider()
    adapter = StorageProviderPortAdapter(provider)

    with pytest.raises(RuntimeError, match="client disconnected"):
        await adapter.upload_stream(_exploding_stream(), "k/big.bin")

    assert provider.started == ["k/big.bin"]
    assert provider.aborted == [("upload-1", "k/big.bin")]
    assert provider.completed == []


async def test_small_stream_uses_plain_upload_no_multipart() -> None:
    provider = _FakeAdvancedProvider()
    adapter = StorageProviderPortAdapter(provider)

    outcome = await adapter.upload_stream(_small_stream(), "k/small.txt")

    assert outcome.etag == "small"
    assert provider.started == []
    assert provider.aborted == []


async def test_happy_path_multipart_completes_without_abort() -> None:
    provider = _FakeAdvancedProvider()
    adapter = StorageProviderPortAdapter(provider)

    async def _big_stream() -> AsyncIterator[bytes]:
        yield b"x" * _PART
        yield b"y" * 10

    outcome = await adapter.upload_stream(_big_stream(), "k/big.bin")

    assert outcome.etag == "final"
    assert provider.completed == ["upload-1"]
    assert provider.aborted == []
