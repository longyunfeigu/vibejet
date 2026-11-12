"""OSSProvider 的 not-found 映射。

HEAD 类请求（get_object_meta）的 404 响应没有 body；不带 x-oss-err 头时 oss2 解析不出
错误码，只能抛裸 ``oss2.exceptions.NotFound``（NoSuchKey 的父类）。它必须与 NoSuchKey
一样映射为存储层 NotFoundError，否则 /storage/complete 在对象未上传时变成 500 而不是 409。
"""

from __future__ import annotations

from typing import Any

import oss2
import pytest

from infrastructure.external.storage.config import StorageConfig, StorageType
from infrastructure.external.storage.exceptions import NotFoundError, StorageError
from infrastructure.external.storage.providers.oss import OSSProvider


class _Resp:
    """oss2.exceptions.make_exception 需要的最小 HTTP 响应替身。"""

    def __init__(self, status: int, body: bytes = b"", headers: dict[str, str] | None = None):
        self.status = status
        self.headers = headers or {}
        self._body = body

    def read(self, amt: int = -1) -> bytes:
        return self._body


def _oss_error(status: int, body: bytes = b"") -> oss2.exceptions.OssError:
    return oss2.exceptions.make_exception(_Resp(status, body, {"x-oss-request-id": "req-1"}))


def _error_body(code: str) -> bytes:
    return f"<Error><Code>{code}</Code><Message>m</Message></Error>".encode()


class _Bucket:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def get_object_meta(self, key: str) -> Any:
        raise self._exc


def _provider(exc: Exception) -> OSSProvider:
    return OSSProvider(_Bucket(exc), StorageConfig(type=StorageType.OSS, bucket="bucket-a"))


def test_bodyless_404_is_bare_not_found_in_installed_oss2() -> None:
    """前提：HEAD 的无 body 404 在 oss2 里是 NotFound 而非 NoSuchKey。"""
    exc = _oss_error(404)
    assert type(exc) is oss2.exceptions.NotFound
    assert issubclass(oss2.exceptions.NoSuchKey, oss2.exceptions.NotFound)


@pytest.mark.parametrize(
    "exc",
    [_oss_error(404), _oss_error(404, _error_body("NoSuchKey"))],
    ids=["head-bare-not-found", "no-such-key"],
)
async def test_get_metadata_maps_object_404_to_not_found(exc: Exception) -> None:
    with pytest.raises(NotFoundError):
        await _provider(exc).get_metadata("uploads/missing.bin")


async def test_no_such_bucket_stays_a_storage_error() -> None:
    """桶不存在是配置错误，不能伪装成"对象尚未上传"（409）。"""
    exc = _oss_error(404, _error_body("NoSuchBucket"))
    assert isinstance(exc, oss2.exceptions.NoSuchBucket)

    with pytest.raises(StorageError) as exc_info:
        await _provider(exc).get_metadata("uploads/x.bin")
    assert not isinstance(exc_info.value, NotFoundError)
