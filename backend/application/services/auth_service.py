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
        async with self._uow_factory() as uow:
            domain_service = UserDomainService(uow.user_repository)
            await domain_service.ensure_username_available(dto.username)
            await domain_service.ensure_email_available(dto.email)

            now = utcnow()
            user = User(
                id=None,
                username=dto.username,
                email=dto.email,
                hashed_password=self._hasher.hash(dto.password),
                full_name=dto.full_name,
                created_at=now,
                updated_at=now,
            )
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

        # 联合登录用户可能没有本地密码（hashed_password 为空）→ 视作凭据错误
        if (
            user is None
            or not user.hashed_password
            or not self._hasher.verify(dto.password, user.hashed_password)
        ):
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
        Unverified emails never auto-link. 无邮箱时合成占位邮箱 ``{sub}@{provider}.local``
        以满足 users.email 非空+唯一约束（合成域不与真实邮箱冲突）。
        """
        async with self._uow_factory() as uow:
            user = await uow.user_repository.get_by_oauth(provider, identity.sub)
            if user is None:
                if identity.email_verified and identity.email:
                    user = await uow.user_repository.get_by_email(identity.email)
                if user is None:
                    domain_service = UserDomainService(uow.user_repository)
                    email = identity.email or f"{identity.sub}@{provider}.local"
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
