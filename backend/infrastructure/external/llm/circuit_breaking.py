"""LLMPort decorator that puts one circuit breaker in front of any provider.

LLM provider 挂掉时，每次调用都要等满 SDK 的超时与重试（默认 60s × 3 次）才失败，
请求、连接和 running 状态的 Run 一起堆积。熔断打开后在本地立刻失败：
generate 由 ChatApplicationService 转成 LLMProviderException（502），
stream 转成 SSE error 事件——与上游真实失败走同一条错误路径。
"""

from __future__ import annotations

from typing import Any, AsyncIterator, Callable

from application.ports.llm import LLMChunk, LLMMessage, LLMPort, LLMResponse
from infrastructure.external.circuit_breaker import SREBreaker


class CircuitBreakingLLM:
    """Wrap an LLMPort; ``is_failure`` classifies the provider SDK's exceptions."""

    def __init__(
        self,
        inner: LLMPort,
        breaker: SREBreaker,
        is_failure: Callable[[BaseException], bool],
    ) -> None:
        self._inner = inner
        self._breaker = breaker
        self._is_failure = is_failure

    @property
    def inner(self) -> LLMPort:
        return self._inner

    async def generate(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        with self._breaker.guard(self._is_failure):
            return await self._inner.generate(messages, **kwargs)

    async def stream(self, messages: list[LLMMessage], **kwargs: Any) -> AsyncIterator[LLMChunk]:
        # 熔断记账覆盖整条流：中途断流同样是上游故障（由 is_failure 判定）
        with self._breaker.guard(self._is_failure):
            chunks = self._inner.stream(messages, **kwargs)
            try:
                async for chunk in chunks:
                    yield chunk
            finally:
                # 调用方提前停止消费时立即关闭内层流、释放上游连接，而不是等 GC；
                # 端口只承诺 AsyncIterator，async generator 才有 aclose
                aclose = getattr(chunks, "aclose", None)
                if aclose is not None:
                    await aclose()
