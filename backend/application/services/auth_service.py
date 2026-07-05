# input: AuthUnitOfWork, PasswordHasher/TokenProvider 端口, GoogleAuthCodeExchanger/LarkAuthCodeExchanger 端口, User 领域实体
# output: AuthApplicationService 注册/登录/Google授权码登录/飞书·Lark授权码登录/刷新/当前用户用例编排
# owner: wanhua.gu
# pos: 应用层服务 - 认证用例编排（注册→哈希入库；登录→校验→签发令牌对；联合登录→授权码换身份→共用 find/link/create）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Application service for authentication workflows."""

from __future__ import annotations

from typing import Callable, Optional, Protocol

from application.dto import LoginRequestDTO, RegisterRequestDTO, TokenPairDTO, UserDTO
from application.ports.oauth import (
    GoogleAuthCodeExchanger,
    LarkAuthCodeExchanger,
    OAuthIdentity,
)
from application.ports.security import PasswordHasher, TokenProvider
from application.utils.time import utcnow
from core.logging_config import get_logger
from domain.common.exceptions import (
    InvalidTokenException,
    PasswordErrorException,
    UserInactiveException,
)
from domain.user.entity import User
from domain.user.oauth_account import OAuthAccount
from domain.user.repository import UserRepository
from domain.user.service import UserDomainService

GOOGLE_PROVIDER = "google"

logger = get_logger(__name__)

# 进程级缓存的 dummy hash（argon2 hash 代价高，不能每请求算一次）。
# verify(输入密码, dummy) 理论上可为 True（输入恰为 dummy 明文），
# 调用方必须仍按 user 存在性判定，不得只看 verify 结果。
_LOGIN_DUMMY_HASH: Optional[str] = None


async def _login_dummy_hash(hasher: PasswordHasher) -> str:
    # 首次并发调用可能重复计算，结果幂等、无需加锁
    global _LOGIN_DUMMY_HASH
    if _LOGIN_DUMMY_HASH is None:
        _LOGIN_DUMMY_HASH = await hasher.hash("vibejet-login-timing-equalizer")
    return _LOGIN_DUMMY_HASH


class AuthUnitOfWork(Protocol):
    @property
    def user_repository(self) -> UserRepository: ...

    async def __aenter__(self) -> "AuthUnitOfWork": ...

    async def __aexit__(self, exc_type, exc, tb) -> None: ...

    async def commit(self) -> None: ...


class AuthApplicationService:
    """Orchestrates registration, login and token verification."""

    def __init__(
        self,
        uow_factory: Callable[..., AuthUnitOfWork],
        password_hasher: PasswordHasher,
        token_provider: TokenProvider,
        google_exchanger: Optional[GoogleAuthCodeExchanger] = None,
        oauth_exchangers: Optional[dict[str, LarkAuthCodeExchanger]] = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._hasher = password_hasher
        self._tokens = token_provider
        self._google = google_exchanger
        # provider(feishu/lark) → 授权码交换器；缺失即该 provider 未配置（fail-closed）。
        self._oauth_exchangers = oauth_exchangers or {}

    async def register(self, dto: RegisterRequestDTO) -> UserDTO:
        """Create a new user with a hashed password."""
        # 唯一性预检走短只读事务；写入与预检之间的并发窗口由 users 表唯一约束
        # 兜底（user_repository.create 将 IntegrityError 映射为域冲突）
        async with self._uow_factory(readonly=True) as uow:
            domain_service = UserDomainService(uow.user_repository)
            await domain_service.ensure_username_available(dto.username)
            await domain_service.ensure_email_available(dto.email)

        # argon2 哈希在事务外计算：不占数据库连接，也不阻塞事件循环（实现已卸载线程池）
        hashed_password = await self._hasher.hash(dto.password)

        now = utcnow()
        user = User(
            id=None,
            username=dto.username,
            email=dto.email,
            hashed_password=hashed_password,
            full_name=dto.full_name,
            created_at=now,
            updated_at=now,
        )
        async with self._uow_factory() as uow:
            user = await uow.user_repository.create(user)

        logger.info("user_registered", user_id=user.id, username=user.username)
        return UserDTO.model_validate(user)

    async def login(self, dto: LoginRequestDTO) -> TokenPairDTO:
        """Verify credentials and issue an access+refresh token pair.

        ``username`` accepts either username or email. Credential errors are
        deliberately indistinguishable (same exception) to avoid user
        enumeration.
        """
        async with self._uow_factory(readonly=True) as uow:
            user = await uow.user_repository.get_by_username(dto.username)
            if user is None and "@" in dto.username:
                user = await uow.user_repository.get_by_email(dto.username)

        # 时序防枚举：查无此人/无本地密码（联合登录用户）时也对 dummy hash 做
        # 一次同代价 verify，避免响应时间区分"用户不存在"与"密码错误"
        candidate_hash = (user.hashed_password if user else None) or await _login_dummy_hash(
            self._hasher
        )
        password_ok = await self._hasher.verify(dto.password, candidate_hash)
        if user is None or not user.hashed_password or not password_ok:
            raise PasswordErrorException()
        if not user.can_authenticate():
            raise UserInactiveException()

        pair = self._tokens.issue_pair(subject=str(user.id))
        logger.info("user_logged_in", user_id=user.id)
        return TokenPairDTO(
            access_token=pair.access_token,
            refresh_token=pair.refresh_token,
            token_type=pair.token_type,
            expires_in=pair.expires_in,
        )

    async def login_with_google(self, code: str) -> TokenPairDTO:
        """Exchange a Google authorization code for an identity and issue our token pair.

        授权码流：后端用 client_secret 去 Google token 端点换 id_token 并验签，得到可信身份。
        Google 永远返回邮箱，故走共用编排时不会触发占位邮箱合成。
        """
        if self._google is None:
            raise RuntimeError(
                "Google login not configured (GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET missing)"
            )

        google_identity = await self._google.exchange(code)  # InvalidTokenException on bad code
        identity = OAuthIdentity(
            sub=google_identity.sub,
            email=google_identity.email,
            email_verified=google_identity.email_verified,
            name=google_identity.name,
        )
        return await self._complete_oauth_login(GOOGLE_PROVIDER, identity)

    async def login_with_oauth(self, provider: str, code: str) -> TokenPairDTO:
        """Exchange a Feishu/Lark authorization code for an identity and issue our token pair.

        ``provider`` ∈ {feishu, lark}；其交换器在 composition root 按配置装配，缺失则未配置（fail-closed）。
        """
        exchanger = self._oauth_exchangers.get(provider)
        if exchanger is None:
            raise RuntimeError(f"OAuth login not configured for provider '{provider}'")

        identity = await exchanger.exchange(code)  # InvalidTokenException on bad code/token
        return await self._complete_oauth_login(provider, identity)

    async def _complete_oauth_login(self, provider: str, identity: OAuthIdentity) -> TokenPairDTO:
        """Shared find/link/create for any federated identity, then issue our token pair.

        Find/link/create policy:
        - existing oauth link (provider + sub) → that user;
        - else if email is verified and matches an existing user → link to it;
        - else create a new (password-less) user and link.
        Unverified emails never auto-link. 未验证邮箱也**不得写入 users.email**：
        否则后续同邮箱的 verified 登录会匹配到这条记录（预注册接管链），撞唯一
        约束还会泄露邮箱注册状态。无邮箱/未验证一律合成占位邮箱
        ``{sub}@{provider}.local``（满足非空+唯一，合成域不与真实邮箱冲突）。
        """
        async with self._uow_factory() as uow:
            user = await uow.user_repository.get_by_oauth(provider, identity.sub)
            if user is None:
                if identity.email_verified and identity.email:
                    user = await uow.user_repository.get_by_email(identity.email)
                if user is None:
                    domain_service = UserDomainService(uow.user_repository)
                    trusted_email = identity.email if identity.email_verified else None
                    email = trusted_email or f"{identity.sub}@{provider}.local"
                    username = await domain_service.derive_unique_username(email)
                    now = utcnow()
                    user = await uow.user_repository.create(
                        User(
                            id=None,
                            username=username,
                            email=email,
                            hashed_password=None,
                            full_name=identity.name,
                            created_at=now,
                            updated_at=now,
                        )
                    )
                await uow.user_repository.add_oauth_account(
                    OAuthAccount(
                        user_id=user.id,
                        provider=provider,
                        provider_sub=identity.sub,
                        email=identity.email,
                        created_at=utcnow(),
                    )
                )

        if not user.can_authenticate():
            raise UserInactiveException()

        pair = self._tokens.issue_pair(subject=str(user.id))
        logger.info("user_logged_in_oauth", user_id=user.id, provider=provider)
        return TokenPairDTO(
            access_token=pair.access_token,
            refresh_token=pair.refresh_token,
            token_type=pair.token_type,
            expires_in=pair.expires_in,
        )

    async def refresh(self, refresh_token: str) -> TokenPairDTO:
        """Exchange a valid refresh token for a new token pair."""
        subject = self._tokens.verify(refresh_token, expected_type="refresh")
        user = await self._load_authenticatable_user(subject)
        pair = self._tokens.issue_pair(subject=str(user.id))
        return TokenPairDTO(
            access_token=pair.access_token,
            refresh_token=pair.refresh_token,
            token_type=pair.token_type,
            expires_in=pair.expires_in,
        )

    async def get_current_user(self, access_token: str) -> UserDTO:
        """Resolve the user behind an access token (used by API dependency)."""
        subject = self._tokens.verify(access_token, expected_type="access")
        user = await self._load_authenticatable_user(subject)
        return UserDTO.model_validate(user)

    async def _load_authenticatable_user(self, subject: str) -> User:
        try:
            user_id = int(subject)
        except (TypeError, ValueError):
            raise InvalidTokenException("malformed subject")
        async with self._uow_factory(readonly=True) as uow:
            user = await uow.user_repository.get_by_id(user_id)
        if user is None:
            raise InvalidTokenException("unknown subject")
        if not user.can_authenticate():
            raise UserInactiveException()
        return user
