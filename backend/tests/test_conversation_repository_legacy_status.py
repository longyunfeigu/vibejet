"""旧版软删写过 conversations.status='archived'；实体现只认 'active'。

Given 库里有 status='archived' + deleted_at 的遗留软删行
When 用 include_deleted=True 加载（软删幂等/删除判定路径）
Then 正常映射为实体（status='active'，删除态由 deleted_at 承载），而不是抛 DomainValidationException。
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import async_sessionmaker

from application.utils.time import utcnow
from infrastructure.models.conversation import ConversationModel
from infrastructure.repositories.conversation_repository import SQLAlchemyConversationRepository


async def test_legacy_archived_soft_deleted_row_loads_with_include_deleted(sqlite_engine) -> None:
    async with sqlite_engine() as engine:
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        deleted_at = utcnow()
        async with sessions() as s:
            row = ConversationModel(
                title="legacy", owner_id=1, status="archived", deleted_at=deleted_at
            )
            s.add(row)
            await s.commit()
            row_id = row.id

        async with sessions() as s:
            repo = SQLAlchemyConversationRepository(s)
            assert await repo.get_by_id(row_id) is None
            loaded = await repo.get_by_id(row_id, include_deleted=True)

        assert loaded is not None
        assert loaded.status == "active"
        assert loaded.deleted_at == deleted_at
        assert loaded.is_deleted()
