"""Login gate: JWT verification, token → user resolution, and the 401 on protected routes.

Every route-level ownership test overrides ``get_current_user``; this file is what proves the
real gate in front of them works.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import pytest
from httpx import ASGITransport, AsyncClient

from api.dependencies import get_auth_service
from application.services.auth_service import AuthApplicationService
from domain.common.exceptions import InvalidTokenException, UserInactiveException
from domain.user.entity import User
from infrastructure.security.jwt_tokens import JwtTokenProvider

SECRET = "unit-test-only-secret-key-0123456789abcdef"


def _tokens(**kwargs: Any) -> JwtTokenProvider:
    return JwtTokenProvider(secret_key=SECRET, **kwargs)


def _user(user_id: int = 1, *, is_active: bool = True) -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=user_id,
        username=f"user{user_id}",
        email=f"user{user_id}@example.com",
        hashed_password="hash",
        is_active=is_active,
        created_at=now,
        updated_at=now,
    )


class _Users:
    def __init__(self, users: list[User]) -> None:
        self._by_id = {u.id: u for u in users}

    async def get_by_id(self, user_id: int) -> Optional[User]:
        return self._by_id.get(user_id)


class _UoW:
    def __init__(self, users: _Users) -> None:
        self.user_repository = users

    async def __aenter__(self) -> "_UoW":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        return None


def _service(*users: User, tokens: Optional[JwtTokenProvider] = None) -> AuthApplicationService:
    repo = _Users(list(users))
    return AuthApplicationService(
        uow_factory=lambda **_: _UoW(repo),
        password_hasher=object(),  # type: ignore[arg-type]  # 本文件不走密码路径
        token_provider=tokens or _tokens(),
    )


# ── JwtTokenProvider ──


def test_access_token_round_trips_to_subject() -> None:
    pair = _tokens().issue_pair(subject="42")

    assert _tokens().verify(pair.access_token, expected_type="access") == "42"
    assert _tokens().verify(pair.refresh_token, expected_type="refresh") == "42"


def test_token_types_are_not_interchangeable() -> None:
    pair = _tokens().issue_pair(subject="42")

    with pytest.raises(InvalidTokenException):
        _tokens().verify(pair.refresh_token, expected_type="access")
    with pytest.raises(InvalidTokenException):
        _tokens().verify(pair.access_token, expected_type="refresh")


def test_expired_token_is_rejected() -> None:
    pair = _tokens(access_ttl_seconds=-1).issue_pair(subject="42")

    with pytest.raises(InvalidTokenException) as caught:
        _tokens().verify(pair.access_token, expected_type="access")
    assert caught.value.details == {"reason": "expired"}


def test_token_signed_with_another_key_is_rejected() -> None:
    forged = JwtTokenProvider(secret_key="another-secret-key-0123456789abcdef").issue_pair(
        subject="42"
    )

    with pytest.raises(InvalidTokenException):
        _tokens().verify(forged.access_token, expected_type="access")


def test_garbage_token_is_rejected() -> None:
    with pytest.raises(InvalidTokenException):
        _tokens().verify("not-a-jwt", expected_type="access")


# ── AuthApplicationService: token → user ──


async def test_get_current_user_resolves_active_user() -> None:
    access = _tokens().issue_pair(subject="1").access_token

    user = await _service(_user(1)).get_current_user(access)

    assert user.id == 1
    assert user.username == "user1"


@pytest.mark.parametrize("subject", ["999", "not-an-int"])
async def test_get_current_user_rejects_unknown_or_malformed_subject(subject: str) -> None:
    access = _tokens().issue_pair(subject=subject).access_token

    with pytest.raises(InvalidTokenException):
        await _service(_user(1)).get_current_user(access)


async def test_get_current_user_rejects_inactive_user() -> None:
    access = _tokens().issue_pair(subject="1").access_token

    with pytest.raises(UserInactiveException):
        await _service(_user(1, is_active=False)).get_current_user(access)


async def test_refresh_issues_new_pair_only_for_refresh_tokens() -> None:
    pair = _tokens().issue_pair(subject="1")
    service = _service(_user(1))

    renewed = await service.refresh(pair.refresh_token)
    assert _tokens().verify(renewed.access_token, expected_type="access") == "1"

    with pytest.raises(InvalidTokenException):
        await service.refresh(pair.access_token)


# ── HTTP: the real get_current_user dependency ──


@pytest.fixture
def app():
    from main import app

    app.dependency_overrides[get_auth_service] = lambda: _service(_user(1))
    yield app
    app.dependency_overrides.pop(get_auth_service, None)


async def _get_me(app: Any, headers: dict[str, str]):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.get("/api/v1/auth/me", headers=headers)


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer not-a-jwt"}, {"Authorization": "Basic dXNlcjpwYXNz"}],
    ids=["no-token", "garbage-token", "wrong-scheme"],
)
async def test_protected_route_without_valid_token_is_401(
    app: Any, headers: dict[str, str]
) -> None:
    resp = await _get_me(app, headers)

    assert resp.status_code == 401


async def test_protected_route_with_refresh_token_is_401(app: Any) -> None:
    refresh = _tokens().issue_pair(subject="1").refresh_token

    resp = await _get_me(app, {"Authorization": f"Bearer {refresh}"})

    assert resp.status_code == 401


async def test_protected_route_with_access_token_returns_user(app: Any) -> None:
    access = _tokens().issue_pair(subject="1").access_token

    resp = await _get_me(app, {"Authorization": f"Bearer {access}"})

    assert resp.status_code == 200
    assert resp.json()["data"]["username"] == "user1"
