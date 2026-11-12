"""Tests for SQLAlchemyUserRepository OAuth identity linking."""

from __future__ import annotations

import pytest

from application.utils.time import utcnow
from domain.common.exceptions import UserAlreadyExistsException
from domain.user.entity import User
from domain.user.oauth_account import OAuthAccount
from infrastructure.repositories.user_repository import SQLAlchemyUserRepository


async def _create_user(repo: SQLAlchemyUserRepository, **overrides) -> User:
    now = utcnow()
    defaults = {
        "id": None,
        "username": "user1",
        "email": "user1@x.com",
        "hashed_password": None,  # 联合登录用户可无密码
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return await repo.create(User(**defaults))


async def test_add_and_get_by_oauth_round_trip(sqlite_session) -> None:
    async with sqlite_session() as session:
        repo = SQLAlchemyUserRepository(session)
        user = await _create_user(repo)

        await repo.add_oauth_account(
            OAuthAccount(
                user_id=user.id,
                provider="google",
                provider_sub="sub-xyz",
                email=user.email,
                created_at=utcnow(),
            )
        )

        found = await repo.get_by_oauth("google", "sub-xyz")
        assert found is not None
        assert found.id == user.id
        assert await repo.get_by_oauth("google", "nope") is None


async def test_duplicate_provider_sub_rejected(sqlite_session) -> None:
    async with sqlite_session() as session:
        repo = SQLAlchemyUserRepository(session)
        user = await _create_user(repo)
        link = OAuthAccount(
            user_id=user.id,
            provider="google",
            provider_sub="dup",
            email=user.email,
            created_at=utcnow(),
        )
        await repo.add_oauth_account(link)

        with pytest.raises(UserAlreadyExistsException):
            await repo.add_oauth_account(
                OAuthAccount(
                    user_id=user.id,
                    provider="google",
                    provider_sub="dup",
                    email=user.email,
                    created_at=utcnow(),
                )
            )


async def test_password_user_create_allows_null_password(sqlite_session) -> None:
    async with sqlite_session() as session:
        repo = SQLAlchemyUserRepository(session)
        user = await _create_user(repo, username="np", email="np@x.com", hashed_password=None)
        stored = await repo.get_by_id(user.id)
        assert stored is not None
        assert stored.hashed_password is None
