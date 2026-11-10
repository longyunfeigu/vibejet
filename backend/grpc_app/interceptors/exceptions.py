from __future__ import annotations

import contextlib
import contextvars
from typing import Awaitable, Callable

import grpc

from core.logging_config import get_logger
from domain.common.exceptions import BusinessException
from grpc_app.interceptors.request_id import get_request_id
from shared.codes import BusinessCode, transport_status

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
    # 与 HTTP 处理器读同一张登记表（shared.codes.TRANSPORT_STATUS）
    return grpc.StatusCode[transport_status(code).grpc]


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
