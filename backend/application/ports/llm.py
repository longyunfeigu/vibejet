# input: LLM provider SDKs (OpenAI, Azure, vLLM, Anthropic)
# output: LLMPort Protocol, LLMMessage/ContentBlock, ToolDefinition/ToolCall, LLMResponse, LLMChunk
# owner: unknown
# pos: 应用层端口 - LLM 调用抽象接口（文本 + tool use + 结构化输出）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Application-owned LLM port abstraction (hexagonal architecture).

Defines the minimal protocol needed by application use cases so that
the application layer does not depend on specific LLM provider details.

Content model follows Anthropic-style content blocks (the more general
shape): an assistant message carries ToolUseBlock, and the tool results
go back inside a *user* message as ToolResultBlock. Providers whose wire
format differs (OpenAI: assistant.tool_calls + role="tool" messages)
adapt in their own implementation.

Streaming contract: text is streamed as content deltas; complete tool
calls are delivered on the final chunk (the one carrying usage and
finish_reason). Partial tool-argument streaming is deliberately not
modeled — a tool call is only executable once complete.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Literal, Optional, Protocol, Union, runtime_checkable


@dataclass
class TextBlock:
    """Plain text content."""

    text: str
    type: Literal["text"] = "text"


@dataclass
class ToolUseBlock:
    """Assistant's request to invoke a tool (appears in assistant messages)."""

    id: str
    name: str
    arguments: dict[str, Any]
    type: Literal["tool_use"] = "tool_use"


@dataclass
class ToolResultBlock:
    """Result of a tool invocation (appears in the following user message)."""

    tool_use_id: str
    content: str
    is_error: bool = False
    type: Literal["tool_result"] = "tool_result"


ContentBlock = Union[TextBlock, ToolUseBlock, ToolResultBlock]


@dataclass
class LLMMessage:
    """A single message in a conversation sent to the LLM.

    ``content`` is a plain string for text-only messages (the common case,
    kept for backward compatibility), or a list of content blocks when the
    message carries tool interactions.
    """

    role: str  # system | user | assistant
    content: str | list[ContentBlock]


@dataclass
class ToolDefinition:
    """A tool the model may call. ``input_schema`` is a JSON Schema object."""

    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class ToolCall:
    """A complete, parsed tool invocation requested by the model."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    """Non-streaming LLM response.

    ``finish_reason`` is provider-native except for one normalization:
    a response that stopped to call tools always reports ``"tool_use"``.
    """

    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    finish_reason: Optional[str] = None
    tool_calls: list[ToolCall] = field(default_factory=list)


@dataclass
class LLMChunk:
    """A single chunk from a streaming LLM response.

    Token usage, finish_reason and complete tool_calls are delivered on
    the final chunk only.
    """

    content: str = ""
    model: str = ""
    finish_reason: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    tool_calls: list[ToolCall] = field(default_factory=list)


@runtime_checkable
class LLMPort(Protocol):
    """Port for interacting with a Large Language Model.

    ``json_schema`` (generate only) requests a response conforming to the
    given JSON Schema (best-effort per provider — callers should validate the
    result); ``content`` then holds the JSON text and ``finish_reason`` is
    ``"stop"``. Mutually exclusive with ``tools`` — providers raise ValueError
    if both are set, and raise ValueError when the provider fails to produce
    the structured output (refusal / truncation).

    ``tool_choice``: "auto" | "required" | "none" | a specific tool name.
    The three keywords are reserved — a tool named exactly "auto"/"required"/
    "none" cannot be force-selected by name.
    """

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
    ) -> LLMResponse: ...

    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[list[ToolDefinition]] = None,
        tool_choice: Optional[str] = None,
    ) -> AsyncIterator[LLMChunk]: ...
