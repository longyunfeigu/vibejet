"""RedisClient 的错误语义：不吞错，连接/超时故障统一抛 CacheUnavailableError。

降级（fail-open）只发生在显式选择它的调用方：CachePatterns 的读路径，以及
幂等 store 把故障翻译成 IdempotencyStoreUnavailableError 交给 IdempotencyContext。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import ResponseError
from redis.exceptions import TimeoutError as RedisTimeoutError

from application.ports.idempotency import IdempotencyStoreUnavailableError
from infrastructure.adapters import idempotency_store as store_mod
from infrastructure.adapters.idempotency_store import RedisIdempotencyStore
from infrastructure.external.cache import CachePatterns, CacheUnavailableError
from infrastructure.external.cache.redis_client import RedisClient


class _FakeRedis:
    """redis.asyncio.Redis 替身：按方法名注入异常，否则用内存 dict 应答。"""

    def __init__(self, errors: dict[str, Exception] | None = None) -> None:
        self.errors = errors or {}
        self.data: dict[str, str] = {}

    def _maybe_raise(self, op: str) -> None:
        if op in self.errors:
            raise self.errors[op]

    async def get(self, key: str) -> str | None:
        self._maybe_raise("get")
        return self.data.get(key)

    async def set(self, key: str, value: str, *, nx: bool = False, **_: Any) -> bool | None:
        self._maybe_raise("set")
        if nx and key in self.data:
            return None
        self.data[key] = value
        return True

    async def delete(self, *keys: str) -> int:
        self._maybe_raise("delete")
        return sum(1 for k in keys if self.data.pop(k, None) is not None)

    async def scan_iter(self, match: str) -> AsyncIterator[str]:
        self._maybe_raise("scan_iter")
        for k in list(self.data):
            yield k


def _client(fake: _FakeRedis, *, metrics: bool = False) -> RedisClient:
    redis: Any = fake
    return RedisClient(redis, enable_metrics=metrics, enable_logging=False)


@pytest.mark.parametrize("error", [RedisConnectionError("refused"), RedisTimeoutError("timed out")])
async def test_get_raises_unavailable_instead_of_returning_default(error: Exception) -> None:
    client = _client(_FakeRedis({"get": error}), metrics=True)

    with pytest.raises(CacheUnavailableError):
        await client.get("k", default="fallback")

    assert client.metrics is not None
    assert client.metrics.errors == 1


async def test_set_raises_unavailable_instead_of_returning_false() -> None:
    client = _client(_FakeRedis({"set": RedisConnectionError("refused")}))

    with pytest.raises(CacheUnavailableError):
        await client.set("k", "v")


async def test_set_nx_on_existing_key_returns_false_without_error() -> None:
    fake = _FakeRedis()
    client = _client(fake)
    assert await client.set("k", "v1", nx=True) is True

    assert await client.set("k", "v2", nx=True) is False


async def test_non_connection_redis_error_propagates_unchanged() -> None:
    client = _client(_FakeRedis({"get": ResponseError("WRONGTYPE")}))

    with pytest.raises(ResponseError):
        await client.get("k")


async def test_direct_client_calls_are_translated_too() -> None:
    client = _client(_FakeRedis({"scan_iter": RedisConnectionError("refused")}))

    with pytest.raises(CacheUnavailableError):
        await client.keys()


async def test_get_metrics_still_count_hits_and_misses() -> None:
    fake = _FakeRedis()
    fake.data["hit"] = '"v"'
    client = _client(fake, metrics=True)

    assert await client.get("hit") == "v"
    assert await client.get("miss") is None

    assert client.metrics is not None
    assert (client.metrics.hits, client.metrics.misses, client.metrics.errors) == (1, 1, 0)


# ── CachePatterns：降级是显式选择 ─────────────────────────────────────


async def test_cache_aside_falls_back_to_source_when_redis_unavailable() -> None:
    fake = _FakeRedis({"get": RedisConnectionError("down"), "set": RedisConnectionError("down")})
    patterns = CachePatterns(_client(fake))

    async def fetch() -> str:
        return "from-source"

    assert await patterns.cache_aside("k", fetch) == "from-source"


async def test_write_behind_raises_when_redis_unavailable() -> None:
    patterns = CachePatterns(_client(_FakeRedis({"set": RedisConnectionError("down")})))

    with pytest.raises(CacheUnavailableError):
        await patterns.write_behind("k", "v")


# ── 幂等 store：锁被占 vs Redis 故障 ──────────────────────────────────


@pytest.fixture
def store_with(monkeypatch: pytest.MonkeyPatch):
    def _install(fake: _FakeRedis) -> RedisIdempotencyStore:
        client = _client(fake)

        async def _get_client() -> RedisClient:
            return client

        monkeypatch.setattr(store_mod, "get_redis_client", _get_client)
        return RedisIdempotencyStore()

    return _install


async def test_try_start_returns_false_when_lock_already_held(store_with) -> None:
    store = store_with(_FakeRedis())
    assert await store.try_start(scope="s", key="k", request_hash="h", ttl_seconds=5) is True

    assert await store.try_start(scope="s", key="k", request_hash="h", ttl_seconds=5) is False


@pytest.mark.parametrize("op", ["get", "try_start", "set_result"])
async def test_redis_failure_surfaces_as_store_unavailable(store_with, op: str) -> None:
    down = RedisConnectionError("down")
    store = store_with(_FakeRedis({"get": down, "set": down}))
    calls = {
        "get": lambda: store.get(scope="s", key="k"),
        "try_start": lambda: store.try_start(scope="s", key="k", request_hash="h", ttl_seconds=5),
        "set_result": lambda: store.set_result(
            scope="s", key="k", request_hash="h", payload={}, ttl_seconds=5
        ),
    }

    with pytest.raises(IdempotencyStoreUnavailableError):
        await calls[op]()
