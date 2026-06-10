# input: User 领域实体（纯接口定义）
# output: UserRepository 仓储接口
# owner: wanhua.gu
# pos: 领域层 - 用户仓储接口，由 infrastructure 实现；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Repository interface for the user aggregate."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from domain.user.entity import User


class UserRepository(ABC):
    @abstractmethod
    async def create(self, user: User) -> User: ...

    @abstractmethod
    async def update(self, user: User) -> User: ...

    @abstractmethod
    async def get_by_id(self, user_id: int) -> Optional[User]: ...

    @abstractmethod
    async def get_by_username(self, username: str) -> Optional[User]: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]: ...
