"""
请求/响应日志中间件（纯 ASGI 实现）
记录所有HTTP请求和响应，包括耗时统计

注意：不使用 BaseHTTPMiddleware，避免 request.body() 消耗 receive 通道导致死锁。
通过 receive/send wrapper 被动捕获请求体和响应状态。
"""

import json
import time
from typing import Any, cast
from urllib.parse import parse_qs

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from core.config import settings
from core.logging_config import get_logger

logger = get_logger(__name__)


class _RequestCapture:
    """单个请求的被动捕获状态，提供包装后的 receive/send。

    - receive：原样透传消息给下游，允许时截取请求体副本（不超过上限）
    - send：记录响应状态码，并注入 X-Process-Time 响应头
    """

    def __init__(
        self,
        receive: Receive,
        send: Send,
        *,
        start_time: float,
        capture_body: bool,
        max_body_bytes: int,
    ) -> None:
        self._receive = receive
        self._send = send
        self._start_time = start_time
        self._max_body_bytes = max_body_bytes
        self._total_captured = 0
        self.capture_body = capture_body
        self.body_chunks: list[bytes] = []
        # 下游没发 http.response.start（例如直接抛异常）时按 500 记录
        self.status_code = 500

    def elapsed(self) -> float:
        return time.time() - self._start_time

    async def receive(self) -> Message:
        message = await self._receive()
        if message["type"] == "http.request" and self.capture_body:
            self._capture(message.get("body", b""))
        return message  # 原样返回，下游正常读取

    def _capture(self, chunk: bytes) -> None:
        if chunk and self._total_captured < self._max_body_bytes:
            capture = chunk[: self._max_body_bytes - self._total_captured]
            self.body_chunks.append(capture)
            self._total_captured += len(capture)

    async def send(self, message: Message) -> None:
        if message["type"] == "http.response.start":
            self.status_code = message.get("status", 500)
            # 注入 X-Process-Time 响应头（新建消息，不改动下游的原对象）
            duration = self.elapsed()
            headers = list(message.get("headers", []))
            headers.append((b"x-process-time", f"{duration:.3f}".encode()))
            message = {**message, "headers": headers}
        await self._send(message)


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
        if scope["type"] != "http" or scope.get("path", "") in self.SKIP_PATHS:
            await self.app(scope, receive, send)
            return
        await self._handle_http(scope, receive, send)

    async def _handle_http(self, scope: Scope, receive: Receive, send: Send) -> None:
        """记录一次 HTTP 请求：开始日志 → 透传给下游 → 完成或失败日志。"""
        start_time = time.time()

        # 从 scope 提取请求信息并记录请求日志
        request_info = self._build_request_info(scope)
        logger.info("request_started", **request_info)

        # 判断是否需要捕获 body
        method = scope.get("method", "")
        should_log_body = method in ("POST", "PUT", "PATCH") and self._should_log_body_from_scope(
            scope
        )
        capture = _RequestCapture(
            receive,
            send,
            start_time=start_time,
            capture_body=should_log_body,
            max_body_bytes=self.max_body_log_bytes,
        )

        try:
            await self.app(scope, capture.receive, capture.send)

            duration = capture.elapsed()
            # body 日志（在请求完成后记录）
            self._attach_body(scope, request_info, capture)
            self._log_response(capture.status_code, duration, request_info)

        except Exception as exc:
            duration = capture.elapsed()
            self._attach_body(scope, request_info, capture)
            logger.error(
                "request_failed",
                duration=duration,
                error=str(exc),
                error_type=type(exc).__name__,
                **request_info,
                exc_info=True,
            )
            raise

    def _attach_body(self, scope: Scope, request_info: dict, capture: _RequestCapture) -> None:
        """把已捕获的请求体（解析并脱敏后）写入请求信息。"""
        if not (capture.body_chunks and capture.capture_body):
            return
        body_info = self._parse_and_sanitize_body(scope, b"".join(capture.body_chunks))
        if body_info is not None:
            request_info["body"] = body_info

    # ------------------------------------------------------------------
    # 从 scope 提取信息的辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _get_header(scope: Scope, name: str) -> str:
        """从 ASGI scope headers 中获取指定 header 值（大小写不敏感）。"""
        name_lower = name.lower().encode("latin-1")
        for key, value in scope.get("headers", []):
            if key == name_lower:
                return cast(str, value.decode("latin-1"))
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
            # 查询串里同样可能带令牌（如 ?token=），与请求体走同一套脱敏
            info["query_params"] = self._sanitize_data(
                {k: v if len(v) > 1 else v[0] for k, v in parse_qs(qs.decode("latin-1")).items()}
            )

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
                # 解析不了就没法按字段脱敏：只记长度，不记原文（原文里可能有密码/令牌）
                return f"<unparseable json, {len(snippet)} bytes>"
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
