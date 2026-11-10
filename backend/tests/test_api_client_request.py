# input: BaseAPIClient + httpx.MockTransport（经真实 httpx-retries RetryTransport 包装）
# output: BaseAPIClient._request 全分支特征测试（请求构造、响应解析、状态码→异常映射、超时/网络/未知异常包装、重试、debug 日志）
# pos: 后端测试 - REST API 客户端基类重构护栏；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Characterization tests for BaseAPIClient._request.

重构（降 McCabe 复杂度 + 修 lint）前后必须同绿。客户端仍由 BaseAPIClient.client
懒创建，只把 RetryTransport 的底层传输换成 MockTransport，因此重试、超时、
headers 合并都走真实的 httpx / httpx-retries 代码路径。
"""

from __future__ import annotations

import json
from typing import Any, Callable, Iterator, Optional

import httpx
import pytest
from httpx_retries import RetryTransport
from pydantic import BaseModel, field_serializer
from structlog.testing import capture_logs

from infrastructure.external.api_clients import base as api_base
from infrastructure.external.api_clients.base import (
    APIError,
    AuthenticationError,
    BaseAPIClient,
    HTTPMethod,
    NotFoundError,
    RateLimitError,
    ServerError,
)

_BASE = "https://api.example.com/"
Handler = Callable[[httpx.Request], httpx.Response]


class _MockHTTP:
    """记录发出的请求，并把 BaseAPIClient 用的 RetryTransport 底层换成 MockTransport。"""

    def __init__(self, handler: Handler) -> None:
        self._handler = handler
        self.requests: list[httpx.Request] = []
        self.retries: list[Any] = []

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self._handler(request)

    def transport_factory(self, *, retry: Any) -> RetryTransport:
        self.retries.append(retry)
        return RetryTransport(transport=httpx.MockTransport(self._handle), retry=retry)


@pytest.fixture
def mock_http(monkeypatch: pytest.MonkeyPatch) -> Callable[[Handler], _MockHTTP]:
    def install(handler: Handler) -> _MockHTTP:
        http = _MockHTTP(handler)
        monkeypatch.setattr(api_base, "RetryTransport", http.transport_factory)
        return http

    return install


def _respond(
    status: int = 200,
    *,
    payload: Any = None,
    content: Optional[bytes] = None,
    headers: Optional[dict[str, str]] = None,
) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        if content is not None:
            return httpx.Response(status, content=content, headers=headers)
        return httpx.Response(status, json=payload, headers=headers)

    return handler


def _raise(err: Exception) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        raise err

    return handler


def _sequence(statuses: list[int]) -> Handler:
    remaining: Iterator[int] = iter(statuses)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(next(remaining), json={"ok": True})

    return handler


class _Payload(BaseModel):
    name: str
    note: Optional[str] = None


class _Item(BaseModel):
    id: int


class _UnserializablePayload(BaseModel):
    name: str = "n"

    @field_serializer("name")
    def _explode(self, value: str) -> str:
        raise ValueError("cannot serialize")


# ── 请求构造 ──────────────────────────────────────────────────────────


async def test_get_returns_parsed_json_response(mock_http: Callable[[Handler], _MockHTTP]) -> None:
    http = mock_http(_respond(payload={"ok": True}, headers={"x-request-id": "req-1"}))

    async with BaseAPIClient(_BASE, retry_delay=0) as api:
        resp = await api.get("/items", params={"q": "x"})

    assert (resp.status_code, resp.is_success, resp.data) == (200, True, {"ok": True})
    assert json.loads(resp.raw_content) == {"ok": True}
    assert resp.request_id == "req-1"
    assert resp.headers["x-request-id"] == "req-1"
    assert isinstance(resp.elapsed_ms, float)
    assert resp.elapsed_ms >= 0
    (request,) = http.requests
    assert request.method == "GET"
    assert str(request.url) == "https://api.example.com/items?q=x"
    assert request.headers["content-type"] == "application/json"
    assert request.headers["accept"] == "application/json"
    assert request.headers["user-agent"] == "FastAPI-Forge/1.0"
    assert "authorization" not in request.headers
    assert request.content == b""


async def test_client_is_built_lazily_with_timeout_and_retry_config(
    mock_http: Callable[[Handler], _MockHTTP],
) -> None:
    http = mock_http(_respond(payload={}))

    async with BaseAPIClient(_BASE, timeout=12.5, max_retries=4, retry_delay=0) as api:
        assert http.retries == []
        await api.get("ping")
        await api.get("ping")

    (retry,) = http.retries
    assert (retry.total, retry.backoff_factor) == (4, 0)
    assert http.requests[0].extensions["timeout"] == {
        "connect": 12.5,
        "read": 12.5,
        "write": 12.5,
        "pool": 12.5,
    }


async def test_request_merges_default_auth_and_per_call_headers(
    mock_http: Callable[[Handler], _MockHTTP],
) -> None:
    http = mock_http(_respond(payload={}))

    async with BaseAPIClient(
        _BASE, headers={"X-Default": "d"}, auth_token="tok", retry_delay=0
    ) as api:
        await api.get("x", headers={"X-Default": "override", "X-Extra": "e"})
        assert api.default_headers["X-Default"] == "d"
        assert "X-Extra" not in api.default_headers

    headers = http.requests[0].headers
    assert headers["authorization"] == "Bearer tok"
    assert headers["x-default"] == "override"
    assert headers["x-extra"] == "e"


@pytest.mark.parametrize(
    ("method", "endpoint", "expected_method", "expected_url"),
    [
        (HTTPMethod.DELETE, "/a/b", "DELETE", "https://api.example.com/a/b"),
        ("PATCH", "c", "PATCH", "https://api.example.com/c"),
        (HTTPMethod.PUT, "", "PUT", "https://api.example.com/"),
    ],
)
async def test_request_accepts_enum_or_string_method_and_joins_url(
    mock_http: Callable[[Handler], _MockHTTP],
    method: Any,
    endpoint: str,
    expected_method: str,
    expected_url: str,
) -> None:
    http = mock_http(_respond(payload={}))

    async with BaseAPIClient(_BASE, retry_delay=0) as api:
        await api._request(method, endpoint)

    assert http.requests[0].method == expected_method
    assert str(http.requests[0].url) == expected_url


@pytest.mark.parametrize(
    ("json_data", "expected_body"),
    [
        ({"a": 1}, {"a": 1}),
        (_Payload(name="n"), {"name": "n"}),
        (_Payload(name="n", note=None), {"name": "n", "note": None}),
        ({}, {}),
    ],
    ids=["dict", "model-excludes-unset", "model-keeps-explicit-none", "empty-dict-still-sent"],
)
async def test_post_serializes_json_body(
    mock_http: Callable[[Handler], _MockHTTP], json_data: Any, expected_body: Any
) -> None:
    http = mock_http(_respond(payload={}))

    async with BaseAPIClient(_BASE, retry_delay=0) as api:
        await api.post("items", json_data=json_data)

    assert json.loads(http.requests[0].content) == expected_body


async def test_form_and_file_bodies_keep_default_json_content_type(
    mock_http: Callable[[Handler], _MockHTTP],
) -> None:
    """现状钉子：默认 Content-Type: application/json 会覆盖表单/multipart 的类型（含 boundary）。"""
    http = mock_http(_respond(payload={}))

    async with BaseAPIClient(_BASE, retry_delay=0) as api:
        await api.post("form", data={"a": "1"})
        await api.post("upload", files={"f": ("a.txt", b"hi", "text/plain")})

    form, upload = http.requests
    assert form.content == b"a=1"
    assert form.headers["content-type"] == "application/json"
    assert b'name="f"' in upload.content
    assert upload.headers["content-type"] == "application/json"


async def test_extra_kwargs_are_forwarded_to_httpx(
    mock_http: Callable[[Handler], _MockHTTP],
) -> None:
    http = mock_http(_respond(payload={}))

    async with BaseAPIClient(_BASE, retry_delay=0) as api:
        await api.get("x", timeout=5.0)

    assert http.requests[0].extensions["timeout"] == {
        "connect": 5.0,
        "read": 5.0,
        "write": 5.0,
        "pool": 5.0,
    }


async def test_pre_send_failures_are_not_wrapped(mock_http: Callable[[Handler], _MockHTTP]) -> None:
    http = mock_http(_respond(payload={}))

    async with BaseAPIClient(_BASE, retry_delay=0) as api:
        with pytest.raises(ValueError, match="cannot serialize") as info:
            await api.post("items", json_data=_UnserializablePayload(name="n"))

    assert not isinstance(info.value, APIError)
    assert http.requests == []


# ── 响应解析 ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("content_type", "body", "expected"),
    [
        ("text/plain", b"hello", None),
        ("application/json", b"{not json", None),
        ("application/json; charset=utf-8", b'{"a": 1}', {"a": 1}),
        ("application/problem+json", b'{"a": 1}', None),
        (None, b'{"a": 1}', None),
    ],
    ids=["text", "invalid-json", "json-with-charset", "problem-json", "no-content-type"],
)
async def test_response_data_only_parsed_for_json_content_type(
    mock_http: Callable[[Handler], _MockHTTP],
    content_type: Optional[str],
    body: bytes,
    expected: Any,
) -> None:
    headers = {"content-type": content_type} if content_type else {}
    mock_http(_respond(content=body, headers=headers))

    async with BaseAPIClient(_BASE, retry_delay=0) as api:
        resp = await api.get("x")

    assert resp.data == expected
    assert resp.raw_content == body
    assert resp.request_id is None


async def test_typed_helpers_build_response_models(
    mock_http: Callable[[Handler], _MockHTTP],
) -> None:
    mock_http(_respond(payload={"id": 7}))

    async with BaseAPIClient(_BASE, retry_delay=0) as api:
        assert await api.get_typed("items/7", _Item) == _Item(id=7)
        assert await api.post_typed("items", _Item, json_data={"x": 1}) == _Item(id=7)


# ── 错误状态码 ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("status", "exc_type"),
    [
        (400, APIError),
        (401, AuthenticationError),
        (403, AuthenticationError),
        (404, NotFoundError),
        (409, APIError),
        (418, APIError),
        (429, RateLimitError),
        (500, ServerError),
        (502, ServerError),
        (503, ServerError),
        (504, ServerError),
    ],
)
async def test_error_status_raises_typed_error_unwrapped(
    mock_http: Callable[[Handler], _MockHTTP], status: int, exc_type: type[APIError]
) -> None:
    mock_http(_respond(status, payload={"message": "nope"}, headers={"x-request-id": "rid"}))

    async with BaseAPIClient(_BASE, retry_delay=0) as api:
        with pytest.raises(APIError) as info:
            await api.post("items")

    err = info.value
    assert type(err) is exc_type
    assert (err.message, err.status_code, err.request_id) == ("nope", status, "rid")
    assert err.response is not None
    assert err.response.data == {"message": "nope"}
    assert str(err) == f"nope | Status: {status} | Request ID: rid"
    assert err.__cause__ is None


_DEFAULT_404 = "API request failed with status 404"


@pytest.mark.parametrize(
    ("handler", "expected"),
    [
        (_respond(404, payload={"message": "m", "error": "e"}), "m"),
        (_respond(404, payload={"error": "e"}), "e"),
        (_respond(404, payload={"detail": "d"}), "d"),
        (_respond(404, payload={"message": "", "error": "e"}), "e"),
        (_respond(404, payload={"other": 1}), _DEFAULT_404),
        (_respond(404, payload=[1, 2]), _DEFAULT_404),
        (_respond(404, content=b"oops", headers={"content-type": "text/plain"}), _DEFAULT_404),
    ],
    ids=[
        "message-first",
        "error",
        "detail",
        "empty-message-falls-through",
        "no-known-key",
        "list",
        "text",
    ],
)
async def test_error_message_extraction(
    mock_http: Callable[[Handler], _MockHTTP], handler: Handler, expected: str
) -> None:
    mock_http(handler)

    async with BaseAPIClient(_BASE, retry_delay=0) as api:
        with pytest.raises(NotFoundError) as info:
            await api.get("x")

    assert info.value.message == expected
    assert str(info.value) == f"{expected} | Status: 404"


# ── 传输层异常 ────────────────────────────────────────────────────────


@pytest.mark.parametrize(("timeout", "expected"), [(30.0, "30.0"), (2, "2")])
async def test_timeout_is_wrapped_in_api_error(
    mock_http: Callable[[Handler], _MockHTTP], timeout: float, expected: str
) -> None:
    err = httpx.ReadTimeout("slow")
    mock_http(_raise(err))

    async with BaseAPIClient(_BASE, timeout=timeout, retry_delay=0) as api:
        with pytest.raises(APIError) as info:
            await api.post("x")

    assert type(info.value) is APIError
    assert str(info.value) == f"Request timeout after {expected}s"
    assert info.value.status_code is None
    assert info.value.__cause__ is err


async def test_network_error_is_wrapped_in_api_error(
    mock_http: Callable[[Handler], _MockHTTP],
) -> None:
    err = httpx.ConnectError("refused")
    mock_http(_raise(err))

    async with BaseAPIClient(_BASE, retry_delay=0) as api:
        with capture_logs() as logs, pytest.raises(APIError) as info:
            await api.post("x")

    assert type(info.value) is APIError
    assert str(info.value) == "Network error: refused"
    assert info.value.__cause__ is err
    assert logs == []


async def test_unexpected_error_is_logged_and_wrapped(
    mock_http: Callable[[Handler], _MockHTTP],
) -> None:
    err = RuntimeError("kaboom")
    mock_http(_raise(err))

    async with BaseAPIClient(_BASE, retry_delay=0) as api:
        with capture_logs() as logs, pytest.raises(APIError) as info:
            await api.post("x")

    assert type(info.value) is APIError
    assert str(info.value) == "Unexpected error: kaboom"
    assert info.value.__cause__ is err
    assert logs == [{"event": "Unexpected error during API request: kaboom", "log_level": "error"}]


async def test_client_construction_failure_is_wrapped(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken_transport(*, retry: Any) -> RetryTransport:
        raise RuntimeError("no transport")

    monkeypatch.setattr(api_base, "RetryTransport", broken_transport)

    async with BaseAPIClient(_BASE, retry_delay=0) as api:
        with pytest.raises(APIError, match="^Unexpected error: no transport$"):
            await api.get("x")


async def test_kwarg_colliding_with_named_argument_is_wrapped(
    mock_http: Callable[[Handler], _MockHTTP],
) -> None:
    """现状钉子：额外 kwargs 原样展开给 httpx，与具名参数撞名时由 httpx 抛 TypeError 并被兜底包装。"""
    http = mock_http(_respond(payload={}))

    async with BaseAPIClient(_BASE, retry_delay=0) as api:
        with pytest.raises(APIError) as info:
            await api.get("x", json={"a": 1})

    assert str(info.value) == (
        "Unexpected error: httpx._client.AsyncClient.request() "
        "got multiple values for keyword argument 'json'"
    )
    assert isinstance(info.value.__cause__, TypeError)
    assert http.requests == []


# ── 重试（由 httpx-retries 传输层负责，_request 只看到最终结果）─────────


async def test_get_retries_transient_status_then_succeeds(
    mock_http: Callable[[Handler], _MockHTTP],
) -> None:
    http = mock_http(_sequence([503, 502, 200]))

    async with BaseAPIClient(_BASE, max_retries=3, retry_delay=0) as api:
        resp = await api.get("x")

    assert resp.status_code == 200
    assert len(http.requests) == 3


async def test_get_gives_up_after_max_retries(mock_http: Callable[[Handler], _MockHTTP]) -> None:
    http = mock_http(_respond(503, payload={}))

    async with BaseAPIClient(_BASE, max_retries=2, retry_delay=0) as api:
        with pytest.raises(ServerError):
            await api.get("x")

    assert len(http.requests) == 3


async def test_post_is_not_retried(mock_http: Callable[[Handler], _MockHTTP]) -> None:
    http = mock_http(_respond(503, payload={}))

    async with BaseAPIClient(_BASE, max_retries=3, retry_delay=0) as api:
        with pytest.raises(ServerError):
            await api.post("x")

    assert len(http.requests) == 1


async def test_get_retries_timeouts_then_wraps(mock_http: Callable[[Handler], _MockHTTP]) -> None:
    http = mock_http(_raise(httpx.ReadTimeout("slow")))

    async with BaseAPIClient(_BASE, max_retries=2, retry_delay=0) as api:
        with pytest.raises(APIError, match=r"^Request timeout after 30\.0s$"):
            await api.get("x")

    assert len(http.requests) == 3


# ── debug 日志 ────────────────────────────────────────────────────────


async def test_debug_mode_logs_redacted_request_and_response(
    mock_http: Callable[[Handler], _MockHTTP],
) -> None:
    mock_http(_respond(201, payload={"id": 1}, headers={"x-request-id": "rid"}))

    async with BaseAPIClient(_BASE, auth_token="secret", debug=True, retry_delay=0) as api:
        with capture_logs() as logs:
            resp = await api.post("items", params={"p": "1"}, json_data=_Payload(name="n"))

    assert logs == [
        {
            "event": "api_request",
            "log_level": "debug",
            "method": "POST",
            "url": "https://api.example.com/items",
            "params": {"p": "1"},
            "json": {"name": "n"},
            "headers": {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "FastAPI-Forge/1.0",
            },
        },
        {
            "event": "api_response",
            "log_level": "debug",
            "status_code": 201,
            "elapsed_ms": resp.elapsed_ms,
            "request_id": "rid",
            "data": {"id": 1},
        },
    ]


async def test_debug_mode_hides_error_response_body(
    mock_http: Callable[[Handler], _MockHTTP],
) -> None:
    mock_http(_respond(404, payload={"message": "gone"}))

    async with BaseAPIClient(_BASE, debug=True, retry_delay=0) as api:
        with capture_logs() as logs, pytest.raises(NotFoundError):
            await api.get("x")

    assert [entry["event"] for entry in logs] == ["api_request", "api_response"]
    assert logs[1]["status_code"] == 404
    assert logs[1]["data"] is None


async def test_non_debug_mode_logs_nothing_on_success(
    mock_http: Callable[[Handler], _MockHTTP],
) -> None:
    mock_http(_respond(payload={}))

    async with BaseAPIClient(_BASE, retry_delay=0) as api:
        with capture_logs() as logs:
            await api.get("x")

    assert logs == []
