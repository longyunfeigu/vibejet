# input: ASGI scope/receive/send, core.config settings, core.observability.tracing
# output: RequestIDMiddleware (纯 ASGI), get_request_id, get_client_ip, request_id_var, client_ip_var, user_id_var
# owner: wanhua.gu
# pos: 表示层中间件 - 请求追踪 ID 注入与上下文绑定（纯 ASGI 实现）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""
Request ID 中间件（纯 ASGI 实现）
用于生成或透传追踪 ID，并通过 contextvars 传递给日志系统。

注意：不使用 BaseHTTPMiddleware。详见 api/middleware/__init__.py。
"""

import uuid
from contextvars import ContextVar
from typing import Optional

import structlog
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from core.config import settings
from core.observability.tracing import get_current_trace_id, set_request_span_attributes

# 定义context变量，用于在请求生命周期内共享request_id
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
client_ip_var: ContextVar[Optional[str]] = ContextVar("client_ip", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)


class RequestIDMiddleware:
    """
    Request ID 追踪中间件（纯 ASGI）

    功能：
    1. 从请求头获取或生成新的 request_id
    2. 将 request_id / client_ip 存入 contextvars，供日志系统使用
    3. 在响应头中返回 X-Request-ID（以及可选的 X-Trace-ID）
    """

    HEADER_NAME = "X-Request-ID"
    HEADER_NAME_BYTES = b"x-request-id"
    TRACE_HEADER_BYTES = b"x-trace-id"

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = self._get_header(scope, self.HEADER_NAME) or str(uuid.uuid4())
        client_ip = self._get_client_ip(scope)
        method = scope.get("method", "")
        path = scope.get("path", "")

        # 写入 scope.state，供下游 endpoint / 中间件访问
        state = scope.setdefault("state", {})
        state["request_id"] = request_id
        state["client_ip"] = client_ip

        # 设置 contextvars，供 structlog / 业务层使用
        request_id_token = request_id_var.set(request_id)
        client_ip_token = client_ip_var.set(client_ip)

        # 绑定结构化日志上下文
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            client_ip=client_ip,
            method=method,
            path=path,
        )

        # 给当前 span 打标签（若 tracing 可用）
        set_request_span_attributes(
            request_id=request_id,
            client_ip=client_ip,
            http_method=method,
            http_path=path,
        )

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((self.HEADER_NAME_BYTES, request_id.encode("latin-1")))

                trace_id = get_current_trace_id()
                if trace_id and settings.tracing.expose_trace_id:
                    headers.append((self.TRACE_HEADER_BYTES, trace_id.encode("latin-1")))

                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            request_id_var.reset(request_id_token)
            client_ip_var.reset(client_ip_token)

    @staticmethod
    def _get_header(scope: Scope, name: str) -> str:
        """从 ASGI scope headers 中获取指定 header 值（大小写不敏感）。"""
        name_lower = name.lower().encode("latin-1")
        for key, value in scope.get("headers", []):
            if key == name_lower:
                return value.decode("latin-1")
        return ""

    def _get_client_ip(self, scope: Scope) -> str:
        """获取客户端真实 IP（优先 X-Forwarded-For，其次 X-Real-IP，最后 scope client）。"""
        x_forwarded_for = self._get_header(scope, "X-Forwarded-For")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()

        x_real_ip = self._get_header(scope, "X-Real-IP")
        if x_real_ip:
            return x_real_ip

        client = scope.get("client")
        if client:
            return client[0]
        return "unknown"


def get_request_id() -> Optional[str]:
    """获取当前请求的 request_id；不在请求上下文中时返回 None。"""
    return request_id_var.get()


def get_client_ip() -> Optional[str]:
    """获取当前请求的客户端 IP；不在请求上下文中时返回 None。"""
    return client_ip_var.get()
