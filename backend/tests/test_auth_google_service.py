# input: AuthApplicationService.login_with_google + fake UoW/repo/verifier/token
# output: Google 登录编排 4 路径行为测试（已绑/验证邮箱链接/新建/未验证不链接）
# pos: 后端测试 - 认证应用服务 Google 登录用例验证；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Behavior tests for AuthApplicationService.login_with_google (find/link/create)."""

from __future__ import annotations

from typing import Optional

from application.ports.oauth import GoogleIdentity
from application.ports.security import TokenPair
from application.services.auth_service import AuthApplicationService
from application.utils.time import utcnow
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


class FakeUoW:
    def __init__(self, repo: FakeUserRepo) -> None:
        self.user_repository = repo
        self.commits = 0

    async def __aenter__(self) -> "FakeUoW":
        return self

    async def __aexit__(self, *exc) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1


class FakeTokens:
    def __init__(self) -> None:
        self.subjects: list[str] = []

    def issue_pair(self, *, subject: str) -> TokenPair:
        self.subjects.append(subject)
        return TokenPair(access_token=f"a-{subject}", refresh_token=f"r-{subject}", expires_in=1800)

    def verify(self, token: str, *, expected_type) -> str:  # pragma: no cover - unused here
        raise NotImplementedError


class FakeVerifier:
    def __init__(self, identity: GoogleIdentity) -> None:
        self._identity = identity

    def verify(self, credential: str) -> GoogleIdentity:
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
        google_verifier=FakeVerifier(identity),
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
    pair = await svc.login_with_google("cred")

    assert tokens.subjects == [str(existing.id)]
    assert repo.oauth[("google", "sub-2")] == existing.id  # 已链接到原账号
    assert len(repo.users) == 1  # 未新建


async def test_unknown_creates_new_user_and_links() -> None:
    repo = FakeUserRepo()
    identity = GoogleIdentity(sub="sub-3", email="carol@x.com", email_verified=True, name="Carol")
    svc, tokens = _service(repo, identity)
    pair = await svc.login_with_google("cred")

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
