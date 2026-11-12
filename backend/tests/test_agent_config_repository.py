"""Tests for SQLAlchemyAgentConfigRepository unique-name conflict handling."""

from __future__ import annotations

import pytest

from application.utils.time import utcnow
from domain.conversation.entity import AgentConfig
from domain.conversation.exceptions import AgentConfigNameExistsException
from infrastructure.repositories.agent_config_repository import SQLAlchemyAgentConfigRepository


def _config(name: str) -> AgentConfig:
    now = utcnow()
    return AgentConfig(id=None, name=name, created_at=now, updated_at=now)


async def test_create_duplicate_name_raises_domain_conflict(sqlite_session) -> None:
    """绕过应用层预检直接写库（模拟并发窗口），唯一索引冲突应映射为域异常而非裸 IntegrityError。"""
    async with sqlite_session() as session:
        repo = SQLAlchemyAgentConfigRepository(session)
        await repo.create(_config("assistant"))

        with pytest.raises(AgentConfigNameExistsException):
            await repo.create(_config("assistant"))


async def test_rename_to_existing_name_raises_domain_conflict(sqlite_session) -> None:
    async with sqlite_session() as session:
        repo = SQLAlchemyAgentConfigRepository(session)
        await repo.create(_config("assistant"))
        other = await repo.create(_config("reviewer"))

        other.rename("assistant")
        with pytest.raises(AgentConfigNameExistsException):
            await repo.update(other)
