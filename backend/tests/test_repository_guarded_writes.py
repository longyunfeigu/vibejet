"""Guarded single-statement writes that must not clobber concurrent changes.

- 会话活跃度刷新只写 updated_at、限未软删行：不覆盖并发 PATCH，不复活并发软删。
- 文件资产激活写守卫 deleted_at IS NULL：确认期间被并发删除的资产不被复活。

"并发方"用同库第二个 session 直接写库模拟（提交后，调用方手里的实体已过期）。
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from application.utils.time import utcnow
from domain.common.exceptions import FileAssetNotFoundException
from domain.conversation.entity import Conversation
from domain.conversation.exceptions import ConversationNotFoundException
from domain.file_asset.entity import FileAsset
from infrastructure.repositories.conversation_repository import SQLAlchemyConversationRepository
from infrastructure.repositories.file_asset_repository import SQLAlchemyFileAssetRepository


async def test_touch_activity_bumps_only_updated_at(sqlite_engine) -> None:
    async with sqlite_engine() as engine:
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        created_at = utcnow() - timedelta(hours=1)
        async with sessions() as s:
            repo = SQLAlchemyConversationRepository(s)
            conv = await repo.create(
                Conversation(title="old", owner_id=1, created_at=created_at, updated_at=created_at)
            )
            await s.commit()

        # 并发 PATCH 已提交改名；聊天路径随后刷新活跃度
        async with sessions() as s:
            repo = SQLAlchemyConversationRepository(s)
            patched = await repo.get_by_id(conv.id)
            patched.update_title("renamed-by-patch")
            await repo.update(patched)
            await s.commit()

        bump_at = utcnow()
        async with sessions() as s:
            await SQLAlchemyConversationRepository(s).touch_activity(conv.id, at=bump_at)
            await s.commit()

        async with sessions() as s:
            fetched = await SQLAlchemyConversationRepository(s).get_by_id(conv.id)
        assert fetched is not None
        assert fetched.title == "renamed-by-patch"
        assert fetched.updated_at == bump_at


async def test_touch_activity_does_not_resurrect_soft_deleted(sqlite_engine) -> None:
    async with sqlite_engine() as engine:
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as s:
            repo = SQLAlchemyConversationRepository(s)
            conv = await repo.create(Conversation(title="t", owner_id=1))
            conv.soft_delete()
            await repo.update(conv)
            await s.commit()

        async with sessions() as s:
            with pytest.raises(ConversationNotFoundException):
                await SQLAlchemyConversationRepository(s).touch_activity(conv.id, at=utcnow())

        async with sessions() as s:
            repo = SQLAlchemyConversationRepository(s)
            assert await repo.get_by_id(conv.id) is None
            still_deleted = await repo.get_by_id(conv.id, include_deleted=True)
        assert still_deleted is not None and still_deleted.deleted_at is not None


async def test_file_asset_update_if_not_deleted_refuses_deleted_row(sqlite_engine) -> None:
    async with sqlite_engine() as engine:
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        now = utcnow()
        async with sessions() as s:
            asset = await SQLAlchemyFileAssetRepository(s).create(
                FileAsset(owner_id=1, key="uploads/a.bin", created_at=now, updated_at=now)
            )
            await s.commit()

        # 确认方已读到 pending 实体……
        async with sessions() as s:
            stale = await SQLAlchemyFileAssetRepository(s).get_by_id(asset.id)
        # ……此时并发删除提交
        async with sessions() as s:
            repo = SQLAlchemyFileAssetRepository(s)
            victim = await repo.get_by_id(asset.id)
            victim.mark_deleted()
            await repo.update(victim)
            await s.commit()

        stale.mark_active()
        async with sessions() as s:
            with pytest.raises(FileAssetNotFoundException):
                await SQLAlchemyFileAssetRepository(s).update_if_not_deleted(stale)

        async with sessions() as s:
            row = await SQLAlchemyFileAssetRepository(s).get_by_id(asset.id, include_deleted=True)
        assert row is not None and row.status == "deleted" and row.deleted_at is not None


async def test_file_asset_update_if_not_deleted_writes_live_row(sqlite_engine) -> None:
    async with sqlite_engine() as engine:
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        now = utcnow()
        async with sessions() as s:
            repo = SQLAlchemyFileAssetRepository(s)
            asset = await repo.create(
                FileAsset(owner_id=1, key="uploads/b.bin", created_at=now, updated_at=now)
            )
            asset.update_object_metadata(size=42, etag="e")
            asset.mark_active()
            await repo.update_if_not_deleted(asset)
            await s.commit()

        async with sessions() as s:
            row = await SQLAlchemyFileAssetRepository(s).get_by_id(asset.id)
        assert row is not None and row.status == "active" and row.size == 42


async def test_conversation_update_does_not_resurrect_concurrent_soft_delete(sqlite_engine) -> None:
    async with sqlite_engine() as engine:
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as s:
            conv = await SQLAlchemyConversationRepository(s).create(
                Conversation(title="t", owner_id=1)
            )
            await s.commit()

        # PATCH 先读到未删除的会话……
        async with sessions() as s:
            stale = await SQLAlchemyConversationRepository(s).get_by_id(conv.id)
        assert stale is not None

        # ……期间并发 DELETE 已提交
        async with sessions() as s:
            repo = SQLAlchemyConversationRepository(s)
            current = await repo.get_by_id(conv.id)
            current.soft_delete()
            await repo.update(current)
            await s.commit()

        # PATCH 带着过期实体整行回写：必须 404，而不是把 deleted_at 写回 NULL
        stale.update_title("patched")
        async with sessions() as s:
            with pytest.raises(ConversationNotFoundException):
                await SQLAlchemyConversationRepository(s).update(stale)

        async with sessions() as s:
            assert await SQLAlchemyConversationRepository(s).get_by_id(conv.id) is None
