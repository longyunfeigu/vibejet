"""Characterization tests for S3Provider.upload and the S3 error mapping.

重构（降 McCabe 复杂度 + 修 lint）前后必须同绿：断言的是可观察行为——
发给 SDK 的参数、返回的 UploadResult、抛出的异常类型/消息/因果链、日志事件。
"""

from __future__ import annotations

import hashlib
import threading
from typing import Any, Optional

import pytest
from botocore.exceptions import ClientError
from structlog.testing import capture_logs

from infrastructure.external.storage.config import StorageConfig, StorageType
from infrastructure.external.storage.exceptions import (
    NotFoundError,
    PermissionDeniedError,
    StorageError,
    TransientError,
)
from infrastructure.external.storage.providers.s3 import S3Provider

_SERVER_ETAG = {"ETag": '"server-etag"'}
_PAYLOAD_MD5 = hashlib.md5(b"payload", usedforsecurity=False).hexdigest()


class _FakeBody:
    """boto3 StreamingBody 的最小替身：按块读取，记录 close。"""

    def __init__(
        self,
        data: bytes = b"",
        read_error: Optional[Exception] = None,
        close_error: Optional[Exception] = None,
    ) -> None:
        self._data = data
        self._read_error = read_error
        self._close_error = close_error
        self.closed = False

    def read(self, size: int = -1) -> bytes:
        if self._read_error is not None:
            raise self._read_error
        if size < 0:
            size = len(self._data)
        chunk, self._data = self._data[:size], self._data[size:]
        return chunk

    def close(self) -> None:
        self.closed = True
        if self._close_error is not None:
            raise self._close_error


class _FakeS3Client:
    """boto3 S3 client 替身：记录每次调用的方法名、kwargs 与执行线程。"""

    def __init__(
        self,
        put_response: Any = _SERVER_ETAG,
        error: Optional[Exception] = None,
        body: Optional[_FakeBody] = None,
    ) -> None:
        self.put_response = put_response
        self.error = error
        self.body = body or _FakeBody()
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.threads: list[int] = []

    def _record(self, name: str, kwargs: dict[str, Any]) -> None:
        self.calls.append((name, kwargs))
        self.threads.append(threading.get_ident())
        if self.error is not None:
            raise self.error

    def put_object(self, **kwargs: Any) -> Any:
        self._record("put_object", kwargs)
        return self.put_response

    def get_object(self, **kwargs: Any) -> dict[str, Any]:
        self._record("get_object", kwargs)
        return {"Body": self.body}

    def delete_object(self, **kwargs: Any) -> dict[str, Any]:
        self._record("delete_object", kwargs)
        return {}

    def copy_object(self, **kwargs: Any) -> dict[str, Any]:
        self._record("copy_object", kwargs)
        return {}

    def head_bucket(self, **kwargs: Any) -> dict[str, Any]:
        self._record("head_bucket", kwargs)
        return {}

    def create_multipart_upload(self, **kwargs: Any) -> dict[str, Any]:
        self._record("create_multipart_upload", kwargs)
        return {"UploadId": "upload-1"}

    def upload_part(self, **kwargs: Any) -> dict[str, Any]:
        self._record("upload_part", kwargs)
        return {"ETag": '"part-etag"'}

    def generate_presigned_url(self, **kwargs: Any) -> str:
        self._record("generate_presigned_url", kwargs)
        return "https://s3.example/signed"

    def generate_presigned_post(self, **kwargs: Any) -> dict[str, Any]:
        self._record("generate_presigned_post", kwargs)
        return {"url": "https://s3.example/post", "fields": {"key": kwargs["Key"]}}


def _provider(client: _FakeS3Client, **config: Any) -> S3Provider:
    return S3Provider(client, StorageConfig(type=StorageType.S3, bucket="bucket-a", **config))


def _client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": "boom"}}, "PutObject")


class _ResponseIsNoneError(Exception):
    """模拟带 response 属性但值为 None 的第三方异常。"""

    response = None


# ── upload：发给 SDK 的参数 ─────────────────────────────────────────────


async def test_upload_sends_every_optional_put_object_arg() -> None:
    client = _FakeS3Client()
    provider = _provider(client, s3_sse="AES256")  # s3_acl 默认 "private"

    await provider.upload(b"data", "docs/a.png", metadata={"owner": "u1"}, content_type="image/png")

    assert client.calls == [
        (
            "put_object",
            {
                "Bucket": "bucket-a",
                "Key": "docs/a.png",
                "Body": b"data",
                "ContentType": "image/png",
                "Metadata": {"owner": "u1"},
                "ACL": "private",
                "ServerSideEncryption": "AES256",
            },
        )
    ]


@pytest.mark.parametrize("acl", [None, ""])
async def test_upload_omits_falsy_optional_args(acl: Optional[str]) -> None:
    client = _FakeS3Client()

    await _provider(client, s3_acl=acl).upload(b"data", "k", metadata={}, content_type=None)

    assert client.calls == [("put_object", {"Bucket": "bucket-a", "Key": "k", "Body": b"data"})]


async def test_upload_runs_sync_sdk_call_in_worker_thread() -> None:
    client = _FakeS3Client()

    await _provider(client).upload(b"x", "k")

    assert len(client.threads) == 1
    assert client.threads[0] != threading.get_ident()


# ── upload：返回值 ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        ({"ETag": '"abc123"'}, "abc123"),
        ({"ETag": "abc123"}, "abc123"),
        ({"ETag": '""'}, _PAYLOAD_MD5),
        ({}, _PAYLOAD_MD5),
        (None, _PAYLOAD_MD5),
        ({"ETag": None}, _PAYLOAD_MD5),
        ({"ETag": 123}, _PAYLOAD_MD5),
        ("not-a-mapping", _PAYLOAD_MD5),
    ],
    ids=[
        "quoted",
        "unquoted",
        "empty-quotes",
        "missing",
        "none-response",
        "none-etag",
        "non-str-etag",
        "non-mapping-response",
    ],
)
async def test_upload_etag_prefers_server_value_then_local_md5(
    response: Any, expected: str
) -> None:
    result = await _provider(_FakeS3Client(put_response=response)).upload(b"payload", "k")

    assert result.etag == expected


@pytest.mark.parametrize("content_type", ["text/plain", None])
async def test_upload_result_reports_key_size_and_content_type(content_type: Optional[str]) -> None:
    result = await _provider(_FakeS3Client()).upload(b"12345", "a/b.txt", content_type=content_type)

    assert (result.key, result.size, result.content_type) == ("a/b.txt", 5, content_type)


@pytest.mark.parametrize(
    ("config", "expected_url"),
    [
        ({"public_base_url": "https://cdn.example.com"}, "https://cdn.example.com/a/b.txt"),
        (
            {"public_base_url": "https://cdn.example.com", "s3_acl": "public-read"},
            "https://cdn.example.com/a/b.txt",
        ),
        ({"s3_acl": "public-read"}, "https://bucket-a.s3.us-east-1.amazonaws.com/a/b.txt"),
        (
            {"s3_acl": "public-read", "region": "eu-west-1"},
            "https://bucket-a.s3.eu-west-1.amazonaws.com/a/b.txt",
        ),
        (
            {"s3_acl": "public-read", "public_base_url": ""},
            "https://bucket-a.s3.us-east-1.amazonaws.com/a/b.txt",
        ),
    ],
    ids=["cdn", "cdn-wins-over-public-acl", "public-acl", "public-acl-region", "empty-cdn"],
)
async def test_upload_attaches_stable_public_url(config: dict[str, Any], expected_url: str) -> None:
    result = await _provider(_FakeS3Client(), **config).upload(b"x", "a/b.txt")

    assert result.url == expected_url


async def test_upload_leaves_url_unset_for_private_bucket() -> None:
    result = await _provider(_FakeS3Client()).upload(b"x", "k")

    assert result.url is None
    assert "url" not in result.model_fields_set


async def test_upload_logs_success_event() -> None:
    with capture_logs() as logs:
        await _provider(_FakeS3Client()).upload(b"data", "k")

    assert logs == [{"event": "Uploaded to S3", "log_level": "info", "key": "k", "size": 4}]


# ── upload：异常映射 ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("code", "exc_type", "message"),
    [
        ("NoSuchKey", NotFoundError, "Object not found: upload k"),
        ("404", NotFoundError, "Object not found: upload k"),
        ("AccessDenied", PermissionDeniedError, "Access denied: upload k"),
        ("403", PermissionDeniedError, "Access denied: upload k"),
    ],
)
async def test_upload_maps_missing_and_denied_codes(
    code: str, exc_type: type[StorageError], message: str
) -> None:
    err = _client_error(code)

    with capture_logs() as logs, pytest.raises(exc_type) as info:
        await _provider(_FakeS3Client(error=err)).upload(b"x", "k")

    assert type(info.value) is exc_type
    assert str(info.value) == message
    assert info.value.__cause__ is None
    assert info.value.__context__ is err
    assert logs == []


@pytest.mark.parametrize("code", ["RequestTimeout", "SlowDown", "ServiceUnavailable"])
async def test_upload_maps_throttling_codes_to_transient(code: str) -> None:
    err = _client_error(code)

    with pytest.raises(TransientError) as info:
        await _provider(_FakeS3Client(error=err)).upload(b"x", "k")

    assert type(info.value) is TransientError
    assert str(info.value) == f"Transient error: upload k: {err}"
    assert info.value.__cause__ is None
    assert info.value.__context__ is err


@pytest.mark.parametrize(
    "err",
    [_client_error("InternalError"), RuntimeError("socket closed")],
    ids=["unknown-aws-code", "non-aws-error"],
)
async def test_upload_wraps_other_errors_in_storage_error(err: Exception) -> None:
    with pytest.raises(StorageError) as info:
        await _provider(_FakeS3Client(error=err)).upload(b"x", "k")

    assert type(info.value) is StorageError
    assert str(info.value) == f"S3 error during upload k: {err}"
    assert info.value.__cause__ is err


async def test_upload_error_whose_response_is_none_maps_to_storage_error() -> None:
    """e.response 为 None 的第三方异常同样归为通用 StorageError，而不是让映射函数自身崩掉。"""
    err = _ResponseIsNoneError("x")
    with pytest.raises(StorageError) as info:
        await _provider(_FakeS3Client(error=err)).upload(b"x", "k")

    assert type(info.value) is StorageError
    assert info.value.__cause__ is err


# ── 同文件 lint 修复触及的方法（f-string / contextlib.suppress / 返回类型）──


async def test_download_returns_body_logs_and_closes_it() -> None:
    body = _FakeBody(b"hello")
    client = _FakeS3Client(body=body)

    with capture_logs() as logs:
        data = await _provider(client).download("k")

    assert data == b"hello"
    assert body.closed
    assert client.calls == [("get_object", {"Bucket": "bucket-a", "Key": "k"})]
    assert logs == [{"event": "Downloaded from S3", "log_level": "info", "key": "k", "size": 5}]


async def test_download_swallows_body_close_failure() -> None:
    body = _FakeBody(b"hello", close_error=OSError("close failed"))

    assert await _provider(_FakeS3Client(body=body)).download("k") == b"hello"


async def test_download_read_failure_is_mapped_and_body_still_closed() -> None:
    body = _FakeBody(read_error=_client_error("NoSuchKey"))

    with pytest.raises(NotFoundError, match="^Object not found: download k$"):
        await _provider(_FakeS3Client(body=body)).download("k")

    assert body.closed


async def test_stream_download_yields_chunks_and_swallows_close_failure() -> None:
    body = _FakeBody(b"abcdefg", close_error=OSError("close failed"))
    provider = _provider(_FakeS3Client(body=body))

    chunks = [chunk async for chunk in provider.stream_download("k", chunk_size=3)]

    assert chunks == [b"abc", b"def", b"g"]
    assert body.closed


async def test_delete_copy_and_health_check_log_events() -> None:
    provider = _provider(_FakeS3Client())

    with capture_logs() as logs:
        assert await provider.delete("k") is True
        assert await provider.copy("src", "dst") is True
        assert await provider.health_check() is True

    assert logs == [
        {"event": "Deleted from S3", "log_level": "info", "key": "k"},
        {"event": "Copied in S3", "log_level": "info", "source": "src", "dest": "dst"},
        {"event": "S3 health check passed", "log_level": "info"},
    ]


async def test_health_check_failure_logs_and_returns_false() -> None:
    provider = _provider(_FakeS3Client(error=RuntimeError("unreachable")))

    with capture_logs() as logs:
        assert await provider.health_check() is False

    assert logs == [
        {"event": "S3 health check failed", "log_level": "error", "error": "unreachable"}
    ]


async def test_multipart_start_and_part_return_raw_sdk_identifiers() -> None:
    client = _FakeS3Client()
    provider = _provider(client)

    assert await provider.multipart_upload_start("k", content_type="video/mp4") == "upload-1"
    assert await provider.multipart_upload_part("k", "upload-1", 1, b"x") == '"part-etag"'
    assert client.calls == [
        ("create_multipart_upload", {"Bucket": "bucket-a", "Key": "k", "ContentType": "video/mp4"}),
        (
            "upload_part",
            {
                "Bucket": "bucket-a",
                "Key": "k",
                "UploadId": "upload-1",
                "PartNumber": 1,
                "Body": b"x",
            },
        ),
    ]


# ── generate_presigned_url：直传大小绑定 ─────────────────────────────────


async def test_presign_put_signs_content_length_when_size_given() -> None:
    client = _FakeS3Client()

    await _provider(client).generate_presigned_url(
        "uploads/a.txt", 600, "PUT", "text/plain", content_length=5
    )

    assert client.calls == [
        (
            "generate_presigned_url",
            {
                "ClientMethod": "put_object",
                "Params": {
                    "Bucket": "bucket-a",
                    "Key": "uploads/a.txt",
                    "ContentType": "text/plain",
                    "ContentLength": 5,
                },
                "ExpiresIn": 600,
            },
        )
    ]


async def test_presign_put_omits_content_length_when_size_unknown() -> None:
    client = _FakeS3Client()

    await _provider(client).generate_presigned_url("uploads/a.txt", 600, "PUT", "text/plain")

    assert "ContentLength" not in client.calls[0][1]["Params"]


async def test_presign_post_binds_exact_content_length_range() -> None:
    client = _FakeS3Client()

    await _provider(client).generate_presigned_url(
        "uploads/a.txt", 600, "POST", "text/plain", content_length=5
    )

    name, kwargs = client.calls[0]
    assert name == "generate_presigned_post"
    assert kwargs["Fields"] == {"Content-Type": "text/plain"}
    assert kwargs["Conditions"] == [
        {"Content-Type": "text/plain"},
        ["content-length-range", 5, 5],
    ]


def test_real_boto3_presign_put_signs_content_length_header() -> None:
    """真 botocore（s3v4，与 build 配置一致）：ContentLength 进入 X-Amz-SignedHeaders。"""
    import boto3
    from botocore.config import Config

    client = boto3.client(
        "s3",
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",  # nosec B106 - offline signing only
        config=Config(signature_version="s3v4"),
    )
    url = client.generate_presigned_url(
        "put_object",
        Params={"Bucket": "b", "Key": "k", "ContentType": "text/plain", "ContentLength": 5},
        ExpiresIn=60,
    )

    assert "X-Amz-SignedHeaders=content-length%3Bcontent-type%3Bhost" in url
