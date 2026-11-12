"""Characterization tests for LoggingMiddleware (pure ASGI).

只断言可观察行为：下游收到的 receive/send、返回给客户端的消息与响应头、
抛出的异常、以及结构化日志事件（structlog capture_logs）。
"""

from __future__ import annotations

import asyncio
import json
import re
from types import SimpleNamespace
from typing import Any, Iterator

import httpx
import pytest
import structlog
from fastapi import FastAPI, Request
from structlog.testing import capture_logs

from api.middleware import logging as logging_mw
from api.middleware.logging import LoggingMiddleware

Message = dict[str, Any]

SKIP_PATHS = [
    "/health",
    "/health/live",
    "/health/ready",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
]
SENSITIVE_FIELDS = [
    "password",
    "secret",
    "api_key",
    "old_password",
    "new_password",
    "token",
    "access_token",
    "refresh_token",
    "id_token",
    "code",
    "credential",
    "client_secret",
    "authorization",
]
JSON_HEADERS = [("content-type", "application/json")]
PROCESS_TIME = re.compile(rb"\d+\.\d{3}")


@pytest.fixture
def logs(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[dict[str, Any]]]:
    """捕获中间件日志；换成新的 lazy logger，避免 cache_logger_on_first_use 绕过捕获。"""
    with capture_logs() as captured:
        monkeypatch.setattr(logging_mw, "logger", structlog.get_logger(logging_mw.__name__))
        yield captured


@pytest.fixture(autouse=True)
def configure(monkeypatch: pytest.MonkeyPatch) -> Any:
    """每个测试都显式固定中间件读取的 settings，不依赖 .env 或进程环境变量。

    默认：DEBUG 开、默认记录请求体、上限 2048 字节、不记录 multipart。
    需要其他取值的测试调用 configure(...) 覆盖；须在构造中间件前调用。
    """

    def _configure(
        *,
        debug: bool = True,
        body_default: bool = True,
        max_bytes: int = 2048,
        allow_multipart: bool = False,
    ) -> None:
        monkeypatch.setattr(
            logging_mw,
            "settings",
            SimpleNamespace(
                DEBUG=debug,
                LOG_REQUEST_BODY_ENABLE_BY_DEFAULT=body_default,
                LOG_REQUEST_BODY_MAX_BYTES=max_bytes,
                LOG_REQUEST_BODY_ALLOW_MULTIPART=allow_multipart,
            ),
        )

    _configure()
    return _configure


class FakeClock:
    """按顺序吐出预设时间戳；多调用或少调用都会让断言失败。"""

    def __init__(self, *ticks: float) -> None:
        self._ticks = list(ticks)

    def time(self) -> float:
        return self._ticks.pop(0)


class Client:
    """ASGI 服务器一侧：按序提供请求消息，记录发回的消息。"""

    def __init__(self, *incoming: Message) -> None:
        self._queue = list(incoming)
        self.sent: list[Message] = []
        self.receive = self._receive
        self.send = self._send

    async def _receive(self) -> Message:
        return self._queue.pop(0) if self._queue else {"type": "http.disconnect"}

    async def _send(self, message: Message) -> None:
        self.sent.append(message)


class Downstream:
    """可编排的下游 ASGI app：读完请求体 → 发响应；记录收到的 scope/receive/send 和消息。"""

    def __init__(
        self,
        status: int = 200,
        *,
        read_body: bool = True,
        send_response: bool = True,
        raise_before_start: BaseException | None = None,
        raise_after_start: BaseException | None = None,
    ) -> None:
        self.status = status
        self.read_body = read_body
        self.send_response = send_response
        self.raise_before_start = raise_before_start
        self.raise_after_start = raise_after_start
        self.received: list[Message] = []
        self.start_message: Message | None = None
        self.body_message: Message | None = None
        self.scope: Any = None
        self.receive: Any = None
        self.send: Any = None

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        self.scope, self.receive, self.send = scope, receive, send
        if self.read_body:
            while True:
                message = await receive()
                self.received.append(message)
                if message["type"] != "http.request" or not message.get("more_body", False):
                    break
        if self.raise_before_start is not None:
            raise self.raise_before_start
        if not self.send_response:
            return
        self.start_message = {
            "type": "http.response.start",
            "status": self.status,
            "headers": [(b"content-type", b"text/plain")],
        }
        await send(self.start_message)
        if self.raise_after_start is not None:
            raise self.raise_after_start
        self.body_message = {"type": "http.response.body", "body": b"ok"}
        await send(self.body_message)


def http_scope(
    method: str = "GET",
    path: str = "/items",
    query: bytes = b"",
    headers: list[tuple[str, str]] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    scope: dict[str, Any] = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": query,
        "headers": [(k.encode("latin-1"), v.encode("latin-1")) for k, v in headers or []],
    }
    scope.update(extra)
    return scope


def body_messages(*chunks: bytes) -> list[Message]:
    if not chunks:
        return [{"type": "http.request", "body": b"", "more_body": False}]
    last = len(chunks) - 1
    return [
        {"type": "http.request", "body": chunk, "more_body": i < last}
        for i, chunk in enumerate(chunks)
    ]


async def run(
    downstream: Any, scope: dict[str, Any], incoming: list[Message] | None = None
) -> Client:
    client = Client(*(incoming if incoming is not None else body_messages()))
    await LoggingMiddleware(downstream)(scope, client.receive, client.send)
    return client


# ----------------------------------------------------------------------
# 不记录日志的透传路径
# ----------------------------------------------------------------------


@pytest.mark.parametrize("scope_type", ["lifespan", "websocket"])
async def test_non_http_scope_is_passed_through_untouched(
    scope_type: str, logs: list[dict[str, Any]]
) -> None:
    downstream = Downstream(read_body=False, send_response=False)
    client = Client()
    scope = {"type": scope_type, "path": "/items"}

    await LoggingMiddleware(downstream)(scope, client.receive, client.send)

    assert downstream.scope is scope
    assert downstream.receive is client.receive
    assert downstream.send is client.send
    assert logs == []


@pytest.mark.parametrize("path", SKIP_PATHS)
async def test_skip_paths_are_passed_through_without_logs_or_header(
    path: str, logs: list[dict[str, Any]]
) -> None:
    downstream = Downstream()
    client = Client(*body_messages())

    await LoggingMiddleware(downstream)(http_scope(path=path), client.receive, client.send)

    assert downstream.receive is client.receive
    assert downstream.send is client.send
    assert client.sent[0] is downstream.start_message
    assert logs == []


async def test_skip_paths_match_exactly(logs: list[dict[str, Any]]) -> None:
    await run(Downstream(), http_scope(path="/health/"))

    assert [entry["event"] for entry in logs] == ["request_started", "request_completed"]


# ----------------------------------------------------------------------
# 请求信息、响应日志与 X-Process-Time
# ----------------------------------------------------------------------


async def test_request_and_response_are_logged_with_process_time_header(
    logs: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(logging_mw, "time", FakeClock(100.0, 100.25, 100.5))
    downstream = Downstream()
    scope = http_scope(
        query=b"a=1&b=2&b=3",
        headers=[("user-agent", "pytest-ua"), ("referer", "https://ref.example/x")],
    )

    client = await run(downstream, scope)

    started = {
        "event": "request_started",
        "log_level": "info",
        "method": "GET",
        "path": "/items",
        "query_params": {"a": "1", "b": ["2", "3"]},
        "user_agent": "pytest-ua",
        "referer": "https://ref.example/x",
    }
    completed = {**started, "event": "request_completed", "status_code": 200, "duration": 0.5}
    assert logs == [started, completed]
    assert client.sent == [
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"text/plain"), (b"x-process-time", b"0.250")],
        },
        downstream.body_message,
    ]
    # 注入响应头时不改动下游自己的消息对象
    assert downstream.start_message == {
        "type": "http.response.start",
        "status": 200,
        "headers": [(b"content-type", b"text/plain")],
    }
    assert downstream.received == body_messages()


async def test_request_info_omits_absent_optional_fields(logs: list[dict[str, Any]]) -> None:
    await run(Downstream(), http_scope(method="DELETE", path="/items/1"))

    assert logs[0] == {
        "event": "request_started",
        "log_level": "info",
        "method": "DELETE",
        "path": "/items/1",
    }


async def test_bare_http_scope_falls_back_to_empty_method_and_path(
    logs: list[dict[str, Any]],
) -> None:
    await run(Downstream(), {"type": "http"})

    assert logs[0] == {"event": "request_started", "log_level": "info", "method": "", "path": ""}
    assert logs[1]["event"] == "request_completed"


async def test_query_string_is_decoded_once(logs: list[dict[str, Any]]) -> None:
    # 只解码一次：编码过的 & / = / + 保持为值的一部分；空值被丢弃；敏感参数脱敏
    scope = http_scope(query=b"q=a%26b%3Dc&name=x%2By&empty=&token=t1")

    await run(Downstream(), scope)

    assert logs[0]["query_params"] == {"q": "a&b=c", "name": "x+y", "token": "***"}


async def test_path_params_present_in_scope_are_logged(logs: list[dict[str, Any]]) -> None:
    await run(Downstream(), http_scope(path_params={"item_id": "42"}))
    await run(Downstream(), http_scope(path_params={}))

    assert logs[0]["path_params"] == {"item_id": "42"}
    assert "path_params" not in logs[2]


@pytest.mark.parametrize(
    "status, event, level",
    [
        (200, "request_completed", "info"),
        (302, "request_completed", "info"),
        (399, "request_completed", "info"),
        (400, "request_client_error", "warning"),
        (404, "request_client_error", "warning"),
        (499, "request_client_error", "warning"),
        (500, "request_server_error", "error"),
        (503, "request_server_error", "error"),
    ],
)
async def test_response_log_level_follows_status_code(
    status: int, event: str, level: str, logs: list[dict[str, Any]]
) -> None:
    await run(Downstream(status=status), http_scope())

    assert logs[-1]["event"] == event
    assert logs[-1]["log_level"] == level
    assert logs[-1]["status_code"] == status


async def test_status_defaults_to_500_when_app_sends_no_response(
    logs: list[dict[str, Any]],
) -> None:
    client = await run(Downstream(send_response=False), http_scope())

    assert client.sent == []
    assert logs[-1]["event"] == "request_server_error"
    assert logs[-1]["status_code"] == 500


async def test_status_defaults_to_500_when_start_message_has_no_status(
    logs: list[dict[str, Any]],
) -> None:
    async def app(scope: Any, receive: Any, send: Any) -> None:
        await send({"type": "http.response.start"})
        await send({"type": "http.response.body", "body": b""})

    client = await run(app, http_scope())

    start = client.sent[0]
    assert start["type"] == "http.response.start"
    assert "status" not in start
    assert [name for name, _ in start["headers"]] == [b"x-process-time"]
    assert PROCESS_TIME.fullmatch(start["headers"][0][1])
    assert logs[-1]["event"] == "request_server_error"
    assert logs[-1]["status_code"] == 500


# ----------------------------------------------------------------------
# 异常路径
# ----------------------------------------------------------------------


async def test_exception_before_response_logs_request_failed_and_reraises(
    logs: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(logging_mw, "time", FakeClock(10.0, 11.5))
    error = ValueError("boom")

    with pytest.raises(ValueError) as caught:
        await run(Downstream(raise_before_start=error), http_scope())

    assert caught.value is error
    started = {"event": "request_started", "log_level": "info", "method": "GET", "path": "/items"}
    assert logs == [
        started,
        {
            **started,
            "event": "request_failed",
            "log_level": "error",
            "duration": 1.5,
            "error": "boom",
            "error_type": "ValueError",
            "exc_info": True,
        },
    ]


async def test_exception_after_response_start_logs_request_failed(
    logs: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(logging_mw, "time", FakeClock(10.0, 10.25, 10.5))
    downstream = Downstream(raise_after_start=RuntimeError("stream broke"))
    client = Client(*body_messages())

    with pytest.raises(RuntimeError):
        await LoggingMiddleware(downstream)(http_scope(), client.receive, client.send)

    assert client.sent == [
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"text/plain"), (b"x-process-time", b"0.250")],
        }
    ]
    assert [entry["event"] for entry in logs] == ["request_started", "request_failed"]
    assert logs[-1]["duration"] == 0.5
    assert logs[-1]["error"] == "stream broke"
    assert logs[-1]["error_type"] == "RuntimeError"
    assert "status_code" not in logs[-1]


async def test_base_exception_propagates_without_failure_log(logs: list[dict[str, Any]]) -> None:
    with pytest.raises(asyncio.CancelledError):
        await run(Downstream(raise_before_start=asyncio.CancelledError()), http_scope())

    assert [entry["event"] for entry in logs] == ["request_started"]


# ----------------------------------------------------------------------
# 请求体捕获：是否记录、解析、脱敏、截断
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "method, debug, body_default, header, logged",
    [
        ("POST", True, True, None, True),
        ("PUT", True, True, None, True),
        ("PATCH", True, True, None, True),
        ("GET", True, True, None, False),
        ("DELETE", True, True, None, False),
        ("GET", True, False, "true", False),
        ("POST", False, True, None, False),
        ("POST", True, False, None, False),
        ("POST", True, False, "true", True),
        ("POST", True, False, "1", True),
        ("POST", True, False, "YES", True),
        ("POST", False, True, "true", False),
        ("POST", True, True, "false", False),
        ("POST", True, True, "0", False),
        ("POST", True, True, "No", False),
        ("POST", True, True, "maybe", True),
        ("POST", False, True, "maybe", False),
    ],
)
async def test_body_logging_decision(
    method: str,
    debug: bool,
    body_default: bool,
    header: str | None,
    logged: bool,
    logs: list[dict[str, Any]],
    configure: Any,
) -> None:
    configure(debug=debug, body_default=body_default)
    headers = JSON_HEADERS + ([("x-log-body", header)] if header is not None else [])
    payload = b'{"name": "n"}'
    downstream = Downstream()

    await run(downstream, http_scope(method=method, headers=headers), body_messages(payload))

    assert ("body" in logs[-1]) is logged
    if logged:
        assert logs[-1]["body"] == {"name": "n"}
    assert "body" not in logs[0]
    # 无论是否记录，下游拿到的都是原样请求体
    assert downstream.received == body_messages(payload)


async def test_json_body_sensitive_fields_are_masked_recursively(
    logs: list[dict[str, Any]],
) -> None:
    payload = {
        "username": "u",
        "Password": "p",
        "profile": {"API_KEY": "k", "nick": "n", "credential": {"nested": "x"}},
        "items": [{"token": "t", "id": 1}, "plain", [{"secret": "s"}]],
        "n": None,
    }
    headers = [("content-type", "Application/JSON; charset=utf-8")]

    await run(
        Downstream(),
        http_scope(method="POST", headers=headers),
        body_messages(json.dumps(payload).encode()),
    )

    assert logs[-1]["body"] == {
        "username": "u",
        "Password": "***",
        "profile": {"API_KEY": "***", "nick": "n", "credential": "***"},
        "items": [{"token": "***", "id": 1}, "plain", [{"secret": "***"}]],
        "n": None,
    }


async def test_every_sensitive_field_is_masked(logs: list[dict[str, Any]]) -> None:
    payload = {field: f"v-{field}" for field in SENSITIVE_FIELDS}
    payload["safe"] = "kept"

    await run(
        Downstream(),
        http_scope(method="POST", headers=JSON_HEADERS),
        body_messages(json.dumps(payload).encode()),
    )

    assert logs[-1]["body"] == {**{field: "***" for field in SENSITIVE_FIELDS}, "safe": "kept"}


async def test_json_list_body_is_masked(logs: list[dict[str, Any]]) -> None:
    await run(
        Downstream(),
        http_scope(method="POST", headers=JSON_HEADERS),
        body_messages(b'[{"token": "t"}, 1]'),
    )

    assert logs[-1]["body"] == [{"token": "***"}, 1]


async def test_invalid_json_body_is_not_logged_verbatim(logs: list[dict[str, Any]]) -> None:
    # 解析失败（含被截断的 JSON）无法按字段脱敏，只记长度，原文里的密码不能进日志
    await run(
        Downstream(),
        http_scope(method="POST", headers=JSON_HEADERS),
        body_messages(b'{"password": "p"'),
    )

    assert logs[-1]["body"] == "<unparseable json, 16 bytes>"


async def test_form_body_is_parsed_and_masked(logs: list[dict[str, Any]]) -> None:
    headers = [("content-type", "application/x-www-form-urlencoded; charset=utf-8")]

    await run(
        Downstream(),
        http_scope(method="POST", headers=headers),
        body_messages(b"a=1&password=secret&b=2&b=3&empty="),
    )

    assert logs[-1]["body"] == {"a": "1", "password": "***", "b": ["2", "3"]}


@pytest.mark.parametrize("headers", [[], [("content-type", "text/plain")]])
async def test_other_bodies_are_logged_as_decoded_text(
    headers: list[tuple[str, str]], logs: list[dict[str, Any]]
) -> None:
    await run(
        Downstream(),
        http_scope(method="POST", headers=headers),
        body_messages(b"hello \xff world"),
    )

    assert logs[-1]["body"] == "hello  world"


@pytest.mark.parametrize("allow_multipart, expected", [(False, None), (True, {"multipart": True})])
async def test_multipart_body_logging(
    allow_multipart: bool,
    expected: dict[str, bool] | None,
    logs: list[dict[str, Any]],
    configure: Any,
) -> None:
    configure(allow_multipart=allow_multipart)
    headers = [("content-type", "multipart/form-data; boundary=xyz")]

    await run(
        Downstream(),
        http_scope(method="POST", headers=headers),
        body_messages(b"--xyz\r\npart\r\n--xyz--"),
    )

    assert logs[-1].get("body") == expected


async def test_body_capture_is_truncated_across_chunks(
    logs: list[dict[str, Any]], configure: Any
) -> None:
    configure(max_bytes=10)
    chunks = (b"0123456", b"789abcdef", b"ghij")
    downstream = Downstream()

    await run(
        downstream,
        http_scope(method="POST", headers=[("content-type", "text/plain")]),
        body_messages(*chunks),
    )

    assert logs[-1]["body"] == "0123456789"
    assert downstream.received == body_messages(*chunks)


async def test_empty_body_is_not_logged(logs: list[dict[str, Any]]) -> None:
    await run(Downstream(), http_scope(method="POST", headers=JSON_HEADERS), body_messages())

    assert logs[-1]["event"] == "request_completed"
    assert "body" not in logs[-1]


async def test_body_is_attached_to_request_failed(logs: list[dict[str, Any]]) -> None:
    downstream = Downstream(raise_before_start=RuntimeError("after read"))

    with pytest.raises(RuntimeError):
        await run(
            downstream,
            http_scope(method="POST", headers=JSON_HEADERS),
            body_messages(b'{"password": "p", "name": "n"}'),
        )

    assert logs[-1]["event"] == "request_failed"
    assert logs[-1]["body"] == {"password": "***", "name": "n"}


async def test_unloggable_body_is_omitted_from_request_failed(
    logs: list[dict[str, Any]],
) -> None:
    downstream = Downstream(raise_before_start=RuntimeError("after read"))
    headers = [("content-type", "multipart/form-data; boundary=xyz")]

    with pytest.raises(RuntimeError):
        await run(
            downstream,
            http_scope(method="POST", headers=headers),
            body_messages(b"--xyz\r\npart\r\n--xyz--"),
        )

    assert logs[-1]["event"] == "request_failed"
    assert "body" not in logs[-1]


async def test_non_request_messages_pass_through_receive(logs: list[dict[str, Any]]) -> None:
    received: list[Message] = []

    async def app(scope: Any, receive: Any, send: Any) -> None:
        received.append(await receive())
        received.append(await receive())
        await send({"type": "http.response.start", "status": 204, "headers": []})

    incoming: list[Message] = [
        {"type": "http.request", "body": b'{"name": "n"}', "more_body": False},
        {"type": "http.disconnect"},
    ]
    await run(app, http_scope(method="POST", headers=JSON_HEADERS), [dict(m) for m in incoming])

    assert received == incoming
    assert logs[-1]["body"] == {"name": "n"}


# ----------------------------------------------------------------------
# 真实 FastAPI 栈端到端
# ----------------------------------------------------------------------


async def test_fastapi_stack_end_to_end(logs: list[dict[str, Any]], configure: Any) -> None:
    app = FastAPI()

    @app.post("/items/{item_id}")
    async def create_item(item_id: str, request: Request) -> dict[str, Any]:
        return {"item_id": item_id, "echo": await request.json()}

    @app.get("/health")
    async def health() -> dict[str, bool]:
        return {"ok": True}

    app.add_middleware(LoggingMiddleware)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post(
            "/items/7?x=1", json={"password": "p", "name": "n"}, headers={"user-agent": "it"}
        )
        health_resp = await client.get("/health")

    assert created.status_code == 200
    # 下游拿到未脱敏的原始请求体
    assert created.json() == {"item_id": "7", "echo": {"password": "p", "name": "n"}}
    assert PROCESS_TIME.fullmatch(created.headers["x-process-time"].encode())
    assert health_resp.status_code == 200
    assert "x-process-time" not in health_resp.headers

    started, completed = logs  # /health 不产生日志
    # 现状：路由匹配发生在中间件提取请求信息之后，所以经 FastAPI 时日志里没有 path_params
    assert started == {
        "event": "request_started",
        "log_level": "info",
        "method": "POST",
        "path": "/items/7",
        "query_params": {"x": "1"},
        "user_agent": "it",
    }
    assert completed == {
        **started,
        "event": "request_completed",
        "status_code": 200,
        "duration": completed["duration"],
        "body": {"password": "***", "name": "n"},
    }
    assert isinstance(completed["duration"], float)


# ----------------------------------------------------------------------
# DEBUG 关闭（生产默认）：请求体一律不记录，X-Log-Body 强制开启无效
# ----------------------------------------------------------------------


@pytest.mark.parametrize("body_default", [True, False])
@pytest.mark.parametrize("header", [None, "true", "1", "YES"])
async def test_body_is_never_logged_outside_debug(
    header: str | None, body_default: bool, logs: list[dict[str, Any]], configure: Any
) -> None:
    configure(debug=False, body_default=body_default)
    headers = JSON_HEADERS + ([("x-log-body", header)] if header is not None else [])
    payload = b'{"password": "p", "name": "n"}'
    downstream = Downstream()

    await run(downstream, http_scope(method="POST", headers=headers), body_messages(payload))

    assert [entry["event"] for entry in logs] == ["request_started", "request_completed"]
    assert "body" not in logs[-1]
    assert downstream.received == body_messages(payload)


async def test_failed_request_body_is_not_logged_outside_debug(
    logs: list[dict[str, Any]], configure: Any
) -> None:
    configure(debug=False)
    headers = JSON_HEADERS + [("x-log-body", "true")]

    with pytest.raises(RuntimeError):
        await run(
            Downstream(raise_before_start=RuntimeError("after read")),
            http_scope(method="POST", headers=headers),
            body_messages(b'{"password": "p"}'),
        )

    assert logs[-1]["event"] == "request_failed"
    assert "body" not in logs[-1]


async def test_fastapi_stack_outside_debug_does_not_log_body(
    logs: list[dict[str, Any]], configure: Any
) -> None:
    configure(debug=False)
    app = FastAPI()

    @app.post("/items")
    async def create_item(request: Request) -> Any:
        return await request.json()

    app.add_middleware(LoggingMiddleware)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post(
            "/items", json={"password": "p"}, headers={"x-log-body": "true"}
        )

    assert created.json() == {"password": "p"}
    assert [entry["event"] for entry in logs] == ["request_started", "request_completed"]
    assert "body" not in logs[-1]
