"""SREBreaker：移植自 Kratos internal/circuitbreaker/sre.go 的行为验证。

验收标准（Given-When-Then）：
- 窗口内请求数不足 request 阈值 → 全部放行（样本不够不下结论）
- 成功数 * k ≥ 总数（失败率未超 failure_ratio）→ 放行
- 失败率超阈值 → 按 max(0, (total - k*successes) / (total + 1)) 的概率在本地拒绝
- 窗口过期后统计清零 → 恢复放行
- guard：被拒抛 CircuitBreakerOpenError 且记一次失败；调用成功记成功；
  is_failure 判定为下游故障记失败、其余异常记成功；取消类 BaseException 不记账
"""

from __future__ import annotations

import asyncio

import pytest

from infrastructure.external.circuit_breaker import CircuitBreakerOpenError, SREBreaker


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def _breaker(clock: _Clock, rnd: float = 0.0) -> SREBreaker:
    return SREBreaker("test", window=10.0, buckets=10, clock=clock, random=lambda: rnd)


def _record(breaker: SREBreaker, *, successes: int, failures: int) -> None:
    for _ in range(successes):
        breaker.mark_success()
    for _ in range(failures):
        breaker.mark_failed()


def test_allows_everything_below_request_threshold() -> None:
    breaker = _breaker(_Clock())
    _record(breaker, successes=0, failures=19)  # 默认 request=20

    assert breaker.allow()


def test_allows_while_failure_ratio_is_healthy() -> None:
    breaker = _breaker(_Clock())
    _record(breaker, successes=10, failures=10)  # k=2：2*10 = 20 ≥ total 20 → drop_ratio=0

    assert breaker.allow()


def test_rejects_probabilistically_when_failing() -> None:
    clock = _Clock()
    failing = _breaker(clock, rnd=0.0)
    lucky = _breaker(clock, rnd=0.99)
    _record(failing, successes=0, failures=20)
    _record(lucky, successes=0, failures=20)

    # drop_ratio = (20 - 0) / 21 ≈ 0.952：随机数落在其下被拒，之上放行
    assert not failing.allow()
    assert lucky.allow()


def test_window_expiry_resets_statistics() -> None:
    clock = _Clock()
    breaker = _breaker(clock)
    _record(breaker, successes=0, failures=50)
    assert not breaker.allow()

    clock.now += 10.0  # 整个窗口过期

    assert breaker.allow()


def test_guard_rejection_raises_and_counts_as_failure() -> None:
    clock = _Clock()
    breaker = _breaker(clock)
    _record(breaker, successes=0, failures=20)

    with pytest.raises(CircuitBreakerOpenError) as exc_info, breaker.guard(lambda exc: True):
        pytest.fail("rejected call must not run")

    assert exc_info.value.reason == "CIRCUITBREAKER"
    assert breaker._stat.summary() == (0, 21)


def test_guard_records_outcome_by_classifier() -> None:
    breaker = _breaker(_Clock())

    def _is_timeout(exc: BaseException) -> bool:
        return isinstance(exc, TimeoutError)

    with breaker.guard(_is_timeout):
        pass
    with pytest.raises(TimeoutError), breaker.guard(_is_timeout):
        raise TimeoutError
    with pytest.raises(ValueError), breaker.guard(_is_timeout):
        raise ValueError  # 非下游故障（如 4xx）说明下游健康

    assert breaker._stat.summary() == (2, 3)


def test_guard_ignores_cancellation() -> None:
    breaker = _breaker(_Clock())

    with pytest.raises(asyncio.CancelledError), breaker.guard(lambda exc: True):
        raise asyncio.CancelledError

    assert breaker._stat.summary() == (0, 0)
