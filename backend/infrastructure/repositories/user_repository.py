# input: SQLAlchemy AsyncSession, UserModel ORM
# output: SQLAlchemyUserRepository 仓储实现
# owner: wanhua.gu
# pos: 基础设施层 - 用户仓储 SQLAlchemy 实现（软删过滤）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""SQLAlchemy-backed repository for users."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from domain.common.exceptions import (
    UserAlreadyExistsException,
    UsernameAlreadyExistsException,
    UserNotFoundException,
)
from domain.user.entity import User
from domain.user.oauth_account import OAuthAccount
from domain.user.repository import UserRepository
from infrastructure.models.user import OAuthAccountModel, UserModel
from infrastructure.repositories.base_repository import execute_targeted_update


class SQLAlchemyUserRepository(UserRepository):
    """Persist user aggregates using SQLAlchemy ORM."""

    model_class = UserModel

    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, model: UserModel) -> User:
        return User(
            id=model.id,
            username=model.username,
            email=model.email,
            hashed_password=model.hashed_password,
            full_name=model.full_name,
            is_active=model.is_active,
            is_superuser=model.is_superuser,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )

    async def create(self, user: User) -> User:
        model = UserModel(
            username=user.username,
            email=user.email,
            hashed_password=user.hashed_password,
            full_name=user.full_name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
            updated_at=user.updated_at,
            deleted_at=user.deleted_at,
        )
        self.session.add(model)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            # 应用层的唯一性预检在并发下存在 check-then-act 窗口；
            # 唯一索引兜底后在这里映射回域异常（409），而不是裸 500
            detail = str(exc.orig or exc)
            if "ix_users_username" in detail or "username" in detail:
                raise UsernameAlreadyExistsException(user.username) from exc
            raise UserAlreadyExistsException(user.email) from exc
        await self.session.refresh(model)
        return self._to_entity(model)

    async def update(self, user: User) -> User:
        # 改名/改邮箱撞唯一索引与 create 同映射
        try:
            await execute_targeted_update(
                self.session,
                UserModel,
                user.id,
                {
                    "username": user.username,
                    "email": user.email,
                    "hashed_password": user.hashed_password,
                    "full_name": user.full_name,
                    "is_active": user.is_active,
                    "is_superuser": user.is_superuser,
                    "updated_at": user.updated_at,
                    "deleted_at": user.deleted_at,
                },
                not_found=lambda: UserNotFoundException(str(user.id)),
            )
        except IntegrityError as exc:
            detail = str(exc.orig or exc)
            if "ix_users_username" in detail or "username" in detail:
                raise UsernameAlreadyExistsException(user.username) from exc
            raise UserAlreadyExistsException(user.email) from exc
        return user

    async def get_by_id(self, user_id: int) -> Optional[User]:
        return await self._get_one(UserModel.id == user_id)

    async def get_by_username(self, username: str) -> Optional[User]:
        return await self._get_one(UserModel.username == username)

    async def get_by_email(self, email: str) -> Optional[User]:
        return await self._get_one(UserModel.email == email)

    async def get_by_oauth(self, provider: str, provider_sub: str) -> Optional[User]:
        query = (
            select(UserModel)
            .join(OAuthAccountModel, OAuthAccountModel.user_id == UserModel.id)
            .where(
                OAuthAccountModel.provider == provider,
                OAuthAccountModel.provider_sub == provider_sub,
                UserModel.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def add_oauth_account(self, account: OAuthAccount) -> OAuthAccount:
        model = OAuthAccountModel(
            user_id=account.user_id,
            provider=account.provider,
            provider_sub=account.provider_sub,
            email=account.email,
            created_at=account.created_at,
        )
        self.session.add(model)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            # 唯一索引 (provider, provider_sub) 兜底并发链接竞争，映射回 409
            raise UserAlreadyExistsException(account.email or account.provider_sub) from exc
        await self.session.refresh(model)
        return OAuthAccount(
            id=model.id,
            user_id=model.user_id,
            provider=model.provider,
            provider_sub=model.provider_sub,
            email=model.email,
            created_at=model.created_at,
        )

    async def _get_one(self, *conditions) -> Optional[User]:
        query = select(UserModel).where(*conditions, UserModel.deleted_at.is_(None))
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
