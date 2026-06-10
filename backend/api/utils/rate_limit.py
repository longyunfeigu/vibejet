# input: core.config.settings.RATE_LIMIT_PER_MINUTE, request.client IP
# output: rate_limit(scope) FastAPI 依赖工厂（进程内滑动窗口限流）
# owner: wanhua.gu
# pos: 表示层工具 - 端点级限流依赖；单进程实现，多副本部署需换 Redis 实现；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Per-endpoint rate limiting dependency (in-process sliding window).

Deliberately minimal for the template:
- keyed by client IP per scope
- sliding window over ``time.monotonic()``
- state is per-process — behind a multi-worker/multi-replica deployment the
  effective limit is multiplied; swap the storage for Redis (INCR+EXPIRE or a
  sorted set) when you need a global limit

Raises the existing :class:`core.exceptions.RateLimitException`, which the
global handler maps to HTTP 429 with ``retry_after`` details.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Callable, Optional

from fastapi import Request

from core.config import settings
from core.exceptions import RateLimitException

# (scope, client_key) -> recent request timestamps within the window
_hits: dict[tuple[str, str], deque[float]] = {}
# Bound total tracked keys; on overflow drop fully-expired entries first
_MAX_TRACKED_KEYS = 10_000


def _client_key(request: Request) -> str:
    # 模板默认信任直连地址；经反向代理部署时应改读受信的 X-Forwarded-For
    client = request.client
    return client.host if client else "unknown"


def _evict_expired(now: float, window_seconds: float) -> None:
    expired = [key for key, dq in _hits.items() if not dq or now - dq[-1] > window_seconds]
    for key in expired:
        _hits.pop(key, None)


def rate_limit(
    scope: str,
    *,
    limit: Optional[int] = None,
    window_seconds: float = 60.0,
) -> Callable:
    """Build a FastAPI dependency enforcing ``limit`` requests per window.

    ``limit`` defaults to ``settings.RATE_LIMIT_PER_MINUTE`` (evaluated per
    request so tests/env overrides take effect).
    """

    async def _dependency(request: Request) -> None:
        max_requests = limit if limit is not None else settings.RATE_LIMIT_PER_MINUTE
        if max_requests <= 0:  # 0/负数视为关闭限流
            return

        now = time.monotonic()
        key = (scope, _client_key(request))
        bucket = _hits.get(key)
        if bucket is None:
            if len(_hits) >= _MAX_TRACKED_KEYS:
                _evict_expired(now, window_seconds)
            bucket = _hits.setdefault(key, deque())

        # Drop hits that left the window
        while bucket and now - bucket[0] > window_seconds:
            bucket.popleft()

        if len(bucket) >= max_requests:
            retry_after = max(1, int(window_seconds - (now - bucket[0])) + 1)
            raise RateLimitException(retry_after=retry_after)

        bucket.append(now)

    return _dependency
