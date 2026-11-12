"""Repository interface for the user aggregate."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from domain.user.entity import User
from domain.user.oauth_account import OAuthAccount


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

    @abstractmethod
    async def get_by_oauth(self, provider: str, provider_sub: str) -> Optional[User]:
        """Return the user linked to a federated identity, or None."""
        ...

    @abstractmethod
    async def add_oauth_account(self, account: OAuthAccount) -> OAuthAccount:
        """Persist a new federated-identity link for an existing user."""
        ...
