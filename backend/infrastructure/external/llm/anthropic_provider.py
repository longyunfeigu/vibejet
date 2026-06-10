# input: anthropic SDK（optional extra: anthropic）, LLMPort 接口
# output: AnthropicProvider LLM 实现
# owner: wanhua.gu
# pos: 基础设施层 - Anthropic 原生 SDK LLM 提供者实现（system 消息抽取、usage 映射）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Anthropic SDK implementation of LLMPort.

API shape differences vs OpenAI handled here so the application layer
stays provider-agnostic:
- system prompts are a separate ``system`` parameter, not a message role
- ``max_tokens`` is mandatory on every request
- usage arrives as input_tokens/output_tokens (split across stream events)
"""

from __future__ import annotations

from typing import AsyncIterator, Optional

from anthropic import AsyncAnthropic

from application.ports.llm import LLMChunk, LLMMessage, LLMResponse
from core.logging_config import get_logger

logger = get_logger(__name__)


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
                system_parts.append(m.content)
            else:
                chat.append({"role": m.role, "content": m.content})
        return ("\n\n".join(system_parts) or None), chat

    def _request_kwargs(
        self,
        messages: list[LLMMessage],
        *,
        model: Optional[str],
        temperature: Optional[float],
        max_tokens: Optional[int],
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
        return kwargs

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        response = await self._client.messages.create(
            **self._request_kwargs(
                messages, model=model, temperature=temperature, max_tokens=max_tokens
            )
        )
        content = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )
        prompt_tokens = response.usage.input_tokens if response.usage else 0
        completion_tokens = response.usage.output_tokens if response.usage else 0
        return LLMResponse(
            content=content,
            model=response.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            finish_reason=response.stop_reason,
        )

    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[LLMChunk]:
        kwargs = self._request_kwargs(
            messages, model=model, temperature=temperature, max_tokens=max_tokens
        )
        resolved_model = kwargs["model"]
        prompt_tokens = 0
        completion_tokens = 0

        async with self._client.messages.stream(**kwargs) as stream:
            async for event in stream:
                if event.type == "message_start":
                    usage = event.message.usage
                    prompt_tokens = getattr(usage, "input_tokens", 0) or 0
                elif event.type == "content_block_delta":
                    delta = event.delta
                    if getattr(delta, "type", "") == "text_delta" and delta.text:
                        yield LLMChunk(content=delta.text, model=resolved_model)
                elif event.type == "message_delta":
                    usage = getattr(event, "usage", None)
                    if usage is not None:
                        completion_tokens = getattr(usage, "output_tokens", 0) or 0

        # 收尾 chunk：与 OpenAIProvider 的 usage-only final chunk 语义对齐
        yield LLMChunk(
            content="",
            model=resolved_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )
