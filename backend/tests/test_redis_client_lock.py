"""Characterization tests for RedisClient.lock.

重构（降 McCabe 复杂度 + 修 lint）前后必须同绿。续租循环的等待通过替换模块内
asyncio.wait_for 来"快进"，从而无需真实等待即可断言续租间隔与 extend 调用；
另有一条用真实计时器的用例证明未替换时同样成立。
"""

from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace
from typing import Any, Callable, Optional

import pytest
from redis.exceptions import RedisError
from structlog.testing import capture_logs

from infrastructure.external.cache import redis_client as redis_mod
from infrastructure.external.cache.redis_client import RedisClient


class _FakeLock:
    """redis.asyncio.lock.Lock 替身：记录 acquire/extend/release，可注入结果与异常。"""

    def __init__(
        self,
        *,
        acquired: bool = True,
        acquire_error: Optional[Exception] = None,
        release_error: Optional[Exception] = None,
        extend_errors: Optional[list[Optional[Exception]]] = None,
    ) -> None:
        self.acquired = acquired
        self.acquire_error = acquire_error
        self.release_error = release_error
        self._extend_errors = list(extend_errors or [])
        self.acquire_calls = 0
        self.release_calls = 0
        self.extend_calls: list[float] = []

    async def acquire(self) -> bool:
        self.acquire_calls += 1
        if self.acquire_error is not None:
            raise self.acquire_error
        return self.acquired

    async def extend(self, additional_time: float) -> bool:
        self.extend_calls.append(additional_time)
        if self._extend_errors:
            err = self._extend_errors.pop(0)
            if err is not None:
                raise err
        return True

    async def release(self) -> None:
        self.release_calls += 1
        if self.release_error is not None:
            raise self.release_error


class _FakeRedis:
    def __init__(self, lock: _FakeLock) -> None:
        self.lock_obj = lock
        self.lock_calls: list[tuple[str, dict[str, Any]]] = []

    def lock(self, name: str, **kwargs: Any) -> _FakeLock:
        self.lock_calls.append((name, kwargs))
        return self.lock_obj


def _client(lock: _FakeLock, namespace: str = "ns") -> tuple[RedisClient, _FakeRedis]:
    fake = _FakeRedis(lock)
    redis: Any = fake
    return RedisClient(redis, namespace=namespace, enable_metrics=False, enable_logging=False), fake


class _ScriptedWaitFor:
    """替换续租循环里的 asyncio.wait_for。

    前 `elapse` 次调用模拟"间隔到期、cancel 未触发"（立即抛 TimeoutError），
    之后真正等待 cancel 事件并置位 `parked`，供测试同步。`swallow_cancel=True`
    模拟 wait_for 在 cancel 事件与任务取消同时到达时返回事件结果而非抛 CancelledError。
    """

    def __init__(self, elapse: int, swallow_cancel: bool = False) -> None:
        self._elapse = elapse
        self._swallow_cancel = swallow_cancel
        self.timeouts: list[float] = []
        self.parked = asyncio.Event()

    async def __call__(self, aw: Any, timeout: float) -> Any:
        self.timeouts.append(timeout)
        if len(self.timeouts) <= self._elapse:
            aw.close()
            raise asyncio.TimeoutError
        self.parked.set()
        try:
            return await aw
        except asyncio.CancelledError:
            if not self._swallow_cancel:
                raise
            return True


class _AsyncioWithWaitFor:
    """只替换 wait_for 的 asyncio 代理，其余属性透传真实模块。"""

    def __init__(self, wait_for: _ScriptedWaitFor) -> None:
        self.wait_for = wait_for

    def __getattr__(self, name: str) -> Any:
        return getattr(asyncio, name)


class _FixedUniform:
    def __init__(self, value: float) -> None:
        self.value = value
        self.calls: list[tuple[float, float]] = []

    def uniform(self, a: float, b: float) -> float:
        self.calls.append((a, b))
        return self.value


def _settings(**overrides: Any) -> SimpleNamespace:
    values: dict[str, Any] = {
        "REDIS_LOCK_AUTO_RENEW_DEFAULT": False,
        "REDIS_LOCK_AUTO_RENEW_INTERVAL_RATIO": 0.6,
        "REDIS_LOCK_AUTO_RENEW_JITTER_RATIO": 0.0,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.fixture(autouse=True)
def lock_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(redis_mod, "settings", _settings())


@pytest.fixture
def scripted(monkeypatch: pytest.MonkeyPatch) -> Callable[[int], _ScriptedWaitFor]:
    def install(elapse: int = 0) -> _ScriptedWaitFor:
        wait_for = _ScriptedWaitFor(elapse)
        monkeypatch.setattr(redis_mod, "asyncio", _AsyncioWithWaitFor(wait_for))
        return wait_for

    return install


@pytest.fixture
def uniform(monkeypatch: pytest.MonkeyPatch) -> Callable[[float], _FixedUniform]:
    def install(value: float) -> _FixedUniform:
        fixed = _FixedUniform(value)
        monkeypatch.setattr(redis_mod, "random", fixed)
        return fixed

    return install


def _pending_tasks() -> list[asyncio.Task]:
    current = asyncio.current_task()
    return [task for task in asyncio.all_tasks() if task is not current and not task.done()]


async def _hold_until_parked(
    client: RedisClient, wait_for: _ScriptedWaitFor, **kwargs: Any
) -> None:
    async with client.lock("job", **kwargs):
        await asyncio.wait_for(wait_for.parked.wait(), timeout=1)


# ── 获取 / 释放 ───────────────────────────────────────────────────────


async def test_lock_acquires_yields_lock_and_releases_on_exit() -> None:
    lock = _FakeLock()
    client, fake = _client(lock)

    async with client.lock("job") as held:
        assert held is lock
        assert lock.release_calls == 0

    assert fake.lock_calls == [
        ("lock:ns:job", {"timeout": 10, "blocking_timeout": 5, "thread_local": True})
    ]
    assert (lock.acquire_calls, lock.release_calls, lock.extend_calls) == (1, 1, [])


async def test_lock_passes_custom_options_and_unnamespaced_key() -> None:
    lock = _FakeLock()
    client, fake = _client(lock, namespace="")

    async with client.lock("job", timeout=30, blocking_timeout=2, thread_local=False):
        pass

    assert fake.lock_calls == [
        ("lock:job", {"timeout": 30, "blocking_timeout": 2, "thread_local": False})
    ]


async def test_lock_not_acquired_raises_timeout_without_releasing() -> None:
    lock = _FakeLock(acquired=False)
    client, _ = _client(lock)
    entered = []

    with pytest.raises(TimeoutError) as info:
        async with client.lock("job"):
            entered.append(True)

    assert type(info.value) is TimeoutError
    assert str(info.value) == "获取锁失败: lock:ns:job"
    assert entered == []
    assert lock.release_calls == 0


async def test_lock_acquire_error_propagates_without_releasing() -> None:
    err = RedisError("connection lost")
    lock = _FakeLock(acquire_error=err)
    client, _ = _client(lock)

    with capture_logs() as logs, pytest.raises(RedisError) as info:
        async with client.lock("job"):
            pass

    assert info.value is err
    assert lock.release_calls == 0
    assert logs == []


async def test_lock_release_failure_is_logged_not_raised() -> None:
    lock = _FakeLock(release_error=RedisError("not owned"))
    client, _ = _client(lock)

    with capture_logs() as logs:
        async with client.lock("job"):
            pass

    assert lock.release_calls == 1
    assert logs == [{"event": "释放锁失败 [lock:ns:job]: not owned", "log_level": "error"}]


async def test_lock_timeout_logs_no_spurious_release_error() -> None:
    lock = _FakeLock(acquired=False, release_error=RedisError("not owned"))
    client, _ = _client(lock)

    with capture_logs() as logs, pytest.raises(TimeoutError, match="^获取锁失败: lock:ns:job$"):
        async with client.lock("job"):
            pass

    assert logs == []
    assert lock.release_calls == 0


async def test_lock_body_error_propagates_after_release() -> None:
    lock = _FakeLock()
    client, _ = _client(lock)
    err = ValueError("body failed")

    with pytest.raises(ValueError) as info:
        async with client.lock("job"):
            raise err

    assert info.value is err
    assert lock.release_calls == 1


# ── 自动续租：开关 ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("settings_default", "auto_renew", "expect_renew"),
    [(True, None, True), (False, None, False), (True, False, False), (False, True, True)],
    ids=["settings-on", "settings-off", "explicit-off-wins", "explicit-on-wins"],
)
async def test_auto_renew_switch(
    monkeypatch: pytest.MonkeyPatch,
    scripted: Callable[[int], _ScriptedWaitFor],
    settings_default: bool,
    auto_renew: Optional[bool],
    expect_renew: bool,
) -> None:
    monkeypatch.setattr(
        redis_mod, "settings", _settings(REDIS_LOCK_AUTO_RENEW_DEFAULT=settings_default)
    )
    wait_for = scripted(0)
    lock = _FakeLock()
    client, _ = _client(lock)

    if expect_renew:
        await _hold_until_parked(client, wait_for, auto_renew=auto_renew)
        assert wait_for.timeouts == [6.0]
    else:
        async with client.lock("job", auto_renew=auto_renew):
            for _ in range(3):
                await asyncio.sleep(0)
        assert wait_for.timeouts == []

    assert lock.release_calls == 1
    assert _pending_tasks() == []


# ── 自动续租：间隔与抖动 ──────────────────────────────────────────────


@pytest.mark.parametrize(
    ("timeout", "renew_interval", "ratio", "expected"),
    [
        (10, None, 0.6, 6.0),
        (1, None, 0.6, 1.0),
        (10, 2.5, 0.6, 2.5),
        (10, 0.1, 0.6, 0.5),
        (10, None, 0.25, 2.5),
    ],
    ids=[
        "ratio-of-timeout",
        "one-second-minimum",
        "explicit-interval",
        "half-second-floor",
        "ratio-setting",
    ],
)
async def test_auto_renew_interval(
    monkeypatch: pytest.MonkeyPatch,
    scripted: Callable[[int], _ScriptedWaitFor],
    timeout: int,
    renew_interval: Optional[float],
    ratio: float,
    expected: float,
) -> None:
    monkeypatch.setattr(
        redis_mod, "settings", _settings(REDIS_LOCK_AUTO_RENEW_INTERVAL_RATIO=ratio)
    )
    wait_for = scripted(0)
    client, _ = _client(_FakeLock())

    await _hold_until_parked(
        client, wait_for, timeout=timeout, auto_renew=True, renew_interval=renew_interval, jitter=0
    )

    assert wait_for.timeouts == [pytest.approx(expected)]


@pytest.mark.parametrize(
    ("jitter", "settings_jitter", "renew_interval", "random_value", "expected", "expected_calls"),
    [
        (0.2, 0.0, None, 0.1, 6.6, [(-0.2, 0.2)]),
        (None, 0.3, None, -0.3, 4.2, [(-0.3, 0.3)]),
        (0.2, 0.0, 0.5, -0.2, 0.5, [(-0.2, 0.2)]),
        (0, 0.3, None, 0.9, 6.0, []),
    ],
    ids=["explicit-jitter", "settings-jitter", "floor-after-jitter", "zero-jitter-skips-random"],
)
async def test_auto_renew_jitter(
    monkeypatch: pytest.MonkeyPatch,
    scripted: Callable[[int], _ScriptedWaitFor],
    uniform: Callable[[float], _FixedUniform],
    jitter: Optional[float],
    settings_jitter: float,
    renew_interval: Optional[float],
    random_value: float,
    expected: float,
    expected_calls: list[tuple[float, float]],
) -> None:
    monkeypatch.setattr(
        redis_mod, "settings", _settings(REDIS_LOCK_AUTO_RENEW_JITTER_RATIO=settings_jitter)
    )
    wait_for = scripted(0)
    fixed = uniform(random_value)
    client, _ = _client(_FakeLock())

    await _hold_until_parked(
        client, wait_for, auto_renew=True, renew_interval=renew_interval, jitter=jitter
    )

    assert wait_for.timeouts == [pytest.approx(expected)]
    assert fixed.calls == expected_calls


async def test_auto_renew_uses_builtin_defaults_when_settings_lack_ratios(
    monkeypatch: pytest.MonkeyPatch,
    scripted: Callable[[int], _ScriptedWaitFor],
    uniform: Callable[[float], _FixedUniform],
) -> None:
    monkeypatch.setattr(redis_mod, "settings", SimpleNamespace(REDIS_LOCK_AUTO_RENEW_DEFAULT=True))
    wait_for = scripted(0)
    fixed = uniform(0.0)
    client, _ = _client(_FakeLock())

    await _hold_until_parked(client, wait_for)

    assert wait_for.timeouts == [pytest.approx(6.0)]
    assert fixed.calls == [(-0.1, 0.1)]


# ── 自动续租：extend 行为与退出 ───────────────────────────────────────


async def test_auto_renew_extends_by_lock_timeout_each_interval(
    scripted: Callable[[int], _ScriptedWaitFor],
) -> None:
    wait_for = scripted(2)
    lock = _FakeLock()
    client, _ = _client(lock)

    await _hold_until_parked(client, wait_for, timeout=10, auto_renew=True)

    assert lock.extend_calls == [10, 10]
    assert wait_for.timeouts == [6.0, 6.0, 6.0]
    assert lock.release_calls == 1
    assert _pending_tasks() == []


async def test_auto_renew_extend_failure_is_logged_and_renewal_continues(
    scripted: Callable[[int], _ScriptedWaitFor],
) -> None:
    wait_for = scripted(2)
    lock = _FakeLock(extend_errors=[RedisError("lost lease"), None])
    client, _ = _client(lock)

    with capture_logs() as logs:
        await _hold_until_parked(client, wait_for, auto_renew=True)

    assert lock.extend_calls == [10, 10]
    assert logs == [{"event": "锁续租失败 [lock:ns:job]: lost lease", "log_level": "warning"}]
    assert lock.release_calls == 1


@pytest.mark.parametrize("timeout", [0, -1])
async def test_auto_renew_is_skipped_for_non_positive_timeout(
    scripted: Callable[[int], _ScriptedWaitFor], timeout: int
) -> None:
    wait_for = scripted(0)
    lock = _FakeLock()
    client, _ = _client(lock)

    async with client.lock("job", timeout=timeout, auto_renew=True):
        for _ in range(3):
            await asyncio.sleep(0)

    assert wait_for.timeouts == []
    assert lock.extend_calls == []
    assert lock.release_calls == 1
    assert _pending_tasks() == []


async def test_auto_renew_body_error_stops_renewal_and_releases(
    scripted: Callable[[int], _ScriptedWaitFor],
) -> None:
    wait_for = scripted(0)
    lock = _FakeLock()
    client, _ = _client(lock)
    err = ValueError("body failed")

    with pytest.raises(ValueError) as info:
        async with client.lock("job", auto_renew=True):
            await asyncio.wait_for(wait_for.parked.wait(), timeout=1)
            raise err

    assert info.value is err
    assert lock.release_calls == 1
    assert _pending_tasks() == []


async def test_auto_renew_stops_without_extending_when_cancel_event_wins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wait_for = _ScriptedWaitFor(0, swallow_cancel=True)
    monkeypatch.setattr(redis_mod, "asyncio", _AsyncioWithWaitFor(wait_for))
    lock = _FakeLock()
    client, _ = _client(lock)

    await _hold_until_parked(client, wait_for, auto_renew=True)

    assert wait_for.timeouts == [6.0]
    assert lock.extend_calls == []
    assert lock.release_calls == 1
    assert _pending_tasks() == []


class _BrokenUniform:
    def uniform(self, a: float, b: float) -> float:
        raise RuntimeError("rng broken")


async def test_auto_renew_task_crash_is_swallowed_on_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(redis_mod, "random", _BrokenUniform())
    lock = _FakeLock()
    client, _ = _client(lock)

    with capture_logs() as logs:
        async with client.lock("job", auto_renew=True, jitter=0.1):
            for _ in range(3):
                await asyncio.sleep(0)

    assert lock.extend_calls == []
    assert lock.release_calls == 1
    assert logs == []
    assert _pending_tasks() == []


class _SignallingLock(_FakeLock):
    """extend 时置位事件，让测试按事件同步而不是按墙钟睡眠。"""

    def __init__(self) -> None:
        super().__init__()
        self.extended = asyncio.Event()

    async def extend(self, additional_time: float) -> bool:
        result = await super().extend(additional_time)
        self.extended.set()
        return result


async def test_auto_renew_with_real_timer_extends_after_half_second_floor() -> None:
    """不替换 wait_for：真实计时器下续租至少等满 0.5s 下限才 extend，退出时取消 wait_for 中的续租。

    body 在首次 extend 的事件上直接等待并立即退出：事件循环卡顿只会拉长 waited，
    不会多出第二次 extend（body 的唤醒先于续租计时器进入就绪队列）。
    """
    lock = _SignallingLock()
    client, _ = _client(lock)
    loop = asyncio.get_running_loop()
    clock_resolution = time.get_clock_info("monotonic").resolution

    async with client.lock("job", auto_renew=True, renew_interval=0.01, jitter=0):
        started = loop.time()
        async with asyncio.timeout(5):
            await lock.extended.wait()
        waited = loop.time() - started

    assert waited >= 0.5 - clock_resolution
    assert lock.extend_calls == [10]
    assert lock.release_calls == 1
    assert _pending_tasks() == []


async def test_auto_renew_exit_without_yielding_still_releases() -> None:
    """body 期间从未让出事件循环时，续租 task 尚未启动就被 cancel：
    这个自己造成的 CancelledError 不能逃逸给调用方，锁也必须照常释放。
    """
    lock = _FakeLock()
    client, _ = _client(lock)

    async with client.lock("job", auto_renew=True):
        pass

    assert lock.release_calls == 1
    assert _pending_tasks() == []


async def test_outer_cancellation_during_lock_exit_still_releases() -> None:
    """持锁任务在退出时被外部取消：取消照常向上传播，但锁仍被释放。"""
    lock = _FakeLock()
    client, _ = _client(lock)
    inside = asyncio.Event()

    async def hold() -> None:
        async with client.lock("job", auto_renew=True):
            inside.set()
            await asyncio.sleep(10)

    task = asyncio.create_task(hold())
    await inside.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert lock.release_calls == 1
