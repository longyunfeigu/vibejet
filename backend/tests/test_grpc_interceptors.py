# input: grpc_app.interceptors.{exceptions,logging,request_id} + 假 ServicerContext / 进程内 grpc.aio server
# output: gRPC 异常映射与日志拦截器特征测试：业务码→status、trailing metadata、映射标记、重复日志抑制、耗时日志、真实调用链
# pos: 后端测试 - gRPC 拦截器行为基线（重构前后行为一致的保护网）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Characterization tests for ExceptionMappingInterceptor and LoggingInterceptor."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, Awaitable, Callable, Iterator

import grpc
import pytest
import structlog
from structlog.testing import capture_logs

from domain.common.exceptions import BusinessException, UserNotFoundException
from grpc_app.interceptors import exceptions as grpc_exceptions
from grpc_app.interceptors import logging as grpc_logging
from grpc_app.interceptors.exceptions import (
    ExceptionMappingInterceptor,
    is_mapped_error,
    set_mapped_error,
)
from grpc_app.interceptors.logging import LoggingInterceptor
from grpc_app.interceptors.request_id import RequestIdInterceptor, _request_id_var
from shared.codes import BusinessCode

METHOD = "/test.Svc/Call"
Status = grpc.StatusCode
Behavior = Callable[[Any, Any], Awaitable[Any]]


@pytest.fixture
def logs(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[dict[str, Any]]]:
    """捕获两个拦截器的日志；换成新的 lazy logger，避免 cache_logger_on_first_use 绕过捕获。"""
    with capture_logs() as captured:
        for module in (grpc_exceptions, grpc_logging):
            monkeypatch.setattr(module, "logger", structlog.get_logger(module.__name__))
        yield captured


class FakeAbort(Exception):
    """模拟 context.abort() 抛出的 AbortError。"""


class FakeContext:
    def __init__(self, *, trailing_error: Exception | None = None) -> None:
        self.trailing_metadata: Any = None
        self.aborted: tuple[Any, str] | None = None
        self._trailing_error = trailing_error

    def peer(self) -> str:
        return "ipv4:127.0.0.1:5000"

    def set_trailing_metadata(self, metadata: Any) -> None:
        if self._trailing_error is not None:
            raise self._trailing_error
        self.trailing_metadata = metadata

    async def abort(self, code: Any, details: str) -> None:
        self.aborted = (code, details)
        raise FakeAbort(details)


def _identity(data: bytes) -> bytes:
    return data


def unary(behavior: Behavior) -> Any:
    return grpc.unary_unary_rpc_method_handler(
        behavior, request_deserializer=_identity, response_serializer=_identity
    )


def raising(exc: BaseException) -> Behavior:
    async def behavior(request: Any, context: Any) -> Any:
        raise exc

    return behavior


async def echo(request: Any, context: Any) -> Any:
    return b"resp:" + request


async def intercept(interceptor: Any, handler: Any) -> Any:
    async def continuation(details: Any) -> Any:
        assert details.method == METHOD
        return handler

    details = SimpleNamespace(method=METHOD, invocation_metadata=())
    return await interceptor.intercept_service(continuation, details)


async def call(interceptor: Any, behavior: Behavior, context: Any) -> Any:
    wrapped = await intercept(interceptor, unary(behavior))
    return await wrapped.unary_unary(b"req", context)


# ----------------------------------------------------------------------
# 两个拦截器共同的装配行为
# ----------------------------------------------------------------------


@pytest.mark.parametrize("interceptor_cls", [ExceptionMappingInterceptor, LoggingInterceptor])
async def test_missing_handler_is_returned_as_is(interceptor_cls: Any) -> None:
    assert await intercept(interceptor_cls(), None) is None


@pytest.mark.parametrize("interceptor_cls", [ExceptionMappingInterceptor, LoggingInterceptor])
async def test_streaming_handler_is_not_wrapped(interceptor_cls: Any) -> None:
    async def stream(request: Any, context: Any) -> Any:
        yield request

    handler = grpc.unary_stream_rpc_method_handler(stream)

    assert await intercept(interceptor_cls(), handler) is handler


@pytest.mark.parametrize("interceptor_cls", [ExceptionMappingInterceptor, LoggingInterceptor])
async def test_unary_handler_is_wrapped_with_same_serializers(interceptor_cls: Any) -> None:
    original = unary(echo)

    wrapped = await intercept(interceptor_cls(), original)

    assert wrapped is not original
    assert wrapped.unary_unary is not original.unary_unary
    assert wrapped.request_deserializer is _identity
    assert wrapped.response_serializer is _identity
    assert wrapped.request_streaming is False
    assert wrapped.response_streaming is False
    assert await wrapped.unary_unary(b"req", FakeContext()) == b"resp:req"


# ----------------------------------------------------------------------
# ExceptionMappingInterceptor
# ----------------------------------------------------------------------


async def test_success_is_returned_without_side_effects(logs: list[dict[str, Any]]) -> None:
    context = FakeContext()

    assert await call(ExceptionMappingInterceptor(), echo, context) == b"resp:req"

    assert context.trailing_metadata is None
    assert context.aborted is None
    assert logs == []
    assert is_mapped_error() is False


BUSINESS_STATUS = [
    (BusinessCode.PARAM_VALIDATION_ERROR, Status.INVALID_ARGUMENT),
    (BusinessCode.PARAM_ERROR, Status.INVALID_ARGUMENT),
    (BusinessCode.PARAM_MISSING, Status.INVALID_ARGUMENT),
    (BusinessCode.PARAM_TYPE_ERROR, Status.INVALID_ARGUMENT),
    (BusinessCode.USER_NOT_FOUND, Status.NOT_FOUND),
    (BusinessCode.NOT_FOUND, Status.NOT_FOUND),
    (BusinessCode.CONVERSATION_NOT_FOUND, Status.NOT_FOUND),
    (BusinessCode.DOCUMENT_NOT_FOUND, Status.NOT_FOUND),
    (BusinessCode.USER_ALREADY_EXISTS, Status.ALREADY_EXISTS),
    (BusinessCode.PASSWORD_ERROR, Status.UNAUTHENTICATED),
    (BusinessCode.UNAUTHORIZED, Status.UNAUTHENTICATED),
    (BusinessCode.FORBIDDEN, Status.PERMISSION_DENIED),
    (BusinessCode.PERMISSION_ERROR, Status.PERMISSION_DENIED),
    (BusinessCode.TOO_MANY_REQUESTS, Status.RESOURCE_EXHAUSTED),
    (BusinessCode.RATE_LIMIT_ERROR, Status.RESOURCE_EXHAUSTED),
    (BusinessCode.SERVICE_UNAVAILABLE, Status.UNAVAILABLE),
    (BusinessCode.SYSTEM_ERROR, Status.INTERNAL),
    (BusinessCode.DATABASE_ERROR, Status.INTERNAL),
    (BusinessCode.NETWORK_ERROR, Status.UNAVAILABLE),
    (
        BusinessCode.RUN_NOT_FOUND,
        Status.NOT_FOUND,
    ),  # master 的统一登记表补登了它（以前漏登记、落到默认值）
    (999_999, Status.FAILED_PRECONDITION),  # 不是 BusinessCode
]


@pytest.mark.parametrize("code, status", BUSINESS_STATUS)
async def test_business_exception_is_mapped_and_aborted(
    code: int, status: Any, logs: list[dict[str, Any]]
) -> None:
    _request_id_var.set("rid-1")
    exc = BusinessException(code=code, message="业务失败", error_type="SomeError")
    context = FakeContext()

    with pytest.raises(FakeAbort) as caught:
        await call(ExceptionMappingInterceptor(), raising(exc), context)

    assert caught.value.__context__ is exc
    assert context.aborted == (status, "业务失败")
    assert context.trailing_metadata == (
        ("x-biz-code", str(code)),
        ("x-error-type", "SomeError"),
    )
    assert logs == [
        {
            "event": "grpc_mapped_error",
            "log_level": "error",
            "method": METHOD,
            "code": str(code),
            "status": str(status),
            "message": "业务失败",
            "request_id": "rid-1",
        }
    ]
    assert is_mapped_error() is True


async def test_domain_exception_subclass_uses_its_code_and_type(
    logs: list[dict[str, Any]],
) -> None:
    context = FakeContext()

    with pytest.raises(FakeAbort):
        await call(ExceptionMappingInterceptor(), raising(UserNotFoundException("u1")), context)

    assert context.aborted == (Status.NOT_FOUND, "User not found")
    assert context.trailing_metadata == (("x-biz-code", "20001"), ("x-error-type", "UserNotFound"))
    assert logs[0]["code"] == "20001"
    assert logs[0]["status"] == "StatusCode.NOT_FOUND"
    assert logs[0]["request_id"] is None


@pytest.mark.parametrize("error_type", ["", None])
async def test_business_exception_without_error_type_falls_back(error_type: Any) -> None:
    exc = BusinessException(code=BusinessCode.NOT_FOUND, message="m")
    exc.error_type = error_type
    context = FakeContext()

    with pytest.raises(FakeAbort):
        await call(ExceptionMappingInterceptor(), raising(exc), context)

    assert context.trailing_metadata == (("x-biz-code", "20004"), ("x-error-type", "BusinessError"))


async def test_unexpected_exception_is_mapped_to_internal(logs: list[dict[str, Any]]) -> None:
    exc = RuntimeError("db exploded")
    context = FakeContext()

    with pytest.raises(FakeAbort) as caught:
        await call(ExceptionMappingInterceptor(), raising(exc), context)

    assert caught.value.__context__ is exc
    assert context.aborted == (Status.INTERNAL, "系统内部错误")
    assert context.trailing_metadata == (("x-biz-code", "40000"), ("x-error-type", "SystemError"))
    assert logs == [
        {
            "event": "grpc_mapped_error",
            "log_level": "error",
            "method": METHOD,
            "code": "40000",
            "status": "StatusCode.INTERNAL",
            "message": "db exploded",
            "request_id": None,
        }
    ]
    assert is_mapped_error() is True


@pytest.mark.parametrize(
    "exc, status, details",
    [
        (
            BusinessException(code=BusinessCode.FORBIDDEN, message="no"),
            Status.PERMISSION_DENIED,
            "no",
        ),
        (RuntimeError("x"), Status.INTERNAL, "系统内部错误"),
    ],
)
async def test_trailing_metadata_failure_is_ignored(
    exc: Exception, status: Any, details: str, logs: list[dict[str, Any]]
) -> None:
    context = FakeContext(trailing_error=RuntimeError("rpc already finished"))

    with pytest.raises(FakeAbort):
        await call(ExceptionMappingInterceptor(), raising(exc), context)

    assert context.trailing_metadata is None
    assert context.aborted == (status, details)
    assert [entry["event"] for entry in logs] == ["grpc_mapped_error"]
    assert is_mapped_error() is True


async def test_servicer_abort_is_remapped_as_system_error(logs: list[dict[str, Any]]) -> None:
    # 现状（疑似缺陷）：servicer 自己 abort 抛出的 AbortError 也被当成未知异常再映射一次
    context = FakeContext()

    with pytest.raises(FakeAbort):
        await call(
            ExceptionMappingInterceptor(), raising(grpc.aio.AbortError("Locally aborted.")), context
        )

    assert context.aborted == (Status.INTERNAL, "系统内部错误")
    assert logs[0]["code"] == "40000"
    assert logs[0]["message"] == "Locally aborted."


async def test_base_exception_is_not_mapped(logs: list[dict[str, Any]]) -> None:
    context = FakeContext()

    with pytest.raises(asyncio.CancelledError):
        await call(ExceptionMappingInterceptor(), raising(asyncio.CancelledError()), context)

    assert context.trailing_metadata is None
    assert context.aborted is None
    assert logs == []
    assert is_mapped_error() is False


# ----------------------------------------------------------------------
# LoggingInterceptor
# ----------------------------------------------------------------------


class FakePerfCounter:
    def __init__(self, *ticks: float) -> None:
        self._ticks = list(ticks)

    def perf_counter(self) -> float:
        return self._ticks.pop(0)


def request_log(peer: Any = "ipv4:127.0.0.1:5000", request_id: Any = "rid-1") -> dict[str, Any]:
    return {
        "event": "grpc_request",
        "log_level": "info",
        "method": METHOD,
        "peer": peer,
        "request_id": request_id,
    }


def done_log(elapsed_ms: float = 12.35, request_id: Any = "rid-1") -> dict[str, Any]:
    return {
        "event": "grpc_request_done",
        "log_level": "info",
        "method": METHOD,
        "elapsed_ms": elapsed_ms,
        "request_id": request_id,
    }


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(grpc_logging, "time", FakePerfCounter(1.0, 1.0123456))
    _request_id_var.set("rid-1")


async def test_success_logs_request_and_elapsed_time(
    clock: None, logs: list[dict[str, Any]]
) -> None:
    assert await call(LoggingInterceptor(), echo, FakeContext()) == b"resp:req"

    assert logs == [request_log(), done_log()]


async def test_context_without_peer_logs_none(clock: None, logs: list[dict[str, Any]]) -> None:
    assert await call(LoggingInterceptor(), echo, SimpleNamespace()) == b"resp:req"

    assert logs == [request_log(peer=None), done_log()]


class CodedError(Exception):
    def __init__(self, code: Any) -> None:
        super().__init__("coded")
        self.code = code


def _raise_inside_code() -> Any:
    raise RuntimeError("code() broke")


@pytest.mark.parametrize(
    "exc",
    [
        grpc.RpcError(),
        CodedError(lambda: Status.NOT_FOUND),
    ],
    ids=["rpc-error", "callable-code"],
)
async def test_already_mapped_errors_are_reraised_without_error_log(
    exc: Exception, clock: None, logs: list[dict[str, Any]]
) -> None:
    with pytest.raises(type(exc)) as caught:
        await call(LoggingInterceptor(), raising(exc), FakeContext())

    assert caught.value is exc
    assert logs == [request_log(), done_log()]


async def test_mapped_flag_suppresses_error_log(clock: None, logs: list[dict[str, Any]]) -> None:
    exc = RuntimeError("mapped elsewhere")
    set_mapped_error()

    with pytest.raises(RuntimeError) as caught:
        await call(LoggingInterceptor(), raising(exc), FakeContext())

    assert caught.value is exc
    assert logs == [request_log(), done_log()]


@pytest.mark.parametrize(
    "exc",
    [
        RuntimeError("boom"),
        CodedError(lambda: None),
        CodedError(5),
        CodedError(_raise_inside_code),
    ],
    ids=["plain", "code-returns-none", "code-not-callable", "code-raises"],
)
async def test_unhandled_errors_are_logged_and_reraised(
    exc: Exception, clock: None, logs: list[dict[str, Any]]
) -> None:
    with pytest.raises(type(exc)) as caught:
        await call(LoggingInterceptor(), raising(exc), FakeContext())

    assert caught.value is exc
    assert logs == [
        request_log(),
        {
            "event": "grpc_unhandled_error",
            "log_level": "error",
            "method": METHOD,
            "error": str(exc),
            "exc_info": True,
            "request_id": "rid-1",
        },
        done_log(),
    ]


async def test_peer_failure_is_logged_as_unhandled(clock: None, logs: list[dict[str, Any]]) -> None:
    class BrokenPeerContext:
        def peer(self) -> str:
            raise RuntimeError("no peer")

    with pytest.raises(RuntimeError, match="no peer"):
        await call(LoggingInterceptor(), echo, BrokenPeerContext())

    assert [entry["event"] for entry in logs] == ["grpc_unhandled_error", "grpc_request_done"]
    assert logs[0]["error"] == "no peer"


async def test_base_exception_skips_error_log_but_logs_done(
    clock: None, logs: list[dict[str, Any]]
) -> None:
    with pytest.raises(asyncio.CancelledError):
        await call(LoggingInterceptor(), raising(asyncio.CancelledError()), FakeContext())

    assert logs == [request_log(), done_log()]


# ----------------------------------------------------------------------
# 真实进程内 grpc.aio server：与 server.py 相同的拦截器顺序
# ----------------------------------------------------------------------


async def _servicer(request: bytes, context: Any) -> bytes:
    if request == b"ok":
        return b"pong"
    if request == b"biz":
        raise UserNotFoundException("u1")
    if request == b"abort":
        await context.abort(Status.FAILED_PRECONDITION, "servicer abort")
    raise RuntimeError("boom")


async def test_real_server_interceptor_chain(logs: list[dict[str, Any]]) -> None:
    server = grpc.aio.server(
        interceptors=(RequestIdInterceptor(), LoggingInterceptor(), ExceptionMappingInterceptor())
    )
    server.add_generic_rpc_handlers(
        (
            grpc.method_handlers_generic_handler(
                "test.Svc", {"Call": grpc.unary_unary_rpc_method_handler(_servicer)}
            ),
        )
    )
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    results: dict[bytes, tuple[Any, Any, tuple[Any, ...], list[dict[str, Any]]]] = {}
    try:
        async with grpc.aio.insecure_channel(f"127.0.0.1:{port}") as channel:
            rpc = channel.unary_unary(METHOD)
            for request in (b"ok", b"biz", b"boom", b"abort"):
                logs.clear()
                try:
                    pending = rpc(request, metadata=(("x-request-id", "rid-e2e"),))
                    response = await pending
                    results[request] = (
                        Status.OK,
                        response,
                        tuple(await pending.trailing_metadata()),
                        list(logs),
                    )
                except grpc.aio.AioRpcError as err:
                    results[request] = (
                        err.code(),
                        err.details(),
                        tuple(err.trailing_metadata()),
                        list(logs),
                    )
    finally:
        await server.stop(None)

    def events(entries: list[dict[str, Any]]) -> list[tuple[str, Any, Any]]:
        return [(e["event"], e.get("code"), e.get("message")) for e in entries]

    status, body, trailers, entries = results[b"ok"]
    assert (status, body, trailers) == (Status.OK, b"pong", (("x-request-id", "rid-e2e"),))
    assert events(entries) == [("grpc_request", None, None), ("grpc_request_done", None, None)]
    assert {e["request_id"] for e in entries} == {"rid-e2e"}

    # 现状：错误响应的 trailing metadata 覆盖了 x-request-id
    status, details, trailers, entries = results[b"biz"]
    assert (status, details) == (Status.NOT_FOUND, "User not found")
    assert trailers == (("x-biz-code", "20001"), ("x-error-type", "UserNotFound"))
    assert events(entries) == [
        ("grpc_request", None, None),
        ("grpc_mapped_error", "20001", "User not found"),
        ("grpc_request_done", None, None),
    ]

    status, details, trailers, entries = results[b"boom"]
    assert (status, details) == (Status.INTERNAL, "系统内部错误")
    assert trailers == (("x-biz-code", "40000"), ("x-error-type", "SystemError"))
    assert events(entries) == [
        ("grpc_request", None, None),
        ("grpc_mapped_error", "40000", "boom"),
        ("grpc_request_done", None, None),
    ]

    # 现状：servicer 自己 abort 时客户端拿到原状态，但服务端多记一条误导性的 SystemError 日志
    status, details, trailers, entries = results[b"abort"]
    assert (status, details) == (Status.FAILED_PRECONDITION, "servicer abort")
    assert trailers == (("x-request-id", "rid-e2e"),)
    assert events(entries) == [
        ("grpc_request", None, None),
        ("grpc_mapped_error", "40000", "Locally aborted."),
        ("grpc_request_done", None, None),
    ]
