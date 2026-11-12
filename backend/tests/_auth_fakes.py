"""Shared fakes for AuthApplicationService tests (Google / Lark login flows)."""

from __future__ import annotations

from typing import Optional

from application.ports.security import TokenPair
from application.ports.unit_of_work import AbstractUnitOfWork
from domain.common.exceptions import UserAlreadyExistsException
from domain.user.entity import User
from domain.user.oauth_account import OAuthAccount


class FakeUserRepo:
    def __init__(self) -> None:
        self.users: dict[int, User] = {}
        self.oauth: dict[tuple[str, str], int] = {}
        self._seq = 0

    async def get_by_oauth(self, provider: str, sub: str) -> Optional[User]:
        uid = self.oauth.get((provider, sub))
        return self.users.get(uid) if uid else None

    async def get_by_email(self, email: str) -> Optional[User]:
        for u in self.users.values():
            if u.email == email and not u.is_deleted():
                return u
        return None

    async def get_by_username(self, username: str) -> Optional[User]:
        for u in self.users.values():
            if u.username == username:
                return u
        return None

    async def get_by_id(self, uid: int) -> Optional[User]:
        return self.users.get(uid)

    async def create(self, user: User) -> User:
        self._seq += 1
        user.id = self._seq
        self.users[user.id] = user
        return user

    async def update(self, user: User) -> User:
        self.users[user.id] = user
        return user

    async def add_oauth_account(self, account: OAuthAccount) -> OAuthAccount:
        key = (account.provider, account.provider_sub)
        if key in self.oauth:
            raise UserAlreadyExistsException(account.email or account.provider_sub)
        self.oauth[key] = account.user_id
        account.id = len(self.oauth)
        return account


class FakeUoW(AbstractUnitOfWork):
    """继承端口基类以复用真实退出语义（干净退出即提交，异常回滚）。"""

    def __init__(self, repo: FakeUserRepo) -> None:
        super().__init__()
        self.user_repository = repo
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        return None


class FakeTokens:
    def __init__(self) -> None:
        self.subjects: list[str] = []

    def issue_pair(self, *, subject: str) -> TokenPair:
        self.subjects.append(subject)
        return TokenPair(access_token=f"a-{subject}", refresh_token=f"r-{subject}", expires_in=1800)

    def verify(self, token: str, *, expected_type) -> str:  # pragma: no cover - unused here
        raise NotImplementedError
