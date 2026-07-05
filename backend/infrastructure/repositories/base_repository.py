"""SQLAlchemy base repository implementation."""

from __future__ import annotations

from typing import Any, Callable, Generic, Optional, Type, TypeVar

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from domain.common.exceptions import BusinessException
from domain.common.repository import BaseRepository

EntityT = TypeVar("EntityT")
ModelT = TypeVar("ModelT")
IdT = TypeVar("IdT")


async def execute_targeted_update(
    session: AsyncSession,
    model_class: Any,
    entity_id: Any,
    values: dict[str, Any],
    *,
    not_found: Callable[[], BusinessException],
) -> None:
    """定向 Core UPDATE（单往返）——全仓写路径的唯一实现，具体仓储不要另写 DML。

    调用方持有的实体即待写入状态（expire_on_commit=False），无需先 SELECT
    再改再 refresh。``values`` 不应包含主键与 created_at。
    synchronize_session=False：同一 session 中已加载的同行 ORM 模型不会被同步，
    调用方持有的领域实体才是权威状态。行不存在（rowcount 0）→ 抛 ``not_found()``。
    """
    result = await session.execute(
        update(model_class)
        .where(model_class.id == entity_id)
        .values(**values)
        .execution_options(synchronize_session=False)
    )
    if (result.rowcount or 0) == 0:
        raise not_found()


async def execute_targeted_delete(
    session: AsyncSession,
    model_class: Any,
    entity_id: Any,
    *,
    not_found: Callable[[], BusinessException],
) -> None:
    """定向 Core DELETE（单往返）：子表清理由数据库外键 ondelete 承担（模型无 ORM 级联）。"""
    result = await session.execute(
        delete(model_class)
        .where(model_class.id == entity_id)
        .execution_options(synchronize_session=False)
    )
    if (result.rowcount or 0) == 0:
        raise not_found()


class SQLAlchemyBaseRepository(BaseRepository[EntityT, IdT], Generic[EntityT, ModelT, IdT]):
    model_class: Type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_entity(self, model: ModelT) -> EntityT:
        raise NotImplementedError

    def _to_model(self, entity: EntityT) -> ModelT:
        raise NotImplementedError

    def _update_values(self, entity: EntityT) -> dict[str, Any]:
        """``update()`` 写入的列值（不含主键与 created_at）。"""
        raise NotImplementedError

    def _not_found_exception(self, identifier: IdT) -> BusinessException:
        raise NotImplementedError

    def _apply_filters(self, query: Any, **kwargs: Any) -> Any:
        return query

    def _default_order(self, query: Any) -> Any:
        return query

    def _raise_not_found(self, identifier: IdT) -> None:
        exc = self._not_found_exception(identifier)
        if not isinstance(exc, BusinessException):
            raise TypeError("_not_found_exception must return BusinessException")
        raise exc

    async def create(self, entity: EntityT) -> EntityT:
        model = self._to_model(entity)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def update(self, entity: EntityT) -> EntityT:
        identifier = getattr(entity, "id", None)
        if identifier is None:
            self._raise_not_found(identifier)
        await execute_targeted_update(
            self.session,
            self.model_class,
            identifier,
            self._update_values(entity),
            not_found=lambda: self._not_found_exception(identifier),
        )
        return entity

    async def delete(self, entity_id: IdT) -> None:
        await execute_targeted_delete(
            self.session,
            self.model_class,
            entity_id,
            not_found=lambda: self._not_found_exception(entity_id),
        )

    async def get_by_id(self, entity_id: IdT) -> Optional[EntityT]:
        result = await self.session.execute(
            select(self.model_class).where(self.model_class.id == entity_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list(self, *, skip: int = 0, limit: int = 20, **filters: Any) -> list[EntityT]:
        query = select(self.model_class)
        query = self._apply_filters(query, **filters)
        query = self._default_order(query)
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models]

    async def count(self, **filters: Any) -> int:
        query = select(func.count()).select_from(self.model_class)
        query = self._apply_filters(query, **filters)
        result = await self.session.execute(query)
        return int(result.scalar() or 0)
