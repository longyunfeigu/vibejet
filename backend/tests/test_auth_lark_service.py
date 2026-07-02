# input: AuthApplicationService.login_with_oauth + fake UoW/repo/exchanger/token
# output: 飞书/Lark 授权码登录编排路径行为测试（已绑/enterprise_email链接/新建合成邮箱/未配置/停用/provider 透传）
# pos: 后端测试 - 认证应用服务飞书/Lark 授权码登录用例验证；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Behavior tests for AuthApplicationService.login_with_oauth (Feishu/Lark find/link/create)."""

from __future__ import annotations

import pytest

from application.ports.oauth import OAuthIdentity
from application.services.auth_service import AuthApplicationService
from application.utils.time import utcnow
from domain.common.exceptions import UserInactiveException
from domain.user.entity import User

# 复用 Google 服务测试里的 fake 实现（同一套 UoW/repo/token 契约）。
from tests.test_auth_google_service import FakeTokens, FakeUoW, FakeUserRepo


class FakeOAuthExchanger:
    """Stub LarkAuthCodeExchanger：跳过真实 token/user_info 调用，直接返回预置身份。"""

    def __init__(self, identity: OAuthIdentity) -> None:
        self._identity = identity
        self.codes: list[str] = []

    async def exchange(self, code: str) -> OAuthIdentity:
        self.codes.append(code)
        return self._identity


def _service(
    repo: FakeUserRepo, identity: OAuthIdentity, *, provider: str = "feishu"
) -> tuple[AuthApplicationService, FakeTokens]:
    uow = FakeUoW(repo)
    tokens = FakeTokens()
    svc = AuthApplicationService(
        uow_factory=lambda *a, **k: uow,
        password_hasher=object(),  # unused in oauth flow
        token_provider=tokens,
        oauth_exchangers={provider: FakeOAuthExchanger(identity)},
    )
    return svc, tokens


async def test_no_email_creates_user_with_synthesized_placeholder() -> None:
    repo = FakeUserRepo()
    identity = OAuthIdentity(sub="on_union_1", email=None, email_verified=False, name="张三")
    svc, tokens = _service(repo, identity, provider="feishu")

    await svc.login_with_oauth("feishu", "code")

    assert len(repo.users) == 1
    user = next(iter(repo.users.values()))
    assert user.email == "on_union_1@feishu.local"  # 合成占位邮箱
    assert user.hashed_password is None
    assert user.full_name == "张三"
    assert repo.oauth[("feishu", "on_union_1")] == user.id
    assert tokens.subjects == [str(user.id)]


async def test_existing_oauth_link_logs_in_without_creating_user() -> None:
    repo = FakeUserRepo()
    now = utcnow()
    existing = await repo.create(
        User(
            id=None,
            username="lark_user",
            email="on_x@lark.local",
            hashed_password=None,
            created_at=now,
            updated_at=now,
        )
    )
    repo.oauth[("lark", "on_x")] = existing.id

    identity = OAuthIdentity(sub="on_x", email=None, email_verified=False, name="L")
    svc, tokens = _service(repo, identity, provider="lark")
    pair = await svc.login_with_oauth("lark", "code")

    assert pair.access_token == f"a-{existing.id}"
    assert len(repo.users) == 1  # 未新建


async def test_enterprise_email_auto_links_to_existing_account() -> None:
    repo = FakeUserRepo()
    now = utcnow()
    existing = await repo.create(
        User(
            id=None,
            username="bob",
            email="bob@corp.com",
            hashed_password="h",  # 原本是密码账号
            created_at=now,
            updated_at=now,
        )
    )

    # enterprise_email 视作已验证 → 命中已有同邮箱账号则自动链接（不新建）
    identity = OAuthIdentity(sub="on_bob", email="bob@corp.com", email_verified=True, name="Bob")
    svc, tokens = _service(repo, identity, provider="feishu")
    await svc.login_with_oauth("feishu", "code")

    assert tokens.subjects == [str(existing.id)]
    assert repo.oauth[("feishu", "on_bob")] == existing.id
    assert len(repo.users) == 1  # 未新建


async def test_not_configured_provider_raises() -> None:
    # oauth_exchangers 不含该 provider（缺 app_id/secret）→ fail-closed
    svc = AuthApplicationService(
        uow_factory=lambda *a, **k: FakeUoW(FakeUserRepo()),
        password_hasher=object(),
        token_provider=FakeTokens(),
        oauth_exchangers={},
    )
    with pytest.raises(RuntimeError):
        await svc.login_with_oauth("feishu", "code")


async def test_inactive_user_cannot_login() -> None:
    repo = FakeUserRepo()
    now = utcnow()
    existing = await repo.create(
        User(
            id=None,
            username="erin",
            email="on_erin@feishu.local",
            hashed_password=None,
            is_active=False,
            created_at=now,
            updated_at=now,
        )
    )
    repo.oauth[("feishu", "on_erin")] = existing.id

    identity = OAuthIdentity(sub="on_erin", email=None, email_verified=False, name="Erin")
    svc, _tokens = _service(repo, identity, provider="feishu")
    with pytest.raises(UserInactiveException):
        await svc.login_with_oauth("feishu", "code")
