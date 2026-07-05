# input: SQLAlchemy AsyncSession, AgentConfigModel ORM
# output: SQLAlchemyAgentConfigRepository 仓储实现
# owner: unknown
# pos: 基础设施层 - Agent 配置仓储 SQLAlchemy 实现；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""SQLAlchemy-backed repository for agent configurations."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from domain.conversation.entity import AgentConfig
from domain.conversation.exceptions import (
    AgentConfigNameExistsException,
    AgentConfigNotFoundException,
)
from domain.conversation.repository import AgentConfigRepository
from infrastructure.models.conversation import AgentConfigModel
from infrastructure.repositories.base_repository import (
    execute_targeted_delete,
    execute_targeted_update,
)


class SQLAlchemyAgentConfigRepository(AgentConfigRepository):
    """Persist agent config aggregates using SQLAlchemy ORM."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, model: AgentConfigModel) -> AgentConfig:
        return AgentConfig(
            id=model.id,
            name=model.name,
            system_prompt=model.system_prompt,
            model=model.model,
            temperature=model.temperature,
            max_tokens=model.max_tokens,
            metadata=dict(model.extra_metadata or {}),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def create(self, config: AgentConfig) -> AgentConfig:
        model = AgentConfigModel(
            name=config.name,
            system_prompt=config.system_prompt,
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            extra_metadata=config.metadata or {},
            created_at=config.created_at,
            updated_at=config.updated_at,
        )
        self.session.add(model)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            # 应用层同名预检在并发下存在 check-then-act 窗口；
            # 唯一索引 ix_agent_configs_name 兜底后映射回域异常（409），而不是裸 500
            raise AgentConfigNameExistsException(config.name) from exc
        await self.session.refresh(model)
        return self._to_entity(model)

    async def update(self, config: AgentConfig) -> AgentConfig:
        # 改名撞唯一索引同样映射为 409，与 create 一致
        try:
            await execute_targeted_update(
                self.session,
                AgentConfigModel,
                config.id,
                {
                    "name": config.name,
                    "system_prompt": config.system_prompt,
                    "model": config.model,
                    "temperature": config.temperature,
                    "max_tokens": config.max_tokens,
                    "extra_metadata": config.metadata or {},
                    "updated_at": config.updated_at,
                },
                not_found=lambda: AgentConfigNotFoundException(config.id),
            )
        except IntegrityError as exc:
            raise AgentConfigNameExistsException(config.name) from exc
        return config

    async def delete(self, config_id: int) -> None:
        await execute_targeted_delete(
            self.session,
            AgentConfigModel,
            config_id,
            not_found=lambda: AgentConfigNotFoundException(config_id),
        )

    async def get_by_id(self, config_id: int) -> Optional[AgentConfig]:
        result = await self.session.execute(
            select(AgentConfigModel).where(AgentConfigModel.id == config_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_name(self, name: str) -> Optional[AgentConfig]:
        result = await self.session.execute(
            select(AgentConfigModel).where(AgentConfigModel.name == name)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> list[AgentConfig]:
        query = (
            select(AgentConfigModel)
            .order_by(AgentConfigModel.created_at.desc(), AgentConfigModel.id.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count(self) -> int:
        query = select(func.count()).select_from(AgentConfigModel)
        result = await self.session.execute(query)
        return int(result.scalar() or 0)
