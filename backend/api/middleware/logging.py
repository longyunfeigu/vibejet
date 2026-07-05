# input: ASGI scope/receive/send, core.config settings, core.logging_config logger
# output: LoggingMiddleware (纯 ASGI)
# owner: wanhua.gu
# pos: 表示层中间件 - 请求/响应日志记录（纯 ASGI 实现）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""
请求/响应日志中间件（纯 ASGI 实现）
记录所有HTTP请求和响应，包括耗时统计

注意：不使用 BaseHTTPMiddleware，避免 request.body() 消耗 receive 通道导致死锁。
通过 receive/send wrapper 被动捕获请求体和响应状态。
"""

import time
from typing import Any
from urllib.parse import unquote, parse_qs
import json

from starlette.types import ASGIApp, Receive, Scope, Send

from core.logging_config import get_logger
from core.config import settings


logger = get_logger(__name__)


class LoggingMiddleware:
    """
    日志记录中间件（纯 ASGI）

    功能：
    1. 记录请求信息（方法、路径、参数等）
    2. 记录响应信息（状态码、耗时等）
    3. 记录异常信息
    4. 统计请求处理时间
    5. 可选记录请求体（通过 receive wrapper 透传捕获，不消耗 body）
    """

    # 跳过日志的路径
    SKIP_PATHS = {
        "/health",
        "/health/live",
        "/health/ready",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    # 敏感字段，日志中需要脱敏（含凭证/令牌类：refresh_token 可换新令牌对、
    # OAuth code 在有效期内可换身份，落日志即泄露面）
    SENSITIVE_FIELDS = {
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
    }

    def __init__(self, app: ASGIApp):
        self.app = app
        # 从配置读取可调参数
        self.enable_body_log_default: bool = settings.LOG_REQUEST_BODY_ENABLE_BY_DEFAULT
        self.max_body_log_bytes: int = settings.LOG_REQUEST_BODY_MAX_BYTES
        self.allow_multipart_body_log: bool = settings.LOG_REQUEST_BODY_ALLOW_MULTIPART

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in self.SKIP_PATHS:
            await self.app(scope, receive, send)
            return

        start_time = time.time()

        # 从 scope 提取请求信息
        request_info = self._build_request_info(scope)

        # 记录请求日志
        logger.info("request_started", **request_info)

        # 判断是否需要捕获 body
        method = scope.get("method", "")
        should_log_body = method in ("POST", "PUT", "PATCH") and self._should_log_body_from_scope(
            scope
        )

        # receive wrapper: 透传 body 给下游，同时捕获副本用于日志
        body_chunks: list[bytes] = []
        total_captured: int = 0

        async def receive_wrapper() -> dict:
            nonlocal total_captured
            message = await receive()
            if message["type"] == "http.request" and should_log_body:
                chunk = message.get("body", b"")
                if chunk and total_captured < self.max_body_log_bytes:
                    capture = chunk[: self.max_body_log_bytes - total_captured]
                    body_chunks.append(capture)
                    total_captured += len(capture)
            return message  # 原样返回，下游正常读取

        # send wrapper: 捕获状态码 + 注入 X-Process-Time
        status_code = 500

        async def send_wrapper(message: dict) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 500)
                # 注入 X-Process-Time 响应头
                duration = time.time() - start_time
                headers = list(message.get("headers", []))
                headers.append((b"x-process-time", f"{duration:.3f}".encode()))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive_wrapper, send_wrapper)

            duration = time.time() - start_time

            # body 日志（在请求完成后记录）
            if body_chunks and should_log_body:
                body_info = self._parse_and_sanitize_body(scope, b"".join(body_chunks))
                if body_info is not None:
                    request_info["body"] = body_info

            self._log_response(status_code, duration, request_info)

        except Exception as exc:
            duration = time.time() - start_time

            if body_chunks and should_log_body:
                body_info = self._parse_and_sanitize_body(scope, b"".join(body_chunks))
                if body_info is not None:
                    request_info["body"] = body_info

            logger.error(
                "request_failed",
                duration=duration,
                error=str(exc),
                error_type=type(exc).__name__,
                **request_info,
                exc_info=True,
            )
            raise

    # ------------------------------------------------------------------
    # 从 scope 提取信息的辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _get_header(scope: Scope, name: str) -> str:
        """从 ASGI scope headers 中获取指定 header 值（大小写不敏感）。"""
        name_lower = name.lower().encode("latin-1")
        for key, value in scope.get("headers", []):
            if key == name_lower:
                return value.decode("latin-1")
        return ""

    def _build_request_info(self, scope: Scope) -> dict:
        """从 ASGI scope 构建请求信息字典。"""
        info: dict[str, Any] = {
            "method": scope.get("method", ""),
            "path": scope.get("path", ""),
        }

        # query params
        qs = scope.get("query_string", b"")
        if qs:
            info["query_params"] = {
                k: v if len(v) > 1 else v[0]
                for k, v in parse_qs(unquote(qs.decode("latin-1"))).items()
            }

        # path params（路由匹配后才有）
        path_params = scope.get("path_params")
        if path_params:
            info["path_params"] = path_params

        # User-Agent
        user_agent = self._get_header(scope, "User-Agent")
        if user_agent:
            info["user_agent"] = user_agent

        # Referer
        referer = self._get_header(scope, "Referer")
        if referer:
            info["referer"] = referer

        return info

    def _should_log_body_from_scope(self, scope: Scope) -> bool:
        """判断是否需要记录请求体。"""
        # X-Log-Body 请求头覆盖：force-true 仅在 DEBUG 下生效——生产环境不允许
        # 任意客户端用一个请求头强制把请求体刷进服务端日志（日志膨胀 + 令牌入日志）
        header = self._get_header(scope, "X-Log-Body").lower()
        if header in ("true", "1", "yes"):
            return bool(settings.DEBUG)
        if header in ("false", "0", "no"):
            return False
        # 按环境默认
        return bool(self.enable_body_log_default and settings.DEBUG)

    def _parse_and_sanitize_body(self, scope: Scope, body: bytes) -> Any:
        """解析并脱敏已捕获的请求体。"""
        if not body:
            return None

        content_type = self._get_header(scope, "Content-Type").lower()

        # multipart 处理
        if "multipart/form-data" in content_type:
            if not self.allow_multipart_body_log:
                return None
            return {"multipart": True}

        # 截断（receive wrapper 已限制大小，此处双重保险）
        snippet = body[: self.max_body_log_bytes]

        parsed: Any = None
        if "application/json" in content_type:
            try:
                parsed = json.loads(snippet.decode("utf-8", errors="ignore"))
            except Exception:
                parsed = snippet.decode("utf-8", errors="ignore")
        elif "application/x-www-form-urlencoded" in content_type:
            try:
                parsed = {
                    k: v if len(v) > 1 else v[0]
                    for k, v in parse_qs(snippet.decode("utf-8", errors="ignore")).items()
                }
            except Exception:
                parsed = snippet.decode("utf-8", errors="ignore")
        else:
            parsed = snippet.decode("utf-8", errors="ignore")

        return self._sanitize_data(parsed)

    def _sanitize_data(self, data: Any) -> Any:
        """递归脱敏敏感字段。"""
        try:
            if isinstance(data, dict):
                return {
                    k: ("***" if k.lower() in self.SENSITIVE_FIELDS else self._sanitize_data(v))
                    for k, v in data.items()
                }
            if isinstance(data, list):
                return [self._sanitize_data(v) for v in data]
            if isinstance(data, tuple):
                return tuple(self._sanitize_data(v) for v in data)
            return data
        except Exception:
            return data

    def _log_response(self, status_code: int, duration: float, request_info: dict) -> None:
        """根据状态码选择日志级别记录响应。"""
        log_data = {"status_code": status_code, "duration": duration, **request_info}

        if status_code < 400:
            logger.info("request_completed", **log_data)
        elif status_code < 500:
            logger.warning("request_client_error", **log_data)
        else:
            logger.error("request_server_error", **log_data)
