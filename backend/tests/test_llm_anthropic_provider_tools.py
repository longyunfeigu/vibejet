# input: AnthropicProvider + 假 Anthropic SDK client（捕获请求 kwargs / 回放事件桩）
# output: Anthropic provider 的 tool use / json_schema / 流式 tool call 映射测试
# pos: 后端测试 - LLMPort tool use 扩展在 Anthropic 适配器上的映射验证；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""AnthropicProvider mapping tests for the extended LLMPort contract.

anthropic SDK 是 optional extra，未安装时整个文件跳过（与 CI 基础矩阵兼容）。

验收标准（Given-When-Then）：
- 纯文本消息的 system 抽取与请求 kwargs 与扩展前一致（向后兼容）
- tools 原样映射；tool_choice: auto/{type:auto}、required/{type:any}、none/{type:none}、具体名/{type:tool}
- 内容块消息映射为 Anthropic 原生 content 数组；is_error 仅在 True 时输出
- generate 解析 tool_use 块为 tool_calls（arguments 为 dict）
- json_schema 走强制 tool call：请求带隐藏 tool + 强制 tool_choice，响应内容为 JSON 文本；与 tools 同传 → ValueError
- 流式：文本按增量输出；完整 tool_calls + usage + finish_reason 在最终 chunk 交付
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

pytest.importorskip("anthropic")

from application.ports.llm import (  # noqa: E402
    LLMMessage,
    TextBlock,
    ToolDefinition,
    ToolResultBlock,
    ToolUseBlock,
)
from infrastructure.external.llm.anthropic_provider import AnthropicProvider  # noqa: E402

WEATHER_TOOL = ToolDefinition(
    name="get_weather",
    description="Get current weather",
    input_schema={"type": "object", "properties": {"city": {"type": "string"}}},
)


def _text_response(content: str = "hi") -> SimpleNamespace:
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=content)],
        usage=SimpleNamespace(input_tokens=10, output_tokens=5),
        model="claude-sonnet-4-6",
        stop_reason="end_turn",
    )


def _tool_use_response() -> SimpleNamespace:
    return SimpleNamespace(
        content=[
            SimpleNamespace(type="text", text="I'll check."),
            SimpleNamespace(
                type="tool_use", id="toolu_1", name="get_weather", input={"city": "sf"}
            ),
        ],
        usage=SimpleNamespace(input_tokens=10, output_tokens=5),
        model="claude-sonnet-4-6",
        stop_reason="tool_use",
    )


class _FakeMessages:
    """捕获 create/stream 的 kwargs；stream 回放事件序列。"""

    def __init__(self, response=None, stream_events=None):
        self._response = response
        self._stream_events = stream_events or []
        self.kwargs: dict | None = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return self._response

    def stream(self, **kwargs):
        self.kwargs = kwargs
        return _FakeStreamContext(self._stream_events)


class _FakeStreamContext:
    def __init__(self, events):
        self._events = events

    async def __aenter__(self):
        return self._aiter()

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def _aiter(self):
        for event in self._events:
            yield event


def _provider(response=None, stream_events=None) -> tuple[AnthropicProvider, _FakeMessages]:
    provider = AnthropicProvider(api_key="test-key")
    fake = _FakeMessages(response=response, stream_events=stream_events)
    provider._client = SimpleNamespace(messages=fake)
    return provider, fake


async def test_str_content_request_kwargs_unchanged() -> None:
    provider, fake = _provider(response=_text_response())

    await provider.generate(
        [
            LLMMessage(role="system", content="be brief"),
            LLMMessage(role="user", content="hi"),
        ]
    )

    assert fake.kwargs is not None
    assert fake.kwargs["system"] == "be brief"
    assert fake.kwargs["messages"] == [{"role": "user", "content": "hi"}]
    for key in ("tools", "tool_choice"):
        assert key not in fake.kwargs


async def test_tools_and_tool_choice_mapping() -> None:
    provider, fake = _provider(response=_text_response())

    await provider.generate(
        [LLMMessage(role="user", content="hi")],
        tools=[WEATHER_TOOL],
        tool_choice="get_weather",
    )

    assert fake.kwargs["tools"] == [
        {
            "name": "get_weather",
            "description": "Get current weather",
            "input_schema": WEATHER_TOOL.input_schema,
        }
    ]
    assert fake.kwargs["tool_choice"] == {"type": "tool", "name": "get_weather"}


@pytest.mark.parametrize(
    ("choice", "expected"),
    [
        ("auto", {"type": "auto"}),
        ("required", {"type": "any"}),
        ("none", {"type": "none"}),
    ],
)
async def test_tool_choice_keyword_mapping(choice: str, expected: dict) -> None:
    provider, fake = _provider(response=_text_response())

    await provider.generate(
        [LLMMessage(role="user", content="hi")], tools=[WEATHER_TOOL], tool_choice=choice
    )

    assert fake.kwargs["tool_choice"] == expected


async def test_block_messages_mapping() -> None:
    provider, fake = _provider(response=_text_response())
    messages = [
        LLMMessage(
            role="assistant",
            content=[
                TextBlock(text="checking..."),
                ToolUseBlock(id="toolu_1", name="get_weather", arguments={"city": "sf"}),
            ],
        ),
        LLMMessage(
            role="user",
            content=[
                ToolResultBlock(tool_use_id="toolu_1", content="sunny"),
                ToolResultBlock(tool_use_id="toolu_2", content="boom", is_error=True),
            ],
        ),
    ]

    await provider.generate(messages)

    assert fake.kwargs["messages"] == [
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "checking..."},
                {
                    "type": "tool_use",
                    "id": "toolu_1",
                    "name": "get_weather",
                    "input": {"city": "sf"},
                },
            ],
        },
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "toolu_1", "content": "sunny"},
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_2",
                    "content": "boom",
                    "is_error": True,
                },
            ],
        },
    ]


async def test_generate_parses_tool_use_blocks() -> None:
    provider, _ = _provider(response=_tool_use_response())

    response = await provider.generate(
        [LLMMessage(role="user", content="weather in sf?")], tools=[WEATHER_TOOL]
    )

    assert response.content == "I'll check."
    assert response.finish_reason == "tool_use"
    assert len(response.tool_calls) == 1
    call = response.tool_calls[0]
    assert (call.id, call.name, call.arguments) == ("toolu_1", "get_weather", {"city": "sf"})


async def test_generate_json_schema_uses_forced_tool_call() -> None:
    schema = {"type": "object", "properties": {"city": {"type": "string"}}}
    forced_response = SimpleNamespace(
        content=[
            SimpleNamespace(
                type="tool_use", id="toolu_1", name="structured_output", input={"city": "sf"}
            )
        ],
        usage=SimpleNamespace(input_tokens=10, output_tokens=5),
        model="claude-sonnet-4-6",
        stop_reason="tool_use",
    )
    provider, fake = _provider(response=forced_response)

    response = await provider.generate(
        [LLMMessage(role="user", content="hi")], json_schema=schema
    )

    assert fake.kwargs["tools"][0]["name"] == "structured_output"
    assert fake.kwargs["tools"][0]["input_schema"] == schema
    assert fake.kwargs["tool_choice"] == {"type": "tool", "name": "structured_output"}
    # 强制 tool call 是实现细节：调用方拿到的是 JSON 文本，而不是 tool_calls；
    # finish_reason 统一为 "stop"，与 OpenAI 结构化输出路径一致
    assert json.loads(response.content) == {"city": "sf"}
    assert response.tool_calls == []
    assert response.finish_reason == "stop"


async def test_generate_json_schema_raises_when_forced_tool_missing() -> None:
    # refusal / max_tokens 截断时强制 tool call 可能缺失，必须报错而不是返回散文
    truncated_response = SimpleNamespace(
        content=[SimpleNamespace(type="text", text="I cannot")],
        usage=SimpleNamespace(input_tokens=10, output_tokens=5),
        model="claude-sonnet-4-6",
        stop_reason="max_tokens",
    )
    provider, _ = _provider(response=truncated_response)

    with pytest.raises(ValueError, match="structured output"):
        await provider.generate(
            [LLMMessage(role="user", content="hi")], json_schema={"type": "object"}
        )


async def test_system_message_with_text_blocks_is_extracted() -> None:
    provider, fake = _provider(response=_text_response())

    await provider.generate(
        [
            LLMMessage(role="system", content=[TextBlock(text="be brief")]),
            LLMMessage(role="user", content="hi"),
        ]
    )

    assert fake.kwargs["system"] == "be brief"


async def test_generate_rejects_tools_with_json_schema() -> None:
    provider, _ = _provider(response=_text_response())

    with pytest.raises(ValueError):
        await provider.generate(
            [LLMMessage(role="user", content="hi")],
            tools=[WEATHER_TOOL],
            json_schema={"type": "object"},
        )


def _stream_events_with_tool_call() -> list[SimpleNamespace]:
    return [
        SimpleNamespace(
            type="message_start",
            message=SimpleNamespace(usage=SimpleNamespace(input_tokens=10)),
        ),
        SimpleNamespace(
            type="content_block_start", index=0, content_block=SimpleNamespace(type="text")
        ),
        SimpleNamespace(
            type="content_block_delta",
            index=0,
            delta=SimpleNamespace(type="text_delta", text="Let me check."),
        ),
        SimpleNamespace(type="content_block_stop", index=0),
        SimpleNamespace(
            type="content_block_start",
            index=1,
            content_block=SimpleNamespace(type="tool_use", id="toolu_1", name="get_weather"),
        ),
        SimpleNamespace(
            type="content_block_delta",
            index=1,
            delta=SimpleNamespace(type="input_json_delta", partial_json='{"ci'),
        ),
        SimpleNamespace(
            type="content_block_delta",
            index=1,
            delta=SimpleNamespace(type="input_json_delta", partial_json='ty": "sf"}'),
        ),
        SimpleNamespace(type="content_block_stop", index=1),
        SimpleNamespace(
            type="message_delta",
            delta=SimpleNamespace(stop_reason="tool_use"),
            usage=SimpleNamespace(output_tokens=5),
        ),
    ]


async def test_stream_delivers_complete_tool_calls_on_final_chunk() -> None:
    provider, _ = _provider(stream_events=_stream_events_with_tool_call())

    chunks = [
        chunk
        async for chunk in provider.stream(
            [LLMMessage(role="user", content="weather in sf?")], tools=[WEATHER_TOOL]
        )
    ]

    assert [c.content for c in chunks if c.content] == ["Let me check."]
    assert all(not c.tool_calls for c in chunks[:-1])

    final = chunks[-1]
    assert final.finish_reason == "tool_use"
    assert final.prompt_tokens == 10
    assert final.completion_tokens == 5
    assert final.total_tokens == 15
    assert len(final.tool_calls) == 1
    call = final.tool_calls[0]
    assert (call.id, call.name, call.arguments) == ("toolu_1", "get_weather", {"city": "sf"})


async def test_stream_text_only_final_chunk_carries_finish_reason() -> None:
    events = [
        SimpleNamespace(
            type="message_start",
            message=SimpleNamespace(usage=SimpleNamespace(input_tokens=3)),
        ),
        SimpleNamespace(
            type="content_block_delta",
            index=0,
            delta=SimpleNamespace(type="text_delta", text="Hello"),
        ),
        SimpleNamespace(
            type="message_delta",
            delta=SimpleNamespace(stop_reason="end_turn"),
            usage=SimpleNamespace(output_tokens=2),
        ),
    ]
    provider, _ = _provider(stream_events=events)

    chunks = [
        chunk async for chunk in provider.stream([LLMMessage(role="user", content="hi")])
    ]

    assert [c.content for c in chunks if c.content] == ["Hello"]
    final = chunks[-1]
    assert final.finish_reason == "end_turn"
    assert final.total_tokens == 5
    assert final.tool_calls == []
