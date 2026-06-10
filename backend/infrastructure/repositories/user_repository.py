# input: SQLAlchemy AsyncSession, UserModel ORM
# output: SQLAlchemyUserRepository 仓储实现
# owner: wanhua.gu
# pos: 基础设施层 - 用户仓储 SQLAlchemy 实现（软删过滤）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""SQLAlchemy-backed repository for users."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.common.exceptions import UserNotFoundException
from domain.user.entity import User
from domain.user.repository import UserRepository
from infrastructure.models.user import UserModel


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
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def update(self, user: User) -> User:
        result = await self.session.execute(select(UserModel).where(UserModel.id == user.id))
        model = result.scalar_one_or_none()
        if model is None:
            raise UserNotFoundException(str(user.id))

        model.username = user.username
        model.email = user.email
        model.hashed_password = user.hashed_password
        model.full_name = user.full_name
        model.is_active = user.is_active
        model.is_superuser = user.is_superuser
        model.updated_at = user.updated_at
        model.deleted_at = user.deleted_at

        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def get_by_id(self, user_id: int) -> Optional[User]:
        return await self._get_one(UserModel.id == user_id)

    async def get_by_username(self, username: str) -> Optional[User]:
        return await self._get_one(UserModel.username == username)

    async def get_by_email(self, email: str) -> Optional[User]:
        return await self._get_one(UserModel.email == email)

    async def _get_one(self, *conditions) -> Optional[User]:
        query = select(UserModel).where(*conditions, UserModel.deleted_at.is_(None))
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
