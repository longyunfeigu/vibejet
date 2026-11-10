"""LLM 调用熔断：provider 外套同一个熔断器，按 SDK 异常区分上游故障。

验收标准（Given-When-Then）：
- 上游持续 5xx / 超时 → 熔断打开后 generate 在本地抛 CircuitBreakerOpenError，不再调用 provider
- 4xx（参数错误、429 限流）说明上游健康，不触发熔断；我方代码的参数校验异常不算上游故障
- stream：中途失败计入故障；正常结束计成功；调用方提前停止消费不记账，且内层流被关闭
- 真实 SDK 流式路径：上游先回 200 再断流 / 读超时 / 下发 error 事件，都计入故障
- 真实 SDK 非流式路径：200 + 无效响应体（HTML / 只含 error 的 JSON / 空 body）计入故障
- _build_client 给 provider 套上熔断；shutdown 仍能关闭内层 SDK client
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import httpx
import openai
import pytest

from application.ports.llm import LLMChunk, LLMMessage, LLMResponse, ToolDefinition
from infrastructure.external import llm as llm_module
from infrastructure.external.circuit_breaker import CircuitBreakerOpenError, SREBreaker
from infrastructure.external.llm._shared import UpstreamResponseError
from infrastructure.external.llm.circuit_breaking import CircuitBreakingLLM
from infrastructure.external.llm.openai_provider import OpenAIProvider, is_upstream_failure

_REQUEST = httpx.Request("POST", "https://llm.test/v1/chat/completions")
_MESSAGES = [LLMMessage(role="user", content="hi")]


def _status_error(cls: type[openai.APIStatusError], status: int) -> openai.APIStatusError:
    return cls("boom", response=httpx.Response(status, request=_REQUEST), body=None)


class _FakeProvider:
    def __init__(self, error: BaseException | None = None, chunks: int = 2) -> None:
        self.error = error
        self.chunks = chunks
        self.calls = 0
        self.stream_closed = False

    async def generate(self, messages, **kwargs) -> LLMResponse:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return LLMResponse(content="ok", model="m")

    async def stream(self, messages, **kwargs):
        self.calls += 1
        try:
            for i in range(self.chunks):
                yield LLMChunk(content=str(i), model="m")
            if self.error is not None:
                raise self.error
        finally:
            self.stream_closed = True


def _wrapped(provider: _FakeProvider) -> tuple[CircuitBreakingLLM, SREBreaker]:
    breaker = SREBreaker("llm:test", random=lambda: 0.0)
    return CircuitBreakingLLM(provider, breaker, is_upstream_failure), breaker


@pytest.mark.parametrize(
    "error",
    [
        _status_error(openai.InternalServerError, 500),
        openai.APITimeoutError(request=_REQUEST),
        openai.APIConnectionError(request=_REQUEST),
    ],
)
@pytest.mark.asyncio
async def test_upstream_failures_open_the_breaker(error: BaseException) -> None:
    provider = _FakeProvider(error=error)
    llm, _ = _wrapped(provider)

    for _ in range(20):
        with pytest.raises(type(error)):
            await llm.generate(_MESSAGES)
    with pytest.raises(CircuitBreakerOpenError):
        await llm.generate(_MESSAGES)

    assert provider.calls == 20, "熔断后不应再调用 provider"


@pytest.mark.parametrize(
    "error",
    [
        _status_error(openai.BadRequestError, 400),
        _status_error(openai.RateLimitError, 429),
    ],
)
@pytest.mark.asyncio
async def test_client_side_errors_do_not_open_the_breaker(error: BaseException) -> None:
    provider = _FakeProvider(error=error)
    llm, _ = _wrapped(provider)

    for _ in range(30):
        with pytest.raises(type(error)):
            await llm.generate(_MESSAGES)

    assert provider.calls == 30


@pytest.mark.asyncio
async def test_own_validation_errors_are_not_upstream_failures() -> None:
    provider = OpenAIProvider(api_key="sk-test", default_model="m", max_retries=0)
    breaker = SREBreaker("llm:test", random=lambda: 0.0)
    llm = CircuitBreakingLLM(provider, breaker, is_upstream_failure)
    tool = ToolDefinition(name="t", description="d", input_schema={"type": "object"})

    with pytest.raises(ValueError):
        await llm.generate(_MESSAGES, tools=[tool], json_schema={"type": "object"})

    assert breaker._stat.summary() == (1, 1)


@pytest.mark.asyncio
async def test_stream_records_outcomes() -> None:
    failing, failing_breaker = _wrapped(
        _FakeProvider(error=_status_error(openai.InternalServerError, 500))
    )
    with pytest.raises(openai.InternalServerError):
        async for _ in failing.stream(_MESSAGES):
            pass
    assert failing_breaker._stat.summary() == (0, 1)

    healthy, healthy_breaker = _wrapped(_FakeProvider())
    chunks = [chunk.content async for chunk in healthy.stream(_MESSAGES)]
    assert chunks == ["0", "1"]
    assert healthy_breaker._stat.summary() == (1, 1)


@pytest.mark.asyncio
async def test_stream_abandoned_by_consumer_is_not_recorded_and_closes_inner() -> None:
    provider = _FakeProvider(chunks=5)
    llm, breaker = _wrapped(provider)

    stream = llm.stream(_MESSAGES)
    await stream.__anext__()
    await stream.aclose()

    assert breaker._stat.summary() == (0, 0)
    assert provider.stream_closed


class _BrokenSSE(httpx.AsyncByteStream):
    """200 响应、先下发一段正常内容，再按 mode 出错（上游中途故障）。"""

    def __init__(self, first: bytes, mode: str, error_event: bytes) -> None:
        self._first = first
        self._mode = mode
        self._error_event = error_event

    async def __aiter__(self):
        yield self._first
        if self._mode == "drop":
            raise httpx.RemoteProtocolError("peer closed connection without complete body")
        if self._mode == "read_timeout":
            raise httpx.ReadTimeout("read timed out")
        yield self._error_event


async def _stream_against(llm: CircuitBreakingLLM) -> BaseException:
    with pytest.raises(Exception) as exc_info:
        async for _ in llm.stream(_MESSAGES):
            pass
    return exc_info.value


def _sse_transport(stream: httpx.AsyncByteStream) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, headers={"content-type": "text/event-stream"}, stream=stream
            )
        )
    )


@pytest.mark.parametrize("mode", ["drop", "read_timeout", "error_event"])
@pytest.mark.asyncio
async def test_openai_midstream_failures_count_as_upstream_failures(mode: str) -> None:
    delta = {
        "id": "c",
        "object": "chat.completion.chunk",
        "created": 1,
        "model": "m",
        "choices": [{"index": 0, "delta": {"content": "hi"}, "finish_reason": None}],
    }
    error = {"error": {"message": "upstream overloaded", "code": 503}}
    stream = _BrokenSSE(
        f"data: {json.dumps(delta)}\n\n".encode(),
        mode,
        f"data: {json.dumps(error)}\n\ndata: [DONE]\n\n".encode(),
    )
    provider = OpenAIProvider(api_key="sk-test", default_model="m", max_retries=0)
    provider._client = openai.AsyncOpenAI(
        api_key="sk-test",
        base_url="https://llm.test/v1",
        max_retries=0,
        http_client=_sse_transport(stream),
    )
    breaker = SREBreaker("llm:test", random=lambda: 0.0)

    await _stream_against(CircuitBreakingLLM(provider, breaker, is_upstream_failure))

    assert breaker._stat.summary() == (0, 1)


@pytest.mark.parametrize("mode", ["drop", "read_timeout", "overloaded_event"])
@pytest.mark.asyncio
async def test_anthropic_midstream_failures_count_as_upstream_failures(mode: str) -> None:
    anthropic = pytest.importorskip("anthropic")
    from infrastructure.external.llm.anthropic_provider import AnthropicProvider
    from infrastructure.external.llm.anthropic_provider import (
        is_upstream_failure as is_anthropic_failure,
    )

    def _event(name: str, data: dict) -> bytes:
        return f"event: {name}\ndata: {json.dumps(data)}\n\n".encode()

    start = _event(
        "message_start",
        {
            "type": "message_start",
            "message": {
                "id": "m1",
                "type": "message",
                "role": "assistant",
                "content": [],
                "model": "c",
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {"input_tokens": 3, "output_tokens": 0},
            },
        },
    )
    # Anthropic 文档：200 之后仍可能下发 error 事件（overloaded_error），SDK 抛 status_code=200
    overloaded = _event(
        "error", {"type": "error", "error": {"type": "overloaded_error", "message": "Overloaded"}}
    )
    provider = AnthropicProvider(api_key="sk-test", default_model="c", max_retries=0)
    provider._client = anthropic.AsyncAnthropic(
        api_key="sk-test",
        base_url="https://llm.test",
        max_retries=0,
        http_client=_sse_transport(_BrokenSSE(start, mode, overloaded)),
    )
    breaker = SREBreaker("llm:test", random=lambda: 0.0)

    await _stream_against(CircuitBreakingLLM(provider, breaker, is_anthropic_failure))

    assert breaker._stat.summary() == (0, 1)


# OpenRouter 文档：非流式请求在响应头发出后失败时返回 200 + 只含 error 的 JSON（无 choices）
_INVALID_2XX_BODIES = {
    "html": lambda request: httpx.Response(
        200, text="<html>Bad Gateway</html>", headers={"content-type": "text/html"}
    ),
    "error_json": lambda request: httpx.Response(
        200, json={"error": {"message": "Provider returned error", "code": 502}}
    ),
    "empty": lambda request: httpx.Response(
        200, content=b"", headers={"content-type": "application/json"}
    ),
}


@pytest.mark.parametrize("body", sorted(_INVALID_2XX_BODIES))
@pytest.mark.asyncio
async def test_generate_invalid_2xx_body_counts_as_upstream_failure(body: str) -> None:
    provider = OpenAIProvider(api_key="sk-test", default_model="m", max_retries=0)
    provider._client = openai.AsyncOpenAI(
        api_key="sk-test",
        base_url="https://llm.test/v1",
        max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(_INVALID_2XX_BODIES[body])),
    )
    breaker = SREBreaker("llm:test", random=lambda: 0.0)
    llm = CircuitBreakingLLM(provider, breaker, is_upstream_failure)

    with pytest.raises((UpstreamResponseError, json.JSONDecodeError)):
        await llm.generate(_MESSAGES)

    assert breaker._stat.summary() == (0, 1)


@pytest.mark.parametrize("body", sorted(_INVALID_2XX_BODIES))
@pytest.mark.asyncio
async def test_anthropic_generate_invalid_2xx_body_counts_as_upstream_failure(body: str) -> None:
    anthropic = pytest.importorskip("anthropic")
    from infrastructure.external.llm.anthropic_provider import AnthropicProvider
    from infrastructure.external.llm.anthropic_provider import (
        is_upstream_failure as is_anthropic_failure,
    )

    provider = AnthropicProvider(api_key="sk-test", default_model="c", max_retries=0)
    provider._client = anthropic.AsyncAnthropic(
        api_key="sk-test",
        base_url="https://llm.test",
        max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(_INVALID_2XX_BODIES[body])),
    )
    breaker = SREBreaker("llm:test", random=lambda: 0.0)
    llm = CircuitBreakingLLM(provider, breaker, is_anthropic_failure)

    with pytest.raises((UpstreamResponseError, json.JSONDecodeError)):
        await llm.generate(_MESSAGES)

    assert breaker._stat.summary() == (0, 1)


def _llm_cfg() -> SimpleNamespace:
    return SimpleNamespace(
        provider="openai",
        api_key="sk-test",
        base_url=None,
        default_model="gpt-4o-mini",
        temperature=0.7,
        max_tokens=16,
        timeout=5,
        max_retries=0,
    )


def test_build_client_wraps_provider_with_breaker() -> None:
    client = llm_module._build_client(_llm_cfg())

    assert isinstance(client, CircuitBreakingLLM)
    assert isinstance(client.inner, OpenAIProvider)


@pytest.mark.asyncio
async def test_shutdown_closes_inner_sdk_client(monkeypatch: pytest.MonkeyPatch) -> None:
    closed: list[bool] = []

    class _SDKClient:
        async def close(self) -> None:
            closed.append(True)

    provider = _FakeProvider()
    provider._client = _SDKClient()
    monkeypatch.setattr(llm_module, "_llm_client", _wrapped(provider)[0])

    await llm_module.shutdown_llm_client()

    assert closed == [True]
    assert llm_module.get_llm_client() is None
