from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest
from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from domain.common.entity import BaseEntity
from domain.common.exceptions import BusinessException
from infrastructure.repositories.base_repository import SQLAlchemyBaseRepository
from shared.codes import BusinessCode


class _TagBase(DeclarativeBase):
    pass


class TagModel(_TagBase):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


@dataclass
class Tag(BaseEntity[int]):
    name: str = ""


class TagRepository(SQLAlchemyBaseRepository[Tag, TagModel, int]):
    model_class = TagModel

    def _to_entity(self, model: TagModel) -> Tag:
        return Tag(
            id=model.id,
            name=model.name,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )

    def _to_model(self, entity: Tag) -> TagModel:
        return TagModel(
            id=entity.id,
            name=entity.name,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
        )

    def _update_values(self, entity: Tag) -> dict:
        return {
            "name": entity.name,
            "updated_at": entity.updated_at,
            "deleted_at": entity.deleted_at,
        }

    def _not_found_exception(self, identifier: int) -> BusinessException:
        return BusinessException(
            code=BusinessCode.NOT_FOUND,
            message="Tag not found",
            error_type="TagNotFound",
            details={"id": identifier},
            message_key="tag.not_found",
        )


async def test_sqlalchemy_base_repository_crud(sqlite_session) -> None:
    async with sqlite_session(_TagBase.metadata) as session:
        repo = TagRepository(session)
        now = datetime.now(timezone.utc)
        created = await repo.create(Tag(name="alpha", created_at=now, updated_at=now))
        assert created.id is not None

        created.name = "beta"
        updated = await repo.update(created)
        assert updated.name == "beta"

        fetched = await repo.get_by_id(updated.id)
        assert fetched is not None
        assert fetched.name == "beta"

        await repo.create(Tag(name="gamma"))
        items = await repo.list(skip=0, limit=10)
        total = await repo.count()
        assert total == len(items) == 2

        await repo.delete(updated.id)
        missing = await repo.get_by_id(updated.id)
        assert missing is None


async def test_sqlalchemy_base_repository_not_found(sqlite_session) -> None:
    async with sqlite_session(_TagBase.metadata) as session:
        repo = TagRepository(session)
        with pytest.raises(BusinessException):
            await repo.delete(999)
