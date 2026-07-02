# input: SQLAlchemyAgentConfigRepository + 内存 SQLite（aiosqlite）
# output: AgentConfig 仓储唯一名冲突（create/update 撞 ix_agent_configs_name → 域异常 409）测试
# pos: 后端测试 - AgentConfig 仓储唯一约束兜底验证；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Tests for SQLAlchemyAgentConfigRepository unique-name conflict handling."""

from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from application.utils.time import utcnow
from domain.conversation.entity import AgentConfig
from domain.conversation.exceptions import AgentConfigNameExistsException
from infrastructure.models import Base
from infrastructure.repositories.agent_config_repository import SQLAlchemyAgentConfigRepository


@asynccontextmanager
async def _session():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as s:
            yield s
    finally:
        await engine.dispose()


def _config(name: str) -> AgentConfig:
    now = utcnow()
    return AgentConfig(id=None, name=name, created_at=now, updated_at=now)


async def test_create_duplicate_name_raises_domain_conflict() -> None:
    """绕过应用层预检直接写库（模拟并发窗口），唯一索引冲突应映射为域异常而非裸 IntegrityError。"""
    async with _session() as session:
        repo = SQLAlchemyAgentConfigRepository(session)
        await repo.create(_config("assistant"))

        with pytest.raises(AgentConfigNameExistsException):
            await repo.create(_config("assistant"))


async def test_rename_to_existing_name_raises_domain_conflict() -> None:
    async with _session() as session:
        repo = SQLAlchemyAgentConfigRepository(session)
        await repo.create(_config("assistant"))
        other = await repo.create(_config("reviewer"))

        other.rename("assistant")
        with pytest.raises(AgentConfigNameExistsException):
            await repo.update(other)
