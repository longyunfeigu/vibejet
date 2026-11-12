from __future__ import annotations

import contextlib
import contextvars
import uuid
from typing import Awaitable, Callable

import grpc

REQUEST_ID_META_KEY = "x-request-id"
_request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "grpc_request_id", default=None
)


def get_request_id() -> str | None:
    return _request_id_var.get()


class RequestIdInterceptor(grpc.aio.ServerInterceptor):
    async def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], Awaitable[grpc.RpcMethodHandler]],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler:
        handler = await continuation(handler_call_details)
        if handler is None:
            return handler

        async def _unary_unary(request, context: grpc.aio.ServicerContext):
            # Try to get request-id from incoming metadata
            md = dict(handler_call_details.invocation_metadata or [])
            request_id = md.get(REQUEST_ID_META_KEY)
            if not request_id:
                request_id = str(uuid.uuid4())

            # Attach as trailing metadata so the client can correlate
            with contextlib.suppress(Exception):
                context.set_trailing_metadata(((REQUEST_ID_META_KEY, request_id),))
            token = _request_id_var.set(request_id)
            try:
                return await handler.unary_unary(request, context)
            finally:
                _request_id_var.reset(token)

        # Only wrap the unary-unary case for now (current server only supports unary-unary in interceptors)
        if handler.unary_unary:
            return grpc.unary_unary_rpc_method_handler(
                _unary_unary,
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )
        return handler
