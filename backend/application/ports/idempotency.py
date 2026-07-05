"""Application-owned idempotency port abstraction.

This defines a minimal interface for implementing Idempotency-Key behavior
without coupling the application layer to infrastructure (e.g., Redis).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable


class IdempotencyStoreUnavailableError(RuntimeError):
    """Store 后端（如 Redis）不可用，无法判定幂等状态。

    刻意不继承 BusinessException：IdempotencyContext 对非业务异常走 fail-open
    （告警 + 本请求禁用幂等去重 + 继续执行），而不是把基础设施故障误报成
    "请求处理中" 的 4xx。
    """


@dataclass(frozen=True, slots=True)
class IdempotencyRecord:
    scope: str
    key: str
    request_hash: str
    payload: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class IdempotencyStore(Protocol):
    async def get(self, *, scope: str, key: str) -> Optional[IdempotencyRecord]: ...

    async def try_start(
        self,
        *,
        scope: str,
        key: str,
        request_hash: str,
        ttl_seconds: int,
    ) -> bool: ...

    async def set_result(
        self,
        *,
        scope: str,
        key: str,
        request_hash: str,
        payload: dict[str, Any],
        ttl_seconds: int,
    ) -> None: ...

    async def release(self, *, scope: str, key: str) -> None: ...
