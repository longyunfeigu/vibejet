# input: OpenAIProvider + 假 OpenAI SDK client（捕获请求 kwargs / 回放响应桩）
# output: OpenAI provider 的 tool use / json_schema / 流式 tool call 映射测试
# pos: 后端测试 - LLMPort tool use 扩展在 OpenAI 适配器上的映射验证；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""OpenAIProvider mapping tests for the extended LLMPort contract.

验收标准（Given-When-Then）：
- 纯文本消息的请求 kwargs 与扩展前完全一致（向后兼容，不多出 tools 等键）
- tools/tool_choice 正确映射为 OpenAI function 格式
- 内容块消息映射：assistant ToolUseBlock → tool_calls；user ToolResultBlock → role="tool" 消息
- generate 解析 tool_calls（arguments 为 dict），finish_reason "tool_calls" 归一化为 "tool_use"
- json_schema → response_format；与 tools 同时传 → ValueError
- 流式：文本按增量输出；完整 tool_calls + usage + finish_reason 在最终 chunk 交付
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from application.ports.llm import (
    LLMMessage,
    TextBlock,
    ToolDefinition,
    ToolResultBlock,
    ToolUseBlock,
)
from infrastructure.external.llm.openai_provider import OpenAIProvider

WEATHER_TOOL = ToolDefinition(
    name="get_weather",
    description="Get current weather",
    input_schema={"type": "object", "properties": {"city": {"type": "string"}}},
)


def _text_response(content: str = "hi") -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content, tool_calls=None),
                finish_reason="stop",
            )
        ],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        model="gpt-4o-mini",
    )


def _tool_call_response() -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=None,
                    tool_calls=[
                        SimpleNamespace(
                            id="call_1",
                            type="function",
                            function=SimpleNamespace(
                                name="get_weather", arguments='{"city": "sf"}'
                            ),
                        )
                    ],
                ),
                finish_reason="tool_calls",
            )
        ],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        model="gpt-4o-mini",
    )


class _FakeCompletions:
    """捕获 create(**kwargs)，非流式回放 response，流式回放 chunk 序列。"""

    def __init__(self, response=None, stream_chunks=None):
        self._response = response
        self._stream_chunks = stream_chunks or []
        self.kwargs: dict | None = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        if kwargs.get("stream"):
            return self._aiter()
        return self._response

    async def _aiter(self):
        for chunk in self._stream_chunks:
            yield chunk


def _provider(response=None, stream_chunks=None) -> tuple[OpenAIProvider, _FakeCompletions]:
    provider = OpenAIProvider(api_key="test-key")
    fake = _FakeCompletions(response=response, stream_chunks=stream_chunks)
    provider._client = SimpleNamespace(chat=SimpleNamespace(completions=fake))
    return provider, fake


async def test_str_content_request_kwargs_unchanged() -> None:
    provider, fake = _provider(response=_text_response())

    await provider.generate([LLMMessage(role="user", content="hi")])

    assert fake.kwargs is not None
    assert fake.kwargs["messages"] == [{"role": "user", "content": "hi"}]
    for key in ("tools", "tool_choice", "response_format"):
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
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get current weather",
                "parameters": WEATHER_TOOL.input_schema,
            },
        }
    ]
    assert fake.kwargs["tool_choice"] == {
        "type": "function",
        "function": {"name": "get_weather"},
    }


@pytest.mark.parametrize("choice", ["auto", "required", "none"])
async def test_tool_choice_keywords_pass_through(choice: str) -> None:
    provider, fake = _provider(response=_text_response())

    await provider.generate(
        [LLMMessage(role="user", content="hi")],
        tools=[WEATHER_TOOL],
        tool_choice=choice,
    )

    assert fake.kwargs["tool_choice"] == choice


async def test_block_messages_mapping() -> None:
    provider, fake = _provider(response=_text_response())
    messages = [
        LLMMessage(
            role="assistant",
            content=[
                TextBlock(text="checking..."),
                ToolUseBlock(id="call_1", name="get_weather", arguments={"city": "sf"}),
            ],
        ),
        LLMMessage(
            role="user",
            content=[
                ToolResultBlock(tool_use_id="call_1", content="sunny"),
                ToolResultBlock(tool_use_id="call_2", content="boom", is_error=True),
                TextBlock(text="thanks"),
            ],
        ),
    ]

    await provider.generate(messages)

    assert fake.kwargs["messages"] == [
        {
            "role": "assistant",
            "content": "checking...",
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": json.dumps({"city": "sf"}, ensure_ascii=False),
                    },
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call_1", "content": "sunny"},
        # OpenAI 无原生 is_error 标记，用内容前缀传递错误信号
        {"role": "tool", "tool_call_id": "call_2", "content": "[tool error] boom"},
        {"role": "user", "content": "thanks"},
    ]


async def test_assistant_tool_call_only_message_has_null_content() -> None:
    provider, fake = _provider(response=_text_response())
    messages = [
        LLMMessage(
            role="assistant",
            content=[ToolUseBlock(id="call_1", name="get_weather", arguments={})],
        ),
    ]

    await provider.generate(messages)

    assert fake.kwargs["messages"][0]["content"] is None


async def test_generate_parses_tool_calls_and_normalizes_finish_reason() -> None:
    provider, _ = _provider(response=_tool_call_response())

    response = await provider.generate(
        [LLMMessage(role="user", content="weather in sf?")], tools=[WEATHER_TOOL]
    )

    assert response.content == ""
    assert response.finish_reason == "tool_use"
    assert len(response.tool_calls) == 1
    call = response.tool_calls[0]
    assert (call.id, call.name, call.arguments) == ("call_1", "get_weather", {"city": "sf"})


async def test_generate_json_schema_sets_response_format() -> None:
    provider, fake = _provider(response=_text_response('{"city": "sf"}'))
    schema = {"type": "object", "properties": {"city": {"type": "string"}}}

    response = await provider.generate(
        [LLMMessage(role="user", content="hi")], json_schema=schema
    )

    # strict 模式会拒绝未全量标注 additionalProperties/required 的普通 schema
    assert fake.kwargs["response_format"] == {
        "type": "json_schema",
        "json_schema": {"name": "structured_output", "schema": schema, "strict": False},
    }
    assert json.loads(response.content) == {"city": "sf"}


async def test_generate_rejects_tools_with_json_schema() -> None:
    provider, _ = _provider(response=_text_response())

    with pytest.raises(ValueError):
        await provider.generate(
            [LLMMessage(role="user", content="hi")],
            tools=[WEATHER_TOOL],
            json_schema={"type": "object"},
        )


def _stream_chunks_with_tool_call() -> list[SimpleNamespace]:
    def _delta_chunk(content=None, tool_calls=None, finish_reason=None):
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    delta=SimpleNamespace(content=content, tool_calls=tool_calls),
                    finish_reason=finish_reason,
                )
            ],
            usage=None,
            model="gpt-4o-mini",
        )

    return [
        _delta_chunk(content="Let me check."),
        _delta_chunk(
            tool_calls=[
                SimpleNamespace(
                    index=0,
                    id="call_1",
                    function=SimpleNamespace(name="get_weather", arguments='{"ci'),
                )
            ]
        ),
        _delta_chunk(
            tool_calls=[
                SimpleNamespace(
                    index=0,
                    id=None,
                    function=SimpleNamespace(name=None, arguments='ty": "sf"}'),
                )
            ]
        ),
        _delta_chunk(finish_reason="tool_calls"),
        SimpleNamespace(
            choices=[],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            model="gpt-4o-mini",
        ),
    ]


async def test_stream_delivers_complete_tool_calls_on_final_chunk() -> None:
    provider, _ = _provider(stream_chunks=_stream_chunks_with_tool_call())

    chunks = [
        chunk
        async for chunk in provider.stream(
            [LLMMessage(role="user", content="weather in sf?")], tools=[WEATHER_TOOL]
        )
    ]

    text_chunks = [c for c in chunks if c.content]
    assert [c.content for c in text_chunks] == ["Let me check."]
    # 中间 chunk 不携带 tool_calls
    assert all(not c.tool_calls for c in chunks[:-1])

    final = chunks[-1]
    assert final.finish_reason == "tool_use"
    assert final.total_tokens == 15
    assert len(final.tool_calls) == 1
    call = final.tool_calls[0]
    assert (call.id, call.name, call.arguments) == ("call_1", "get_weather", {"city": "sf"})


async def test_stream_text_only_final_chunk_has_usage_no_tool_calls() -> None:
    chunks_in = [
        SimpleNamespace(
            choices=[
                SimpleNamespace(
                    delta=SimpleNamespace(content="Hello", tool_calls=None),
                    finish_reason=None,
                )
            ],
            usage=None,
            model="gpt-4o-mini",
        ),
        SimpleNamespace(
            choices=[
                SimpleNamespace(
                    delta=SimpleNamespace(content=None, tool_calls=None),
                    finish_reason="stop",
                )
            ],
            usage=None,
            model="gpt-4o-mini",
        ),
        SimpleNamespace(
            choices=[],
            usage=SimpleNamespace(prompt_tokens=3, completion_tokens=2, total_tokens=5),
            model="gpt-4o-mini",
        ),
    ]
    provider, _ = _provider(stream_chunks=chunks_in)

    chunks = [
        chunk async for chunk in provider.stream([LLMMessage(role="user", content="hi")])
    ]

    assert [c.content for c in chunks if c.content] == ["Hello"]
    final = chunks[-1]
    assert final.finish_reason == "stop"
    assert final.total_tokens == 5
    assert final.tool_calls == []
