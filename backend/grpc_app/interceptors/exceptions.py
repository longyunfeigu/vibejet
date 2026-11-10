from __future__ import annotations

import contextlib
import contextvars
from typing import Awaitable, Callable

import grpc

from core.logging_config import get_logger
from domain.common.exceptions import BusinessException
from grpc_app.interceptors.request_id import get_request_id
from shared.codes import BusinessCode

logger = get_logger(__name__)

# Mark that the current request has been mapped to a gRPC status
_mapped_error: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "grpc_mapped_error", default=False
)


def set_mapped_error() -> None:
    with contextlib.suppress(Exception):
        _mapped_error.set(True)


def is_mapped_error() -> bool:
    try:
        return bool(_mapped_error.get())
    except Exception:
        return False


def _business_code_to_grpc_status(code: int) -> grpc.StatusCode:
    try:
        bc = BusinessCode(code)
    except Exception:
        return grpc.StatusCode.FAILED_PRECONDITION

    mapping = {
        BusinessCode.PARAM_VALIDATION_ERROR: grpc.StatusCode.INVALID_ARGUMENT,
        BusinessCode.PARAM_ERROR: grpc.StatusCode.INVALID_ARGUMENT,
        BusinessCode.PARAM_MISSING: grpc.StatusCode.INVALID_ARGUMENT,
        BusinessCode.PARAM_TYPE_ERROR: grpc.StatusCode.INVALID_ARGUMENT,
        BusinessCode.USER_NOT_FOUND: grpc.StatusCode.NOT_FOUND,
        BusinessCode.NOT_FOUND: grpc.StatusCode.NOT_FOUND,
        # 与 HTTP 层一致（core/exceptions.py）：越权伪装为 not-found，跨传输层同语义
        BusinessCode.CONVERSATION_NOT_FOUND: grpc.StatusCode.NOT_FOUND,
        BusinessCode.DOCUMENT_NOT_FOUND: grpc.StatusCode.NOT_FOUND,
        BusinessCode.USER_ALREADY_EXISTS: grpc.StatusCode.ALREADY_EXISTS,
        BusinessCode.PASSWORD_ERROR: grpc.StatusCode.UNAUTHENTICATED,
        BusinessCode.UNAUTHORIZED: grpc.StatusCode.UNAUTHENTICATED,
        BusinessCode.FORBIDDEN: grpc.StatusCode.PERMISSION_DENIED,
        BusinessCode.PERMISSION_ERROR: grpc.StatusCode.PERMISSION_DENIED,
        BusinessCode.TOO_MANY_REQUESTS: grpc.StatusCode.RESOURCE_EXHAUSTED,
        BusinessCode.RATE_LIMIT_ERROR: grpc.StatusCode.RESOURCE_EXHAUSTED,
        BusinessCode.SERVICE_UNAVAILABLE: grpc.StatusCode.UNAVAILABLE,
        BusinessCode.SYSTEM_ERROR: grpc.StatusCode.INTERNAL,
        BusinessCode.DATABASE_ERROR: grpc.StatusCode.INTERNAL,
        BusinessCode.NETWORK_ERROR: grpc.StatusCode.UNAVAILABLE,
    }

    return mapping.get(bc, grpc.StatusCode.FAILED_PRECONDITION)


async def _abort_mapped(
    context: grpc.aio.ServicerContext,
    method: str,
    *,
    biz_code: str,
    error_type: str,
    status: grpc.StatusCode,
    message: str,
    details: str,
) -> None:
    """附加业务码 trailing metadata → 标记已映射 → 记简洁错误日志（无堆栈）→ abort。"""
    # trailing metadata 尽力而为：RPC 已结束等情况下设置失败则忽略
    with contextlib.suppress(Exception):
        context.set_trailing_metadata((("x-biz-code", biz_code), ("x-error-type", error_type)))
    set_mapped_error()
    logger.error(
        "grpc_mapped_error",
        method=method,
        code=biz_code,
        status=str(status),
        message=message,
        request_id=get_request_id(),
    )
    await context.abort(status, details)


async def _abort_business_error(
    context: grpc.aio.ServicerContext, method: str, exc: BusinessException
) -> None:
    await _abort_mapped(
        context,
        method,
        biz_code=str(exc.code),
        error_type=exc.error_type or "BusinessError",
        status=_business_code_to_grpc_status(exc.code),
        message=exc.message,
        details=exc.message,
    )


async def _abort_system_error(
    context: grpc.aio.ServicerContext, method: str, exc: Exception
) -> None:
    await _abort_mapped(
        context,
        method,
        biz_code=str(BusinessCode.SYSTEM_ERROR.value),
        error_type="SystemError",
        status=grpc.StatusCode.INTERNAL,
        message=str(exc),
        details="系统内部错误",
    )


class ExceptionMappingInterceptor(grpc.aio.ServerInterceptor):
    async def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], Awaitable[grpc.RpcMethodHandler]],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler:
        handler = await continuation(handler_call_details)
        # Only unary-unary handlers are wrapped; anything else (including None) passes through
        if handler is None or not handler.unary_unary:
            return handler

        async def _unary_unary(request, context: grpc.aio.ServicerContext):
            try:
                return await handler.unary_unary(request, context)
            except BusinessException as exc:
                await _abort_business_error(context, handler_call_details.method, exc)
            except Exception as exc:
                await _abort_system_error(context, handler_call_details.method, exc)

        return grpc.unary_unary_rpc_method_handler(
            _unary_unary,
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )
