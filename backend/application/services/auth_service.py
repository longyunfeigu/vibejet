# input: AuthUnitOfWork, PasswordHasher/TokenProvider 端口, User 领域实体
# output: AuthApplicationService 注册/登录/刷新/当前用户用例编排
# owner: wanhua.gu
# pos: 应用层服务 - 认证用例编排（注册→哈希入库；登录→校验→签发令牌对）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Application service for authentication workflows."""

from __future__ import annotations

from typing import Callable, Protocol

from application.dto import LoginRequestDTO, RegisterRequestDTO, TokenPairDTO, UserDTO
from application.ports.security import PasswordHasher, TokenProvider
from application.utils.time import utcnow
from core.logging_config import get_logger
from domain.common.exceptions import (
    InvalidTokenException,
    PasswordErrorException,
    UserInactiveException,
)
from domain.user.entity import User
from domain.user.repository import UserRepository
from domain.user.service import UserDomainService

logger = get_logger(__name__)


class AuthUnitOfWork(Protocol):
    user_repository: UserRepository

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
    ) -> None:
        self._uow_factory = uow_factory
        self._hasher = password_hasher
        self._tokens = token_provider

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
            await uow.commit()

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

        if user is None or not self._hasher.verify(dto.password, user.hashed_password):
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
