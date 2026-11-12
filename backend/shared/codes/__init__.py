"""
Shared business codes used across layers (Domain/Core/API).

This package exposes BusinessCode and its per-transport status table at `shared.codes`.
"""

from enum import IntEnum
from http import HTTPStatus
from typing import NamedTuple


class BusinessCode(IntEnum):
    """Unified business status codes (single source of truth)."""

    # Success
    SUCCESS = 0

    # Parameter errors (1xxxx)
    PARAM_ERROR = 10000
    PARAM_MISSING = 10001
    PARAM_TYPE_ERROR = 10002
    PARAM_VALIDATION_ERROR = 10003

    # Business errors (2xxxx)
    BUSINESS_ERROR = 20000
    USER_NOT_FOUND = 20001
    USER_ALREADY_EXISTS = 20002
    PASSWORD_ERROR = 20003
    NOT_FOUND = 20004  # Generic resource not found
    FILE_NOT_UPLOADED = 20005  # Direct-upload confirmed before the object exists in storage
    FILE_UPLOAD_CLOSED = 20006  # Asset no longer pending (confirmed/deleted); no new upload URL

    # Authorization errors (3xxxx)
    PERMISSION_ERROR = 30000
    UNAUTHORIZED = 30001
    FORBIDDEN = 30002

    # System errors (4xxxx)
    SYSTEM_ERROR = 40000
    DATABASE_ERROR = 40001
    NETWORK_ERROR = 40002
    SERVICE_UNAVAILABLE = 40003

    # Rate limiting (5xxxx)
    RATE_LIMIT_ERROR = 50000
    TOO_MANY_REQUESTS = 50001

    # Agent / AI (6xxxx)
    CONVERSATION_NOT_FOUND = 60001
    RUN_NOT_FOUND = 60003
    RUN_ALREADY_COMPLETED = 60004
    AGENT_CONFIG_NOT_FOUND = 60005
    AGENT_CONFIG_NAME_EXISTS = 60006
    LLM_PROVIDER_ERROR = 60010
    LLM_TIMEOUT = 60011
    DOCUMENT_NOT_FOUND = 60020
    DOCUMENT_NOT_READY = 60021
    DOCUMENT_ALREADY_PROCESSING = 60022


class TransportStatus(NamedTuple):
    """A business code's status on each transport."""

    http: HTTPStatus
    # grpc.StatusCode 成员名：shared 不能依赖可选的 grpc extra，由 gRPC 层按名解析
    grpc: str


# 业务码 → 传输层状态的唯一登记处（借鉴 Kratos errors：错误在定义处声明一次状态码）。
# HTTP 处理器与 gRPC 拦截器都从这里取；新增错误码必须在此登记，
# tests/test_error_status_mapping.py 对漏登记直接失败。SUCCESS 不是错误、不登记：
# 误用 BusinessException(code=SUCCESS) 时走兜底 400，而不是渲染成 200 错误体或 gRPC abort(OK)
TRANSPORT_STATUS: dict[BusinessCode, TransportStatus] = {
    BusinessCode.PARAM_ERROR: TransportStatus(HTTPStatus.BAD_REQUEST, "INVALID_ARGUMENT"),
    BusinessCode.PARAM_MISSING: TransportStatus(HTTPStatus.BAD_REQUEST, "INVALID_ARGUMENT"),
    BusinessCode.PARAM_TYPE_ERROR: TransportStatus(HTTPStatus.BAD_REQUEST, "INVALID_ARGUMENT"),
    BusinessCode.PARAM_VALIDATION_ERROR: TransportStatus(
        HTTPStatus.UNPROCESSABLE_ENTITY, "INVALID_ARGUMENT"
    ),
    # 状态前置条件不满足（未就绪/处理中/已完成）= 400 + FAILED_PRECONDITION，
    # 即 google.rpc.Code 的规范映射
    BusinessCode.BUSINESS_ERROR: TransportStatus(HTTPStatus.BAD_REQUEST, "FAILED_PRECONDITION"),
    BusinessCode.RUN_ALREADY_COMPLETED: TransportStatus(
        HTTPStatus.BAD_REQUEST, "FAILED_PRECONDITION"
    ),
    BusinessCode.DOCUMENT_NOT_READY: TransportStatus(HTTPStatus.BAD_REQUEST, "FAILED_PRECONDITION"),
    BusinessCode.DOCUMENT_ALREADY_PROCESSING: TransportStatus(
        HTTPStatus.BAD_REQUEST, "FAILED_PRECONDITION"
    ),
    # 越权访问伪装为 404（Epic-1 D1）：not-found 类业务码必须真渲染 404，
    # 否则"真不存在=400 / 越权=404"反而泄露存在性
    BusinessCode.NOT_FOUND: TransportStatus(HTTPStatus.NOT_FOUND, "NOT_FOUND"),
    BusinessCode.USER_NOT_FOUND: TransportStatus(HTTPStatus.NOT_FOUND, "NOT_FOUND"),
    BusinessCode.CONVERSATION_NOT_FOUND: TransportStatus(HTTPStatus.NOT_FOUND, "NOT_FOUND"),
    BusinessCode.RUN_NOT_FOUND: TransportStatus(HTTPStatus.NOT_FOUND, "NOT_FOUND"),
    BusinessCode.AGENT_CONFIG_NOT_FOUND: TransportStatus(HTTPStatus.NOT_FOUND, "NOT_FOUND"),
    BusinessCode.DOCUMENT_NOT_FOUND: TransportStatus(HTTPStatus.NOT_FOUND, "NOT_FOUND"),
    BusinessCode.USER_ALREADY_EXISTS: TransportStatus(HTTPStatus.CONFLICT, "ALREADY_EXISTS"),
    # 直传确认早于对象落盘：资源当前状态与请求冲突，客户端上传完成后重试即可
    BusinessCode.FILE_NOT_UPLOADED: TransportStatus(HTTPStatus.CONFLICT, "FAILED_PRECONDITION"),
    # 资产已确认/已删除后再要上传 URL：状态冲突，不再签发可覆盖对象的写链接
    BusinessCode.FILE_UPLOAD_CLOSED: TransportStatus(HTTPStatus.CONFLICT, "FAILED_PRECONDITION"),
    BusinessCode.AGENT_CONFIG_NAME_EXISTS: TransportStatus(HTTPStatus.CONFLICT, "ALREADY_EXISTS"),
    BusinessCode.PASSWORD_ERROR: TransportStatus(HTTPStatus.UNAUTHORIZED, "UNAUTHENTICATED"),
    BusinessCode.UNAUTHORIZED: TransportStatus(HTTPStatus.UNAUTHORIZED, "UNAUTHENTICATED"),
    BusinessCode.PERMISSION_ERROR: TransportStatus(HTTPStatus.FORBIDDEN, "PERMISSION_DENIED"),
    BusinessCode.FORBIDDEN: TransportStatus(HTTPStatus.FORBIDDEN, "PERMISSION_DENIED"),
    BusinessCode.RATE_LIMIT_ERROR: TransportStatus(
        HTTPStatus.TOO_MANY_REQUESTS, "RESOURCE_EXHAUSTED"
    ),
    BusinessCode.TOO_MANY_REQUESTS: TransportStatus(
        HTTPStatus.TOO_MANY_REQUESTS, "RESOURCE_EXHAUSTED"
    ),
    BusinessCode.SYSTEM_ERROR: TransportStatus(HTTPStatus.INTERNAL_SERVER_ERROR, "INTERNAL"),
    BusinessCode.DATABASE_ERROR: TransportStatus(HTTPStatus.INTERNAL_SERVER_ERROR, "INTERNAL"),
    BusinessCode.NETWORK_ERROR: TransportStatus(HTTPStatus.INTERNAL_SERVER_ERROR, "UNAVAILABLE"),
    BusinessCode.SERVICE_UNAVAILABLE: TransportStatus(
        HTTPStatus.SERVICE_UNAVAILABLE, "UNAVAILABLE"
    ),
    # 上游（LLM provider）故障是服务端问题，不能算客户端的 4xx
    BusinessCode.LLM_PROVIDER_ERROR: TransportStatus(HTTPStatus.BAD_GATEWAY, "UNAVAILABLE"),
    BusinessCode.LLM_TIMEOUT: TransportStatus(HTTPStatus.GATEWAY_TIMEOUT, "DEADLINE_EXCEEDED"),
}

# 未进 BusinessCode 的裸 int 码沿用旧默认
_UNREGISTERED = TransportStatus(HTTPStatus.BAD_REQUEST, "FAILED_PRECONDITION")


def transport_status(code: int) -> TransportStatus:
    """Look up the declared transport status of a business code."""
    try:
        return TRANSPORT_STATUS[BusinessCode(code)]
    except (ValueError, KeyError):
        return _UNREGISTERED


__all__ = ["BusinessCode", "TransportStatus", "TRANSPORT_STATUS", "transport_status"]
