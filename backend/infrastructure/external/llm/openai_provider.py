# input: openai SDK, LLMPort 接口
# output: OpenAIProvider LLM 实现（文本 + tool use + json_schema 结构化输出）
# owner: unknown
# pos: 基础设施层 - OpenAI SDK LLM 提供者实现（兼容 Azure/vLLM；内容块↔tool_calls/tool 消息映射）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""OpenAI SDK implementation of LLMPort.

API shape differences vs the port's Anthropic-style content blocks are
handled here so the application layer stays provider-agnostic:
- assistant ToolUseBlock → ``tool_calls`` field (arguments JSON-encoded)
- user ToolResultBlock → separate ``role="tool"`` messages
  (OpenAI has no is_error flag; error results are conveyed by prefixing the
  content with ``[tool error]`` so the model still sees the failure signal)
- finish_reason ``"tool_calls"`` is normalized to the port's ``"tool_use"``
- json_schema → native ``response_format`` (non-strict: strict mode would
  reject ordinary schemas lacking additionalProperties/required annotations)
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Optional

from openai import AsyncOpenAI

from application.ports.llm import (
    LLMChunk,
    LLMMessage,
    LLMResponse,
    TextBlock,
    ToolCall,
    ToolDefinition,
    ToolResultBlock,
    ToolUseBlock,
)
from infrastructure.external.llm._shared import (
    STRUCTURED_OUTPUT_TOOL_NAME,
    parse_tool_arguments,
)


def _normalize_finish_reason(finish_reason: Optional[str]) -> Optional[str]:
    return "tool_use" if finish_reason == "tool_calls" else finish_reason


class _ToolCallAccumulator:
    """按 index 累积流式 tool call 片段（OpenAI 把 arguments 拆成字符串增量下发）。"""

    def __init__(self) -> None:
        self._calls: dict[int, dict[str, str]] = {}

    def add(self, deltas: list) -> None:
        for delta in deltas:
            slot = self._calls.setdefault(delta.index, {"id": "", "name": "", "arguments": ""})
            if getattr(delta, "id", None):
                slot["id"] = delta.id
            function = getattr(delta, "function", None)
            if function is not None:
                if getattr(function, "name", None):
                    slot["name"] = function.name
                if getattr(function, "arguments", None):
                    slot["arguments"] += function.arguments

    def build(self) -> list[ToolCall]:
        return [
            ToolCall(
                id=slot["id"],
                name=slot["name"],
                arguments=parse_tool_arguments(slot["arguments"]),
            )
            for _, slot in sorted(self._calls.items())
        ]


class OpenAIProvider:
    """LLMPort implementation using the OpenAI Python SDK.

    Compatible with OpenAI, Azure OpenAI, vLLM, and other
    OpenAI-API-compatible providers via base_url.
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: Optional[str] = None,
        default_model: str = "gpt-4o-mini",
        default_temperature: float = 0.7,
        default_max_tokens: int = 4096,
        timeout: int = 60,
        max_retries: int = 2,
    ) -> None:
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )
        self._default_model = default_model
        self._default_temperature = default_temperature
        self._default_max_tokens = default_max_tokens

    @staticmethod
    def _build_messages(messages: list[LLMMessage]) -> list[dict]:
        result: list[dict] = []
        for m in messages:
            if isinstance(m.content, str):
                result.append({"role": m.role, "content": m.content})
                continue

            texts: list[str] = []
            tool_calls: list[dict] = []
            tool_results: list[ToolResultBlock] = []
            for block in m.content:
                if isinstance(block, TextBlock):
                    texts.append(block.text)
                elif isinstance(block, ToolUseBlock):
                    tool_calls.append(
                        {
                            "id": block.id,
                            "type": "function",
                            "function": {
                                "name": block.name,
                                "arguments": json.dumps(block.arguments, ensure_ascii=False),
                            },
                        }
                    )
                elif isinstance(block, ToolResultBlock):
                    tool_results.append(block)

            # tool result 在端口里挂在 user 消息下（Anthropic 形状）；
            # OpenAI 要求展开成紧跟 assistant tool_calls 的 role="tool" 消息
            for tr in tool_results:
                content = f"[tool error] {tr.content}" if tr.is_error else tr.content
                result.append(
                    {"role": "tool", "tool_call_id": tr.tool_use_id, "content": content}
                )
            if tool_calls:
                # 无文本时 content 必须是 None：部分兼容端点拒绝空字符串 + tool_calls 组合
                msg: dict = {
                    "role": m.role,
                    "content": "".join(texts) or None,
                    "tool_calls": tool_calls,
                }
                result.append(msg)
            elif texts:
                result.append({"role": m.role, "content": "".join(texts)})
        return result

    @staticmethod
    def _map_tool_choice(tool_choice: str) -> Any:
        if tool_choice in ("auto", "required", "none"):
            return tool_choice
        return {"type": "function", "function": {"name": tool_choice}}

    def _request_kwargs(
        self,
        messages: list[LLMMessage],
        *,
        model: Optional[str],
        temperature: Optional[float],
        max_tokens: Optional[int],
        tools: Optional[list[ToolDefinition]] = None,
        tool_choice: Optional[str] = None,
        json_schema: Optional[dict[str, Any]] = None,
    ) -> dict:
        if tools and json_schema:
            raise ValueError("tools and json_schema are mutually exclusive")
        kwargs: dict = {
            "model": model or self._default_model,
            "messages": self._build_messages(messages),
            "temperature": temperature if temperature is not None else self._default_temperature,
            "max_tokens": max_tokens or self._default_max_tokens,
        }
        if tools:
            kwargs["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.input_schema,
                    },
                }
                for t in tools
            ]
            if tool_choice:
                kwargs["tool_choice"] = self._map_tool_choice(tool_choice)
        if json_schema:
            # strict 模式要求 schema 全量标注 additionalProperties/required，
            # 会拒绝普通 JSON Schema；这里走非严格模式，与端口的 best-effort 契约一致
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": STRUCTURED_OUTPUT_TOOL_NAME,
                    "schema": json_schema,
                    "strict": False,
                },
            }
        return kwargs

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[list[ToolDefinition]] = None,
        tool_choice: Optional[str] = None,
        json_schema: Optional[dict[str, Any]] = None,
    ) -> LLMResponse:
        response = await self._client.chat.completions.create(
            **self._request_kwargs(
                messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                tool_choice=tool_choice,
                json_schema=json_schema,
            ),
            stream=False,
        )
        choice = response.choices[0]
        usage = response.usage
        tool_calls = [
            ToolCall(
                id=tc.id,
                name=tc.function.name,
                arguments=parse_tool_arguments(tc.function.arguments),
            )
            for tc in (choice.message.tool_calls or [])
        ]
        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            total_tokens=usage.total_tokens if usage else 0,
            finish_reason=_normalize_finish_reason(choice.finish_reason),
            tool_calls=tool_calls,
        )

    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[list[ToolDefinition]] = None,
        tool_choice: Optional[str] = None,
    ) -> AsyncIterator[LLMChunk]:
        kwargs = self._request_kwargs(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            tool_choice=tool_choice,
        )
        response = await self._client.chat.completions.create(
            **kwargs,
            stream=True,
            stream_options={"include_usage": True},
        )
        # 部分兼容端点（vLLM 等）的 chunk 不带 model，用请求的 model 兜底
        resolved_model = kwargs["model"]
        finish_reason: Optional[str] = None
        usage = None
        accumulator = _ToolCallAccumulator()

        async for chunk in response:
            resolved_model = chunk.model or resolved_model
            if chunk.usage:
                usage = chunk.usage
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            if choice.finish_reason:
                finish_reason = choice.finish_reason
            delta = choice.delta
            if delta.tool_calls:
                accumulator.add(delta.tool_calls)
            if delta.content:
                yield LLMChunk(content=delta.content, model=resolved_model)

        # 收尾 chunk：usage、finish_reason 与完整 tool_calls 统一在最后交付
        yield LLMChunk(
            content="",
            model=resolved_model,
            finish_reason=_normalize_finish_reason(finish_reason),
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            total_tokens=usage.total_tokens if usage else 0,
            tool_calls=accumulator.build(),
        )
