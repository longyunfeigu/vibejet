"""Client-side adaptive circuit breaker for outbound calls, ported from Kratos.

移植来源 go-kratos/kratos v3（commit dd0fb7d）：
- ``internal/circuitbreaker/sre.go``：算法与滚动窗口计数
- ``middleware/circuitbreaker/circuitbreaker.go``：调用侧语义（被拒也记失败；
  只有下游自身故障记失败，其余结果都说明下游健康、记成功）

算法是 Google SRE《Handling Overload》的客户端自适应节流，不是经典三态熔断：
没有"全开 + 冷却 + 半开试探"，而是按窗口内成功数在本地算拒绝概率
``max(0, (total - k * successes) / (total + 1))``，下游恢复后概率自然回落到 0；
只用本进程计数，多 worker 部署无需共享状态。PyPI 上的熔断库（purgatory /
pybreaker / circuitbreaker）都是经典三态，没有此算法的维护实现，故移植。

与 Kratos 的有意偏差：
- 默认窗口 120s（SRE 书的"最近两分钟"）而非 Kratos 的 3s：3s 是给高 QPS 内部 RPC 的，
  本仓库外呼（LLM、第三方 API）QPS 低、单次耗时长，3s 窗口内凑不满最小请求数，熔断永远不会触发。
  代价：下游恢复后，窗口里的旧失败要滚出去才完全放行，最长约 120s
- 一个下游服务一个熔断器（Kratos 按 operation）：endpoint 常带 ID，按它建熔断器会无限增长
- 时钟用 time.monotonic，避免系统校时让窗口跳变

失败口径（各调用方的 is_failure）：Kratos 对未识别的错误按 500 处理、记失败，只有明确的
4xx 记成功。这里同样"源自下游的错误默认算故障"（含 2xx 之后才出的错：流式中途断流、
200 + 无效响应体），只排除两类：明确的 4xx 响应（下游健康，是请求本身的问题），以及调用方
自己的 bug（本地协议错误、我方代码抛的普通异常）——按服务熔断时，一个出 bug 的调用点
不能拖垮这个下游的所有调用方。5xx 全部计入（Kratos 只计 500/503/504）。
"""

from __future__ import annotations

import random as _random
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

import httpx

from core.logging_config import get_logger

logger = get_logger(__name__)


class CircuitBreakerOpenError(Exception):
    """The breaker rejected the call locally; nothing was sent downstream."""

    # 对应 Kratos ErrNotAllowed：503 / reason CIRCUITBREAKER
    reason = "CIRCUITBREAKER"

    def __init__(self, name: str) -> None:
        super().__init__(f"circuit breaker '{name}' rejected the call: downstream is failing")
        self.name = name


def is_downstream_httpx_failure(exc: BaseException) -> bool:
    """httpx 请求错误中源自下游/网络的部分：连接、超时、对端断流、响应解码失败、重定向死循环。

    LocalProtocolError / UnsupportedProtocol 是请求在本地就构造不出来（非法 header、
    错误 scheme），是调用方的 bug，不算下游故障。
    """
    return isinstance(exc, httpx.RequestError) and not isinstance(
        exc, (httpx.LocalProtocolError, httpx.UnsupportedProtocol)
    )


@dataclass(slots=True)
class _Bucket:
    slot: int = 0
    success: int = 0
    total: int = 0


class _RollingCounter:
    def __init__(self, size: int, bucket_duration: float, clock: Callable[[], float]) -> None:
        self._buckets = [_Bucket() for _ in range(size)]
        self._bucket_duration = bucket_duration
        self._clock = clock
        self._lock = threading.Lock()

    def _current_slot(self) -> int:
        return int(self._clock() // self._bucket_duration)

    def add(self, success: int) -> None:
        slot = self._current_slot()
        with self._lock:
            bucket = self._buckets[slot % len(self._buckets)]
            if bucket.slot != slot:
                bucket.slot, bucket.success, bucket.total = slot, 0, 0
            bucket.success += success
            bucket.total += 1

    def summary(self) -> tuple[int, int]:
        slot = self._current_slot()
        size = len(self._buckets)
        success = total = 0
        with self._lock:
            for bucket in self._buckets:
                if bucket.total == 0 or slot - bucket.slot >= size or bucket.slot > slot:
                    continue
                success += bucket.success
                total += bucket.total
        return success, total


class SREBreaker:
    """Adaptive throttling breaker; one instance per downstream service."""

    def __init__(
        self,
        name: str,
        *,
        failure_ratio: float = 0.5,
        request: int = 20,
        window: float = 120.0,
        buckets: int = 10,
        clock: Callable[[], float] = time.monotonic,
        random: Callable[[], float] = _random.random,
    ) -> None:
        # 非法参数回落默认值（同 Kratos NewBreaker）
        if not 0 <= failure_ratio < 1:
            failure_ratio = 0.5
        self.name = name
        self._k = 1 / (1 - failure_ratio)
        self._request = max(request, 1)
        window = window if window > 0 else 120.0
        buckets = max(buckets, 1)
        self._stat = _RollingCounter(buckets, window / buckets, clock)
        self._random = random
        self._open = False

    def allow(self) -> bool:
        successes, total = self._stat.summary()
        requests = self._k * successes
        if total < self._request or total < requests:
            self._set_open(False)
            return True
        self._set_open(True)
        drop_ratio = max(0.0, (total - requests) / (total + 1))
        return self._random() >= drop_ratio

    def mark_success(self) -> None:
        self._stat.add(1)

    def mark_failed(self) -> None:
        self._stat.add(0)

    def guard(self, is_failure: Callable[[BaseException], bool]) -> "_Guard":
        """Wrap one call: reject via CircuitBreakerOpenError, then record its outcome.

        ``is_failure`` decides which exceptions mean the downstream itself failed
        (timeouts, connection errors, 5xx); every other exception counts as success.
        """
        return _Guard(self, is_failure)

    def _set_open(self, is_open: bool) -> None:
        # 只在状态翻转时打日志：熔断开合是运维要看到的信号，逐请求打会刷屏
        if is_open == self._open:
            return
        self._open = is_open
        if is_open:
            logger.warning("circuit_breaker_open", breaker=self.name)
        else:
            logger.info("circuit_breaker_closed", breaker=self.name)


class _Guard:
    __slots__ = ("_breaker", "_is_failure")

    def __init__(self, breaker: SREBreaker, is_failure: Callable[[BaseException], bool]) -> None:
        self._breaker = breaker
        self._is_failure = is_failure

    def __enter__(self) -> None:
        if not self._breaker.allow():
            # 被拒也记失败：持续施压让拒绝率维持，直到放行的请求重新成功（同 Kratos）
            self._breaker.mark_failed()
            raise CircuitBreakerOpenError(self._breaker.name)

    def __exit__(self, exc_type, exc: Optional[BaseException], tb) -> None:
        if exc is None:
            self._breaker.mark_success()
        elif isinstance(exc, Exception):
            if self._is_failure(exc):
                self._breaker.mark_failed()
            else:
                self._breaker.mark_success()
        # 取消 / GeneratorExit 等 BaseException 不记账：调用没有结果，不说明下游好坏
