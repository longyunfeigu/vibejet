"""Helpers shared by the LLM provider implementations."""

from __future__ import annotations

import json
from typing import Any, Optional

from core.logging_config import get_logger
from infrastructure.external.circuit_breaker import is_downstream_httpx_failure

logger = get_logger(__name__)


class UpstreamResponseError(Exception):
    """The upstream answered 2xx but the body is not a generation result.

    例：OpenRouter 非流式请求在响应头发出后失败时，返回 200 + 只含 error 的 JSON（无 choices）；
    网关返回 200 + HTML。provider 取必需字段前先校验，把这类响应翻译成本异常，
    而不是让它在取字段处炸成 TypeError / AttributeError（那样与调用方 bug 无法区分）。
    """


# json_schema 结构化输出使用的 tool 名：OpenAI 用作 response_format 的 schema 名，
# Anthropic 用作强制调用的隐藏 tool 名（实现细节，不暴露给调用方）
STRUCTURED_OUTPUT_TOOL_NAME = "structured_output"


def parse_tool_arguments(raw: Optional[str]) -> dict[str, Any]:
    """Parse a model-emitted tool-arguments JSON string into a dict.

    Malformed JSON (e.g. truncated by a length stop) degrades to ``{}`` with a
    warning — callers detecting truncation should check the finish_reason.
    """
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("llm_tool_arguments_parse_failed", raw=raw[:200])
        return {}
    return parsed if isinstance(parsed, dict) else {}


def is_sdk_upstream_failure(
    exc: BaseException, *, api_error: type[Exception], status_error: type[Exception]
) -> bool:
    """熔断失败口径，OpenAI / Anthropic SDK 通用（两者异常体系同构）。

    除明确的 4xx 外，源自上游的错误都算上游故障。上游先回 200 再出错的情形尤其要靠这条
    "默认算故障"，它们都不带 5xx 状态码：流式中途的裸 httpx 断流/读超时、SSE error 事件
    （``api_error``）、status_code=200 的 ``status_error``（Anthropic overloaded_error）；
    非流式的 200 + 无效响应体（SDK 解析抛 JSONDecodeError，或 provider 抛 UpstreamResponseError）。
    我方代码抛的普通异常（参数校验、结构化输出被拒等）不算——按服务熔断时，一个出 bug 的
    调用点不能拖垮所有调用方。
    """
    if isinstance(exc, status_error):
        return not 400 <= getattr(exc, "status_code", 0) < 500
    return isinstance(
        exc, (api_error, UpstreamResponseError, json.JSONDecodeError)
    ) or is_downstream_httpx_failure(exc)
