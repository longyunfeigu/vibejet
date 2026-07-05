# input: anthropic SDK（optional extra: anthropic）, LLMPort 接口
# output: AnthropicProvider LLM 实现（文本 + tool use + json_schema 结构化输出）
# owner: wanhua.gu
# pos: 基础设施层 - Anthropic 原生 SDK LLM 提供者实现（system 抽取、usage 映射、内容块原生映射、json_schema 走强制 tool call）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Anthropic SDK implementation of LLMPort.

API shape differences vs OpenAI handled here so the application layer
stays provider-agnostic:
- system prompts are a separate ``system`` parameter, not a message role
- ``max_tokens`` is mandatory on every request
- usage arrives as input_tokens/output_tokens (split across stream events)
- the port's content blocks map 1:1 to Anthropic native blocks
- json_schema structured output is implemented as a forced tool call
  (portable across the whole supported SDK range, no beta API needed);
  the tool arguments come back to the caller as JSON text in ``content``
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Optional

from anthropic import AsyncAnthropic

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


def _block_to_dict(block: TextBlock | ToolUseBlock | ToolResultBlock) -> dict:
    if isinstance(block, TextBlock):
        return {"type": "text", "text": block.text}
    if isinstance(block, ToolUseBlock):
        return {"type": "tool_use", "id": block.id, "name": block.name, "input": block.arguments}
    result: dict = {
        "type": "tool_result",
        "tool_use_id": block.tool_use_id,
        "content": block.content,
    }
    if block.is_error:
        result["is_error"] = True
    return result


def _map_tool_choice(tool_choice: str) -> dict:
    if tool_choice == "auto":
        return {"type": "auto"}
    if tool_choice == "required":
        return {"type": "any"}
    if tool_choice == "none":
        return {"type": "none"}
    return {"type": "tool", "name": tool_choice}


class AnthropicProvider:
    """LLMPort implementation using the Anthropic Python SDK."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: Optional[str] = None,
        default_model: str = "claude-sonnet-4-6",
        default_temperature: float = 0.7,
        default_max_tokens: int = 4096,
        timeout: int = 60,
        max_retries: int = 2,
    ) -> None:
        self._client = AsyncAnthropic(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )
        self._default_model = default_model
        self._default_temperature = default_temperature
        self._default_max_tokens = default_max_tokens

    @staticmethod
    def _split_messages(messages: list[LLMMessage]) -> tuple[Optional[str], list[dict]]:
        """Extract system messages into Anthropic's `system` param."""
        system_parts: list[str] = []
        chat: list[dict] = []
        for m in messages:
            if m.role == "system":
                if isinstance(m.content, str):
                    system_parts.append(m.content)
                else:
                    # 块列表形式的 system 消息：抽取文本块，不静默丢弃
                    system_parts.append(
                        "".join(b.text for b in m.content if isinstance(b, TextBlock))
                    )
            elif isinstance(m.content, str):
                chat.append({"role": m.role, "content": m.content})
            else:
                chat.append(
                    {"role": m.role, "content": [_block_to_dict(b) for b in m.content]}
                )
        return ("\n\n".join(system_parts) or None), chat

    def _request_kwargs(
        self,
        messages: list[LLMMessage],
        *,
        model: Optional[str],
        temperature: Optional[float],
        max_tokens: Optional[int],
        tools: Optional[list[ToolDefinition]] = None,
        tool_choice: Optional[str] = None,
    ) -> dict:
        system, chat = self._split_messages(messages)
        temp = temperature if temperature is not None else self._default_temperature
        kwargs: dict = {
            "model": model or self._default_model,
            "messages": chat,
            # Anthropic 要求显式 max_tokens
            "max_tokens": max_tokens or self._default_max_tokens,
            # Anthropic temperature 取值范围 [0, 1]
            "temperature": min(max(temp, 0.0), 1.0),
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = [
                {"name": t.name, "description": t.description, "input_schema": t.input_schema}
                for t in tools
            ]
            if tool_choice:
                kwargs["tool_choice"] = _map_tool_choice(tool_choice)
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
        if tools and json_schema:
            raise ValueError("tools and json_schema are mutually exclusive")
        structured = json_schema is not None
        if structured:
            tools = [
                ToolDefinition(
                    name=STRUCTURED_OUTPUT_TOOL_NAME,
                    description="Record the structured output conforming to the schema.",
                    input_schema=json_schema,
                )
            ]
            tool_choice = STRUCTURED_OUTPUT_TOOL_NAME

        response = await self._client.messages.create(
            **self._request_kwargs(
                messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                tool_choice=tool_choice,
            )
        )
        content = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )
        tool_calls = [
            ToolCall(id=block.id, name=block.name, arguments=dict(block.input or {}))
            for block in response.content
            if getattr(block, "type", "") == "tool_use"
        ]
        finish_reason = response.stop_reason
        if structured:
            structured_calls = [c for c in tool_calls if c.name == STRUCTURED_OUTPUT_TOOL_NAME]
            if not structured_calls:
                # 强制 tool_choice 也可能拿不到 tool call（refusal / max_tokens 截断），
                # 静默返回散文会让下游 json.loads 在远处爆炸，这里直接报错
                raise ValueError(
                    "structured output requested but no "
                    f"'{STRUCTURED_OUTPUT_TOOL_NAME}' tool_use block returned "
                    f"(stop_reason={response.stop_reason})"
                )
            # 强制 tool call 是实现细节：拆包成 JSON 文本返回，对调用方呈现为普通完成；
            # finish_reason 统一为 "stop"，与 OpenAI 结构化输出路径一致
            content = json.dumps(structured_calls[0].arguments, ensure_ascii=False)
            finish_reason = "stop"
            tool_calls = []

        prompt_tokens = response.usage.input_tokens if response.usage else 0
        completion_tokens = response.usage.output_tokens if response.usage else 0
        return LLMResponse(
            content=content,
            model=response.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            finish_reason=finish_reason,
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
        resolved_model = kwargs["model"]
        prompt_tokens = 0
        completion_tokens = 0
        finish_reason: Optional[str] = None
        accumulator = _ToolUseAccumulator()

        async with self._client.messages.stream(**kwargs) as stream:
            async for event in stream:
                if event.type == "message_start":
                    usage = event.message.usage
                    prompt_tokens = getattr(usage, "input_tokens", 0) or 0
                elif event.type == "content_block_start":
                    accumulator.start(event.index, event.content_block)
                elif event.type == "content_block_delta":
                    delta = event.delta
                    delta_type = getattr(delta, "type", "")
                    if delta_type == "text_delta" and delta.text:
                        yield LLMChunk(content=delta.text, model=resolved_model)
                    elif delta_type == "input_json_delta":
                        accumulator.add_json(event.index, delta.partial_json or "")
                elif event.type == "content_block_stop":
                    accumulator.stop(event.index)
                elif event.type == "message_delta":
                    finish_reason = getattr(event.delta, "stop_reason", None) or finish_reason
                    usage = getattr(event, "usage", None)
                    if usage is not None:
                        completion_tokens = getattr(usage, "output_tokens", 0) or 0

        # 收尾 chunk：usage、finish_reason 与完整 tool_calls 统一在最后交付
        yield LLMChunk(
            content="",
            model=resolved_model,
            finish_reason=finish_reason,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            tool_calls=accumulator.calls,
        )


class _ToolUseAccumulator:
    """按 index 累积流式 tool_use 块（arguments 以 partial_json 字符串增量下发）。"""

    def __init__(self) -> None:
        self._pending: dict[int, dict[str, str]] = {}
        self.calls: list[ToolCall] = []

    def start(self, index: int, block: Any) -> None:
        if getattr(block, "type", "") == "tool_use":
            self._pending[index] = {"id": block.id, "name": block.name, "arguments": ""}

    def add_json(self, index: int, partial_json: str) -> None:
        if index in self._pending:
            self._pending[index]["arguments"] += partial_json

    def stop(self, index: int) -> None:
        slot = self._pending.pop(index, None)
        if slot is not None:
            self.calls.append(
                ToolCall(
                    id=slot["id"],
                    name=slot["name"],
                    arguments=parse_tool_arguments(slot["arguments"]),
                )
            )
