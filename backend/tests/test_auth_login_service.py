# input: AuthApplicationService.login + fake UoW/repo/hasher/token
# output: 本地登录行为测试（凭据错误不可区分 + 时序均衡 dummy verify + oauth-only 用户拒绝）
# pos: 后端测试 - 认证应用服务本地登录用例验证；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Behavior tests for AuthApplicationService.login (enumeration-resistant credential check)."""

from __future__ import annotations

from typing import Optional

import pytest

import application.services.auth_service as auth_service_module
from application.dto import LoginRequestDTO, RegisterRequestDTO
from application.ports.security import TokenPair
from application.ports.unit_of_work import AbstractUnitOfWork
from application.services.auth_service import AuthApplicationService
from application.utils.time import utcnow
from domain.common.exceptions import PasswordErrorException
from domain.user.entity import User


class FakeUserRepo:
    def __init__(self) -> None:
        self.users: dict[int, User] = {}
        self._seq = 0

    async def get_by_username(self, username: str) -> Optional[User]:
        return next((u for u in self.users.values() if u.username == username), None)

    async def get_by_email(self, email: str) -> Optional[User]:
        return next((u for u in self.users.values() if u.email == email), None)

    async def get_by_id(self, uid: int) -> Optional[User]:
        return self.users.get(uid)

    async def create(self, user: User) -> User:
        self._seq += 1
        user.id = self._seq
        self.users[user.id] = user
        return user


class FakeUoW(AbstractUnitOfWork):
    def __init__(self, repo: FakeUserRepo) -> None:
        super().__init__()
        self.user_repository = repo

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class FakeHasher:
    """hash() 前缀标记；verify() 记录调用以断言时序均衡路径被执行。

    与 PasswordHasher 端口一致：方法为 async（真实实现卸载线程池）。
    """

    def __init__(self) -> None:
        self.verify_calls: list[str] = []

    async def hash(self, password: str) -> str:
        return f"hashed:{password}"

    async def verify(self, password: str, hashed: str) -> bool:
        self.verify_calls.append(hashed)
        return hashed == f"hashed:{password}"


class FakeTokens:
    def issue_pair(self, *, subject: str) -> TokenPair:
        return TokenPair(access_token=f"a-{subject}", refresh_token=f"r-{subject}", expires_in=1800)

    def verify(self, token: str, *, expected_type) -> str:  # pragma: no cover - unused here
        raise NotImplementedError


@pytest.fixture(autouse=True)
def _reset_dummy_hash_cache():
    # dummy hash 是进程级缓存，隔离测试间的 hasher 差异
    auth_service_module._LOGIN_DUMMY_HASH = None
    yield
    auth_service_module._LOGIN_DUMMY_HASH = None


def _service(repo: FakeUserRepo) -> tuple[AuthApplicationService, FakeHasher]:
    hasher = FakeHasher()
    svc = AuthApplicationService(
        uow_factory=lambda *a, **k: FakeUoW(repo),
        password_hasher=hasher,
        token_provider=FakeTokens(),
    )
    return svc, hasher


async def _make_user(repo: FakeUserRepo, *, hashed_password: Optional[str]) -> User:
    now = utcnow()
    return await repo.create(
        User(
            id=None,
            username="alice",
            email="alice@x.com",
            hashed_password=hashed_password,
            created_at=now,
            updated_at=now,
        )
    )


async def test_login_success() -> None:
    repo = FakeUserRepo()
    await _make_user(repo, hashed_password="hashed:pw123456")
    svc, _ = _service(repo)

    pair = await svc.login(LoginRequestDTO(username="alice", password="pw123456"))
    assert pair.access_token == "a-1"


async def test_unknown_user_rejected_but_still_runs_verify() -> None:
    """查无此人也必须执行一次哈希校验（时序防枚举），且异常与密码错误相同。"""
    svc, hasher = _service(FakeUserRepo())

    with pytest.raises(PasswordErrorException):
        await svc.login(LoginRequestDTO(username="ghost", password="whatever"))
    assert len(hasher.verify_calls) == 1  # dummy verify 已执行


class _RecordingUoW(FakeUoW):
    def __init__(self, repo: FakeUserRepo, events: list[str]) -> None:
        super().__init__(repo)
        self._events = events

    async def __aenter__(self):
        self._events.append("uow_enter")
        return await super().__aenter__()

    async def __aexit__(self, exc_type, exc, tb):
        self._events.append("uow_exit")
        return await super().__aexit__(exc_type, exc, tb)


class _RecordingHasher(FakeHasher):
    def __init__(self, events: list[str]) -> None:
        super().__init__()
        self._events = events

    async def hash(self, password: str) -> str:
        self._events.append("hash")
        return await super().hash(password)


async def test_register_hashes_password_outside_transaction() -> None:
    """argon2 哈希必须在事务外计算：既不占数据库连接，也已由实现卸载出事件循环。"""
    events: list[str] = []
    repo = FakeUserRepo()
    svc = AuthApplicationService(
        uow_factory=lambda *a, **k: _RecordingUoW(repo, events),
        password_hasher=_RecordingHasher(events),
        token_provider=FakeTokens(),
    )

    user = await svc.register(
        RegisterRequestDTO(username="bob", email="bob@x.com", password="pw12345678")
    )
    assert user.username == "bob"
    assert repo.users[user.id].hashed_password == "hashed:pw12345678"

    hash_idx = events.index("hash")
    # hash 发生时没有开启中的 UoW：其前的 enter/exit 已配平
    assert events[:hash_idx].count("uow_enter") == events[:hash_idx].count("uow_exit")
    # 结构 = 只读预检事务 + 写入事务
    assert events.count("uow_enter") == 2


async def test_oauth_only_user_rejected_even_with_dummy_plaintext() -> None:
    """无本地密码的联合登录用户不可走密码登录；
    即便输入恰好等于 dummy 明文（verify 会返回 True）也必须拒绝。"""
    repo = FakeUserRepo()
    await _make_user(repo, hashed_password=None)
    svc, hasher = _service(repo)

    with pytest.raises(PasswordErrorException):
        await svc.login(
            LoginRequestDTO(username="alice", password="vibejet-login-timing-equalizer")
        )
    assert len(hasher.verify_calls) == 1
