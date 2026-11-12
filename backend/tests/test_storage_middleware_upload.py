"""Characterization tests for MiddlewareStorage.upload.

重构（降 McCabe 复杂度 + 修 lint）前后必须同绿：断言 hook 的调用顺序与入参、
provider 收到的最终参数、异常对象身份与因果链、日志事件。
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, AsyncGenerator, AsyncIterator, Optional

import pytest
from structlog.testing import capture_logs

from infrastructure.external.storage import utils as storage_utils
from infrastructure.external.storage.exceptions import ValidationError
from infrastructure.external.storage.models import UploadResult
from infrastructure.external.storage.utils import (
    LoggingMiddleware,
    MetricsMiddleware,
    MiddlewareStorage,
    StorageMiddleware,
    ValidationMiddleware,
    calculate_etag,
    calculate_etag_stream,
)

_MD5_ABC = "900150983cd24fb0d6963f7d28e17f72"
_SHA256_ABC = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


class _FakeProvider:
    """只实现被 MiddlewareStorage.upload / stream_download 用到的方法。"""

    def __init__(self, error: Optional[Exception] = None) -> None:
        self.error = error
        self.calls: list[tuple[bytes, str, Optional[dict], Optional[str]]] = []

    async def upload(
        self,
        file: bytes,
        key: str,
        metadata: Optional[dict] = None,
        content_type: Optional[str] = None,
    ) -> UploadResult:
        self.calls.append((file, key, metadata, content_type))
        if self.error is not None:
            raise self.error
        return UploadResult(key=key, etag="etag", size=len(file), content_type=content_type)

    async def stream_download(self, key: str, chunk_size: int = 8192) -> AsyncIterator[bytes]:
        data = b"abcdef"
        for start in range(0, len(data), chunk_size):
            yield data[start : start + chunk_size]


class _RecordingMiddleware(StorageMiddleware):
    """把每次 hook 调用记进共享 events；可按需改写参数或在某个 hook 抛错。"""

    def __init__(
        self,
        name: str,
        events: list[tuple[Any, ...]],
        *,
        suffix: Optional[str] = None,
        fail_before: Optional[Exception] = None,
        fail_after: Optional[Exception] = None,
        fail_on_error: Optional[Exception] = None,
    ) -> None:
        self.name = name
        self.events = events
        self.suffix = suffix
        self.fail_before = fail_before
        self.fail_after = fail_after
        self.fail_on_error = fail_on_error

    async def before_upload(
        self,
        file: bytes,
        key: str,
        metadata: Optional[dict] = None,
        content_type: Optional[str] = None,
    ) -> tuple[bytes, str, Optional[dict], Optional[str]]:
        self.events.append((self.name, "before", file, key, metadata, content_type))
        if self.fail_before is not None:
            raise self.fail_before
        if self.suffix is None:
            return file, key, metadata, content_type
        return (
            file + self.suffix.encode(),
            f"{key}.{self.suffix}",
            {**(metadata or {}), self.name: self.suffix},
            f"{content_type}+{self.suffix}",
        )

    async def after_upload(self, result: UploadResult, file: bytes, key: str) -> UploadResult:
        self.events.append((self.name, "after", result.etag, file, key))
        if self.fail_after is not None:
            raise self.fail_after
        return result.model_copy(update={"etag": f"{result.etag}>{self.name}"})

    async def on_error(self, error: Exception, operation: str, **kwargs: Any) -> None:
        self.events.append((self.name, "on_error", error, operation, kwargs))
        if self.fail_on_error is not None:
            raise self.fail_on_error


def _storage(provider: Any, *middlewares: StorageMiddleware) -> MiddlewareStorage:
    return MiddlewareStorage(provider, list(middlewares))


def _perf_log(key: str, size: int) -> dict[str, Any]:
    return {
        "event": "Storage upload performance",
        "log_level": "info",
        "key": key,
        "elapsed_ms": "250.00",
        "size": size,
    }


@pytest.fixture
def fixed_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    """upload 内恰好读两次时钟：开始 100.0s、结束 100.25s → elapsed_ms "250.00"。"""
    ticks = iter([100.0, 100.25])
    monkeypatch.setattr(storage_utils, "time", SimpleNamespace(time=lambda: next(ticks)))


# ── MiddlewareStorage.upload：成功路径 ─────────────────────────────────


async def test_upload_without_middlewares_returns_provider_result_and_logs_timing(
    fixed_clock: None,
) -> None:
    provider = _FakeProvider()

    with capture_logs() as logs:
        result = await _storage(provider).upload(b"data", "k", {"m": "1"}, "text/plain")

    assert result == UploadResult(key="k", etag="etag", size=4, content_type="text/plain")
    assert provider.calls == [(b"data", "k", {"m": "1"}, "text/plain")]
    assert logs == [_perf_log("k", 4)]


async def test_upload_threads_values_through_before_and_after_hooks_in_order(
    fixed_clock: None,
) -> None:
    events: list[tuple[Any, ...]] = []
    provider = _FakeProvider()
    storage = _storage(
        provider,
        _RecordingMiddleware("mw1", events, suffix="a"),
        _RecordingMiddleware("mw2", events, suffix="b"),
    )

    with capture_logs() as logs:
        result = await storage.upload(b"x", "k", None, "text/plain")

    assert events == [
        ("mw1", "before", b"x", "k", None, "text/plain"),
        ("mw2", "before", b"xa", "k.a", {"mw1": "a"}, "text/plain+a"),
        ("mw1", "after", "etag", b"xab", "k.a.b"),
        ("mw2", "after", "etag>mw1", b"xab", "k.a.b"),
    ]
    assert provider.calls == [(b"xab", "k.a.b", {"mw1": "a", "mw2": "b"}, "text/plain+a+b")]
    assert result.etag == "etag>mw1>mw2"
    assert logs == [_perf_log("k.a.b", 3)]


# ── MiddlewareStorage.upload：三个阶段的失败 ───────────────────────────


async def test_before_upload_failure_notifies_every_middleware_and_reraises(
    fixed_clock: None,
) -> None:
    events: list[tuple[Any, ...]] = []
    err = RuntimeError("rejected")
    provider = _FakeProvider()
    storage = _storage(
        provider,
        _RecordingMiddleware("mw1", events, suffix="a"),
        _RecordingMiddleware("mw2", events, fail_before=err),
        _RecordingMiddleware("mw3", events),
    )

    with capture_logs() as logs, pytest.raises(RuntimeError) as info:
        await storage.upload(b"x", "k")

    assert info.value is err
    assert events == [
        ("mw1", "before", b"x", "k", None, None),
        ("mw2", "before", b"xa", "k.a", {"mw1": "a"}, "None+a"),
        ("mw1", "on_error", err, "before_upload", {"key": "k.a"}),
        ("mw2", "on_error", err, "before_upload", {"key": "k.a"}),
        ("mw3", "on_error", err, "before_upload", {"key": "k.a"}),
    ]
    assert provider.calls == []
    assert logs == []


async def test_provider_failure_notifies_every_middleware_with_upload_operation(
    fixed_clock: None,
) -> None:
    events: list[tuple[Any, ...]] = []
    err = OSError("bucket down")
    storage = _storage(
        _FakeProvider(error=err),
        _RecordingMiddleware("mw1", events, suffix="a"),
        _RecordingMiddleware("mw2", events),
    )

    with capture_logs() as logs, pytest.raises(OSError) as info:
        await storage.upload(b"x", "k")

    assert info.value is err
    assert events[2:] == [
        ("mw1", "on_error", err, "upload", {"key": "k.a"}),
        ("mw2", "on_error", err, "upload", {"key": "k.a"}),
    ]
    assert [event[1] for event in events] == ["before", "before", "on_error", "on_error"]
    assert logs == []


async def test_after_upload_failure_notifies_every_middleware_and_skips_remaining_hooks(
    fixed_clock: None,
) -> None:
    events: list[tuple[Any, ...]] = []
    err = ValueError("bad result")
    storage = _storage(
        _FakeProvider(),
        _RecordingMiddleware("mw1", events, fail_after=err),
        _RecordingMiddleware("mw2", events),
    )

    with capture_logs() as logs, pytest.raises(ValueError) as info:
        await storage.upload(b"x", "k")

    assert info.value is err
    assert events[2:] == [
        ("mw1", "after", "etag", b"x", "k"),
        ("mw1", "on_error", err, "after_upload", {"key": "k"}),
        ("mw2", "on_error", err, "after_upload", {"key": "k"}),
    ]
    assert logs == [_perf_log("k", 1)]


async def test_failing_on_error_hook_replaces_error_and_stops_notification(
    fixed_clock: None,
) -> None:
    events: list[tuple[Any, ...]] = []
    err = OSError("bucket down")
    hook_err = RuntimeError("hook broke")
    storage = _storage(
        _FakeProvider(error=err),
        _RecordingMiddleware("mw1", events, fail_on_error=hook_err),
        _RecordingMiddleware("mw2", events),
    )

    with pytest.raises(RuntimeError) as info:
        await storage.upload(b"x", "k")

    assert info.value is hook_err
    assert info.value.__context__ is err
    assert [event[:2] for event in events] == [
        ("mw1", "before"),
        ("mw2", "before"),
        ("mw1", "on_error"),
    ]


# ── 与真实 middleware 组合 ────────────────────────────────────────────


async def test_real_middlewares_log_and_count_a_rejected_upload() -> None:
    provider = _FakeProvider()
    metrics = MetricsMiddleware()
    storage = _storage(provider, LoggingMiddleware(), ValidationMiddleware(max_size=3), metrics)

    with capture_logs() as logs, pytest.raises(ValidationError, match=r"^File too large: 4 > 3$"):
        await storage.upload(b"data", "k", content_type="text/plain")

    assert provider.calls == []
    assert metrics.error_count == 1
    assert logs == [
        {
            "event": "Storage upload starting",
            "log_level": "info",
            "key": "k",
            "size": 4,
            "content_type": "text/plain",
        },
        {
            "event": "Storage operation failed",
            "log_level": "error",
            "operation": "before_upload",
            "error": "File too large: 4 > 3",
            "key": "k",
        },
    ]


async def test_real_middlewares_log_and_measure_a_successful_upload(fixed_clock: None) -> None:
    metrics = MetricsMiddleware()
    storage = _storage(_FakeProvider(), LoggingMiddleware(), metrics)

    with capture_logs() as logs:
        await storage.upload(b"data", "k")

    assert metrics.upload_sizes == [4]
    assert metrics.error_count == 0
    assert logs == [
        {
            "event": "Storage upload starting",
            "log_level": "info",
            "key": "k",
            "size": 4,
            "content_type": None,
        },
        _perf_log("k", 4),
        {
            "event": "Storage upload completed",
            "log_level": "info",
            "key": "k",
            "size": 4,
            "etag": "etag",
            "url": None,
        },
    ]


@pytest.mark.parametrize(
    ("allowed", "content_type", "error"),
    [
        (["image/png"], "image/png", None),
        (["image/png"], "text/plain", "Content type not allowed: text/plain"),
        (["image/png"], None, None),
        (None, "text/plain", None),
        ([], "text/plain", None),
    ],
    ids=["allowed", "rejected", "no-content-type", "no-allowlist", "empty-allowlist"],
)
async def test_validation_middleware_content_type_rules(
    allowed: Optional[list[str]], content_type: Optional[str], error: Optional[str]
) -> None:
    middleware = ValidationMiddleware(max_size=4, allowed_types=allowed)

    if error is None:
        result = await middleware.before_upload(b"data", "k", None, content_type)
        assert result == (b"data", "k", None, content_type)
    else:
        with pytest.raises(ValidationError, match=f"^{error}$"):
            await middleware.before_upload(b"data", "k", None, content_type)


async def test_stream_download_delegates_chunks_to_provider() -> None:
    storage = _storage(_FakeProvider())

    chunks = [chunk async for chunk in storage.stream_download("k", 4)]

    assert chunks == [b"abcd", b"ef"]


# ── ETag 工具（md5 调用改为 usedforsecurity=False，摘要必须不变）──────────


@pytest.mark.parametrize(("algorithm", "expected"), [("md5", _MD5_ABC), ("sha256", _SHA256_ABC)])
def test_calculate_etag_digests(algorithm: str, expected: str) -> None:
    assert calculate_etag(b"abc", algorithm) == expected


def test_calculate_etag_defaults_to_md5_and_rejects_unknown_algorithm() -> None:
    assert calculate_etag(b"abc") == _MD5_ABC
    with pytest.raises(ValueError, match="^Unsupported algorithm: sha1$"):
        calculate_etag(b"abc", "sha1")


async def _chunks() -> AsyncGenerator[bytes, None]:
    yield b"a"
    yield b"bc"


@pytest.mark.parametrize(("algorithm", "expected"), [("md5", _MD5_ABC), ("sha256", _SHA256_ABC)])
async def test_calculate_etag_stream_digests(algorithm: str, expected: str) -> None:
    assert await calculate_etag_stream(_chunks(), algorithm) == expected


async def test_calculate_etag_stream_rejects_unknown_algorithm() -> None:
    stream = _chunks()
    with pytest.raises(ValueError, match="^Unsupported algorithm: sha1$"):
        await calculate_etag_stream(stream, "sha1")
    await stream.aclose()
