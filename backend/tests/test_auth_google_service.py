"""Behavior tests for AuthApplicationService.login_with_google (auth-code find/link/create)."""

from __future__ import annotations

import pytest

from application.ports.oauth import GoogleIdentity
from application.services.auth_service import AuthApplicationService
from application.utils.time import utcnow
from domain.common.exceptions import ServiceUnavailableException, UserInactiveException
from domain.user.entity import User
from shared.codes import BusinessCode
from tests._auth_fakes import FakeTokens, FakeUoW, FakeUserRepo


class FakeExchanger:
    """Stub GoogleAuthCodeExchanger：跳过真实 token 交换，直接返回预置身份。"""

    def __init__(self, identity: GoogleIdentity) -> None:
        self._identity = identity
        self.codes: list[str] = []

    async def exchange(self, code: str) -> GoogleIdentity:
        self.codes.append(code)
        return self._identity


def _service(
    repo: FakeUserRepo, identity: GoogleIdentity
) -> tuple[AuthApplicationService, FakeTokens]:
    uow = FakeUoW(repo)
    tokens = FakeTokens()
    svc = AuthApplicationService(
        uow_factory=lambda *a, **k: uow,
        password_hasher=object(),  # unused in google flow
        token_provider=tokens,
        google_exchanger=FakeExchanger(identity),
    )
    return svc, tokens


async def test_existing_oauth_link_logs_in_without_creating_user() -> None:
    repo = FakeUserRepo()
    now = utcnow()
    existing = await repo.create(
        User(
            id=None,
            username="alice",
            email="alice@x.com",
            hashed_password=None,
            created_at=now,
            updated_at=now,
        )
    )
    repo.oauth[("google", "sub-1")] = existing.id

    identity = GoogleIdentity(sub="sub-1", email="alice@x.com", email_verified=True, name="Alice")
    svc, tokens = _service(repo, identity)
    pair = await svc.login_with_google("cred")

    assert pair.access_token == f"a-{existing.id}"
    assert tokens.subjects == [str(existing.id)]
    assert len(repo.users) == 1  # 未新建用户


async def test_verified_email_links_to_existing_user() -> None:
    repo = FakeUserRepo()
    now = utcnow()
    existing = await repo.create(
        User(
            id=None,
            username="bob",
            email="bob@x.com",
            hashed_password="h",
            created_at=now,
            updated_at=now,
        )
    )

    identity = GoogleIdentity(sub="sub-2", email="bob@x.com", email_verified=True, name="Bob")
    svc, tokens = _service(repo, identity)
    await svc.login_with_google("cred")

    assert tokens.subjects == [str(existing.id)]
    assert repo.oauth[("google", "sub-2")] == existing.id  # 已链接到原账号
    assert len(repo.users) == 1  # 未新建


async def test_unknown_creates_new_user_and_links() -> None:
    repo = FakeUserRepo()
    identity = GoogleIdentity(sub="sub-3", email="carol@x.com", email_verified=True, name="Carol")
    svc, tokens = _service(repo, identity)
    await svc.login_with_google("cred")

    assert len(repo.users) == 1
    new_user = next(iter(repo.users.values()))
    assert new_user.email == "carol@x.com"
    assert new_user.hashed_password is None  # 无本地密码
    assert new_user.username == "carol"  # 邮箱前缀派生
    assert repo.oauth[("google", "sub-3")] == new_user.id
    assert tokens.subjects == [str(new_user.id)]


async def test_unverified_email_does_not_link_to_existing() -> None:
    repo = FakeUserRepo()
    now = utcnow()
    existing = await repo.create(
        User(
            id=None,
            username="dave",
            email="dave@x.com",
            hashed_password="h",
            created_at=now,
            updated_at=now,
        )
    )

    identity = GoogleIdentity(sub="sub-4", email="dave@x.com", email_verified=False, name="Dave")
    svc, tokens = _service(repo, identity)
    await svc.login_with_google("cred")

    # 未验证邮箱：不得链接到已有账号，应新建独立账号
    assert repo.oauth[("google", "sub-4")] != existing.id
    assert len(repo.users) == 2
    # 且未验证邮箱不得写入 users.email（防预注册接管：后续 verified 登录不能匹配到它；
    # 也避免撞 email 唯一约束泄露注册状态）——新账号用占位邮箱
    new_user = repo.users[repo.oauth[("google", "sub-4")]]
    assert new_user.email == "sub-4@google.local"


async def test_unverified_email_never_matched_by_later_verified_login() -> None:
    """接管链回归：攻击者未验证邮箱先登录，受害者 verified 同邮箱后登录，
    两者必须是相互隔离的账号。"""
    repo = FakeUserRepo()

    attacker = GoogleIdentity(
        sub="attacker-sub", email="victim@corp.com", email_verified=False, name="Mallory"
    )
    svc, _ = _service(repo, attacker)
    await svc.login_with_google("cred-a")

    victim = GoogleIdentity(
        sub="victim-sub", email="victim@corp.com", email_verified=True, name="Victim"
    )
    svc2, _ = _service(repo, victim)
    await svc2.login_with_google("cred-v")

    assert repo.oauth[("google", "victim-sub")] != repo.oauth[("google", "attacker-sub")]


async def test_not_configured_raises() -> None:
    # google_exchanger 为 None（缺 client_id/secret）时应 fail-closed 拒绝
    svc = AuthApplicationService(
        uow_factory=lambda *a, **k: FakeUoW(FakeUserRepo()),
        password_hasher=object(),
        token_provider=FakeTokens(),
        google_exchanger=None,
    )
    # 未配置是服务端能力缺失 → 503 SERVICE_UNAVAILABLE（不是 500）
    with pytest.raises(ServiceUnavailableException) as exc_info:
        await svc.login_with_google("code")
    assert exc_info.value.code == BusinessCode.SERVICE_UNAVAILABLE
    assert exc_info.value.message_key == "auth.google.not_configured"


async def test_inactive_user_cannot_login() -> None:
    repo = FakeUserRepo()
    now = utcnow()
    existing = await repo.create(
        User(
            id=None,
            username="erin",
            email="erin@x.com",
            hashed_password=None,
            is_active=False,
            created_at=now,
            updated_at=now,
        )
    )
    repo.oauth[("google", "sub-5")] = existing.id

    identity = GoogleIdentity(sub="sub-5", email="erin@x.com", email_verified=True, name="Erin")
    svc, _tokens = _service(repo, identity)
    with pytest.raises(UserInactiveException):
        await svc.login_with_google("code")
