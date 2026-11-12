"""Security ports: password hashing and token issuance/verification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

TokenType = Literal["access", "refresh"]


@dataclass(frozen=True)
class TokenPair:
    """Issued token pair returned to clients."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 0  # access token TTL in seconds


class PasswordHasher(Protocol):
    """密码哈希端口。

    方法为 async：argon2 这类哈希算法故意昂贵（几十~上百毫秒/次），实现必须把
    计算卸载出事件循环（如 ``asyncio.to_thread``），否则单 worker 下每次登录会
    冻结所有并发请求。
    """

    async def hash(self, password: str) -> str: ...

    async def verify(self, password: str, hashed: str) -> bool: ...


class TokenProvider(Protocol):
    def issue_pair(self, *, subject: str) -> TokenPair:
        """Issue an access+refresh token pair for the given subject (user id)."""
        ...

    def verify(self, token: str, *, expected_type: TokenType) -> str:
        """Validate a token and return its subject.

        Must raise ``InvalidTokenException`` on bad signature, expiry,
        or token-type mismatch (e.g. refresh token used as access token).
        """
        ...
