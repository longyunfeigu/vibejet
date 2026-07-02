# input: UserRepository 接口（无外部系统依赖）
# output: UserDomainService 用户域业务规则
# owner: wanhua.gu
# pos: 领域服务 - 跨实体业务校验（用户名/邮箱唯一性）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Domain service for user business rules spanning the aggregate."""

from __future__ import annotations

from domain.common.exceptions import UserAlreadyExistsException, UsernameAlreadyExistsException
from domain.user.repository import UserRepository


class UserDomainService:
    """Business validation that needs repository lookups but no external systems."""

    def __init__(self, user_repository: UserRepository) -> None:
        self._users = user_repository

    async def ensure_username_available(self, username: str) -> None:
        if await self._users.get_by_username(username) is not None:
            raise UsernameAlreadyExistsException(username)

    async def ensure_email_available(self, email: str) -> None:
        if await self._users.get_by_email(email) is not None:
            raise UserAlreadyExistsException(email)

    async def derive_unique_username(self, email: str) -> str:
        """Generate a valid, unique username from an email local-part.

        Used when creating users from federated logins (no chosen username).
        Sanitizes to the allowed charset ``[a-zA-Z0-9_.-]``, pads to >= 3 chars,
        then appends an incrementing suffix until unused.
        """
        local = email.split("@", 1)[0]
        base = "".join(ch for ch in local if ch.isalnum() or ch in "_.-") or "user"
        base = base[:40]
        if len(base) < 3:
            base = f"{base}_user"[:40]

        candidate = base
        suffix = 0
        while await self._users.get_by_username(candidate) is not None:
            suffix += 1
            candidate = f"{base}{suffix}"[:50]
        return candidate
