# input: 无（仅标准库 + core.logging_config）
# output: parse_tool_arguments 安全 JSON 解析、STRUCTURED_OUTPUT_TOOL_NAME 常量
# owner: unknown
# pos: 基础设施层 - LLM provider 共享助手（tool 参数解析、结构化输出 tool 名）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Helpers shared by the LLM provider implementations."""

from __future__ import annotations

import json
from typing import Any, Optional

from core.logging_config import get_logger

logger = get_logger(__name__)

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
