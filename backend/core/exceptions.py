"""
自定义异常映射与全局异常处理器
"""

import traceback
import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status as http_status

from core.i18n import get_locale, t
from core.logging_config import get_logger
from domain.common.exceptions import BusinessException
from shared.codes import BusinessCode, transport_status

from .response import error_response


class RateLimitException(BusinessException):
    """限流异常"""

    def __init__(self, retry_after: Optional[int] = None):
        details = {"retry_after": retry_after} if retry_after else None
        super().__init__(
            code=BusinessCode.TOO_MANY_REQUESTS,
            message="Too many requests, please try again later",
            error_type="RateLimit",
            details=details,
            message_key="rate.limited",
            format_params=details or {},
        )


def register_exception_handlers(app: FastAPI):
    """
    注册全局异常处理器

    Args:
        app: FastAPI应用实例
    """

    # logger
    logger = get_logger(__name__)

    @app.exception_handler(BusinessException)
    async def business_exception_handler(request: Request, exc: BusinessException):
        """处理业务异常"""
        request_id = getattr(getattr(request, "state", object()), "request_id", None) or str(
            uuid.uuid4()
        )
        locale = get_locale()
        # Render i18n message if message_key is provided, otherwise fallback to original message
        fmt_params = getattr(exc, "format_params", None)
        params = fmt_params if isinstance(fmt_params, dict) else (exc.details or {})
        message_key = getattr(exc, "message_key", None)
        translated = t(message_key or exc.message, **params)
        # 翻译表缺这个 key 时 t() 原样返回 key：退回异常自带的默认文案，不把 key 当提示漏给用户
        if message_key and translated == message_key:
            translated = exc.message
        response = error_response(
            code=exc.code,
            message=translated,
            error_type=exc.error_type,
            details=exc.details,
            field=exc.field,
            request_id=request_id,
            locale=locale,
            message_key=message_key,
        )
        status_code = int(transport_status(exc.code).http)
        # 对于401可选地返回WWW-Authenticate，但仅对需要的场景添加
        headers = (
            {"WWW-Authenticate": "Bearer"}
            if status_code == http_status.HTTP_401_UNAUTHORIZED
            else None
        )
        return JSONResponse(
            status_code=status_code, content=response.model_dump(mode="json"), headers=headers
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """处理参数验证异常"""
        request_id = getattr(getattr(request, "state", object()), "request_id", None) or str(
            uuid.uuid4()
        )
        # 只保留 loc/msg/type：pydantic 的 input/ctx 会把原始入参回显进响应体
        # （如注册校验失败时的密码明文），前端错误追踪采集响应后即成泄露面
        errors = [
            {"loc": e.get("loc"), "msg": e.get("msg"), "type": e.get("type")} for e in exc.errors()
        ]

        # 提取第一个错误的详细信息
        first_error = errors[0] if errors else {}
        field = ".".join(str(loc) for loc in first_error.get("loc", [])[1:])

        locale = get_locale()
        response = error_response(
            code=BusinessCode.PARAM_VALIDATION_ERROR,
            message=t("validation.failed", reason=first_error.get("msg", "unknown")),
            error_type="ValidationError",
            details={"errors": errors},
            field=field,
            request_id=request_id,
            locale=locale,
            message_key="validation.failed",
        )
        return JSONResponse(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=response.model_dump(mode="json"),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """处理HTTP异常"""
        request_id = getattr(getattr(request, "state", object()), "request_id", None) or str(
            uuid.uuid4()
        )

        # 映射HTTP状态码到业务码
        code_mapping = {
            400: BusinessCode.PARAM_ERROR,
            401: BusinessCode.UNAUTHORIZED,
            403: BusinessCode.FORBIDDEN,
            404: BusinessCode.NOT_FOUND,
            422: BusinessCode.PARAM_VALIDATION_ERROR,
            429: BusinessCode.TOO_MANY_REQUESTS,
            500: BusinessCode.SYSTEM_ERROR,
            503: BusinessCode.SERVICE_UNAVAILABLE,
        }
        # 兜底按状态码段归类，避免 4xx 被误标成 SYSTEM_ERROR
        default_code = (
            BusinessCode.BUSINESS_ERROR if exc.status_code < 500 else BusinessCode.SYSTEM_ERROR
        )
        code = code_mapping.get(exc.status_code, default_code)

        locale = get_locale()
        response = error_response(
            code=code,
            message=str(exc.detail),
            error_type="HTTPError",
            details={"status_code": exc.status_code},
            request_id=request_id,
            locale=locale,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=response.model_dump(mode="json"),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """处理所有未捕获的异常"""
        request_id = getattr(getattr(request, "state", object()), "request_id", None) or str(
            uuid.uuid4()
        )

        # 在开发环境可以返回详细错误信息
        details = None
        if app.debug:
            details = {"exception": str(exc), "traceback": traceback.format_exc()}

        locale = get_locale()
        response = error_response(
            code=BusinessCode.SYSTEM_ERROR,
            message=t("error.internal"),
            error_type="SystemError",
            details=details,
            request_id=request_id,
            locale=locale,
            message_key="error.internal",
        )

        # 记录日志（使用结构化日志）
        logger.error(
            "unhandled_exception",
            request_id=request_id,
            error=str(exc),
            exc_info=True,
        )

        return JSONResponse(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=response.model_dump(mode="json"),
        )
