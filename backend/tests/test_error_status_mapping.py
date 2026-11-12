"""业务码 → 传输层状态：单一登记表的完整性与关键映射。

借鉴 Kratos errors（错误在定义处声明一次状态码）：HTTP 处理器与 gRPC 拦截器曾各维护
一张表、各带静默默认值，新增业务码漏登记就悄悄落到 400 / FAILED_PRECONDITION
（AGENT_CONFIG_NOT_FOUND 曾因此渲染成 400，与"not-found 必须 404"的归属约定冲突）。

验收标准（Given-When-Then）：
- 每个错误码都在 TRANSPORT_STATUS 登记，gRPC 状态名是规范名；SUCCESS 不登记、误用时走兜底 400
- HTTP 处理器按登记表渲染状态码（含此前漏登记的 not-found / 冲突 / 上游故障码）
- 状态前置条件类码保持 400 / FAILED_PRECONDITION（google.rpc.Code 规范映射，不改行为）
- gRPC 拦截器与 HTTP 处理器读同一张表
"""

from __future__ import annotations

from http import HTTPStatus

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from core.exceptions import register_exception_handlers
from domain.common.exceptions import (
    BusinessException,
    FileNotUploadedException,
    FileUploadClosedException,
)
from domain.conversation.exceptions import (
    AgentConfigNameExistsException,
    AgentConfigNotFoundException,
    LLMProviderException,
    LLMTimeoutException,
    RunNotFoundException,
)
from domain.document.exceptions import DocumentNotReadyException
from shared.codes import TRANSPORT_STATUS, BusinessCode, transport_status

# google/rpc/code.proto 的规范状态名（grpc.StatusCode 成员名与之一致）
_GRPC_STATUS_NAMES = {
    "OK",
    "CANCELLED",
    "UNKNOWN",
    "INVALID_ARGUMENT",
    "DEADLINE_EXCEEDED",
    "NOT_FOUND",
    "ALREADY_EXISTS",
    "PERMISSION_DENIED",
    "RESOURCE_EXHAUSTED",
    "FAILED_PRECONDITION",
    "ABORTED",
    "OUT_OF_RANGE",
    "UNIMPLEMENTED",
    "INTERNAL",
    "UNAVAILABLE",
    "DATA_LOSS",
    "UNAUTHENTICATED",
}


def test_every_error_code_declares_transport_status() -> None:
    missing = [
        code.name
        for code in BusinessCode
        if code is not BusinessCode.SUCCESS and code not in TRANSPORT_STATUS
    ]
    assert not missing, f"新增业务码必须在 shared.codes.TRANSPORT_STATUS 登记: {missing}"
    assert BusinessCode.SUCCESS not in TRANSPORT_STATUS, "SUCCESS 不是错误，不应有错误状态"


def test_grpc_status_names_are_canonical() -> None:
    invalid = {
        code.name: status.grpc
        for code, status in TRANSPORT_STATUS.items()
        if status.grpc not in _GRPC_STATUS_NAMES
    }
    assert not invalid


def test_unregistered_codes_keep_legacy_fallback() -> None:
    fallback = (HTTPStatus.BAD_REQUEST, "FAILED_PRECONDITION")
    assert transport_status(99999) == fallback
    # 误用 BusinessException(code=SUCCESS)：不能渲染成 200 错误体 / gRPC abort(OK)
    assert transport_status(BusinessCode.SUCCESS) == fallback


def _app_raising(exc: BusinessException) -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    async def boom():
        raise exc

    return app


@pytest.mark.parametrize(
    ("exc", "expected_status"),
    [
        # 此前漏登记、被默认值吞成 400 的码
        (AgentConfigNotFoundException(1), 404),
        (RunNotFoundException(1), 404),
        (AgentConfigNameExistsException("dup"), 409),
        (LLMProviderException(), 502),
        (LLMTimeoutException(), 504),
        # 状态前置条件：保持 400（不改既有行为）
        (DocumentNotReadyException(1), 400),
        # 直传确认早于对象落盘：可重试的状态冲突
        (FileNotUploadedException(1), 409),
        # 已确认/已删除资产不再签发上传链接
        (FileUploadClosedException(1), 409),
    ],
)
async def test_http_handler_renders_declared_status(
    exc: BusinessException, expected_status: int
) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=_app_raising(exc)), base_url="http://test"
    ) as client:
        resp = await client.get("/boom")

    assert resp.status_code == expected_status
    assert resp.json()["code"] == exc.code


def test_grpc_interceptor_reads_the_same_table() -> None:
    grpc = pytest.importorskip("grpc")
    from grpc_app.interceptors.exceptions import _business_code_to_grpc_status

    for code, status in TRANSPORT_STATUS.items():
        assert _business_code_to_grpc_status(code) == grpc.StatusCode[status.grpc]
    assert _business_code_to_grpc_status(BusinessCode.AGENT_CONFIG_NOT_FOUND) == (
        grpc.StatusCode.NOT_FOUND
    )
