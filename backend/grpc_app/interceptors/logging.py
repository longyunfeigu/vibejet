from __future__ import annotations

import contextlib
import time
from typing import Any, Awaitable, Callable

import grpc

from core.logging_config import get_logger
from grpc_app.interceptors.exceptions import is_mapped_error
from grpc_app.interceptors.request_id import get_request_id

logger = get_logger(__name__)


def _abort_status_code(exc: Exception) -> Any:
    """Return the gRPC status carried by abort-style errors via code(); None if absent or failing."""
    with contextlib.suppress(Exception):
        if hasattr(exc, "code") and callable(exc.code):
            return exc.code()
    return None


def _already_reported(exc: Exception) -> bool:
    """True when the error was already mapped/aborted (and logged) by the exception interceptor."""
    # Many server-side aborts raise grpc.RpcError / AbortError with code()/details()
    return is_mapped_error() or _abort_status_code(exc) is not None


def _log_request_done(method: str, start: float) -> None:
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "grpc_request_done",
        method=method,
        elapsed_ms=round(elapsed_ms, 2),
        request_id=get_request_id(),
    )


class LoggingInterceptor(grpc.aio.ServerInterceptor):
    async def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], Awaitable[grpc.RpcMethodHandler]],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler:
        handler = await continuation(handler_call_details)
        # Only unary-unary handlers are wrapped; anything else (including None) passes through
        if handler is None or not handler.unary_unary:
            return handler

        method = handler_call_details.method

        async def _unary_unary(request, context: grpc.aio.ServicerContext):
            start = time.perf_counter()
            try:
                peer = context.peer() if hasattr(context, "peer") else None
                logger.info("grpc_request", method=method, peer=peer, request_id=get_request_id())
                return await handler.unary_unary(request, context)
            except grpc.RpcError:
                # Already mapped/aborted by exception interceptor; avoid duplicate error logs here
                raise
            except Exception as exc:
                # Normalize gRPC abort errors (with code/details) vs truly unhandled exceptions.
                if not _already_reported(exc):
                    # Unknown/unexpected exception -> log with stack
                    logger.error(
                        "grpc_unhandled_error",
                        method=method,
                        error=str(exc),
                        exc_info=True,
                        request_id=get_request_id(),
                    )
                raise
            finally:
                _log_request_done(method, start)

        return grpc.unary_unary_rpc_method_handler(
            _unary_unary,
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )
