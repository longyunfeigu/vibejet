# input: 内存 SQLite 引擎 + conversation/document 仓储 + SQL 语句捕获
# output: 写路径单往返与列表 defer 的回归测试（PERF QE-2/QE-1/QE-3）
# pos: 后端测试 - 仓储 SQL 往返数回归；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Repository round-trip regression tests.

update()/delete() 必须是单条定向 DML（不得先 SELECT 再改再 refresh）；
文档列表不得加载 content_md；try_mark_parsing 用 RETURNING 一次往返完成认领。
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import pytest

from application.utils.time import utcnow
from domain.common.exceptions import FileAssetKeyConflictException
from domain.conversation.entity import Conversation
from domain.document import Document
from domain.file_asset.entity import FileAsset
from infrastructure.models import Base
from infrastructure.repositories.conversation_repository import SQLAlchemyConversationRepository
from infrastructure.repositories.document_repository import SQLAlchemyDocumentRepository
from infrastructure.repositories.file_asset_repository import SQLAlchemyFileAssetRepository


@asynccontextmanager
async def _session_with_statements() -> AsyncIterator[tuple[AsyncSession, list[str]]]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        statements: list[str] = []

        @event.listens_for(engine.sync_engine, "before_cursor_execute")
        def _capture(conn, cursor, statement, parameters, context, executemany) -> None:
            statements.append(statement.strip())

        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            yield session, statements
    finally:
        await engine.dispose()


def _verbs(statements: list[str]) -> list[str]:
    return [s.split()[0].upper() for s in statements]


def _pending_document(now) -> Document:
    return Document(
        id=None,
        owner_id=1,
        file_asset_id=1,
        title="d",
        source_filename="d.pdf",
        content_type="application/pdf",
        parser=None,
        status="pending",
        content_md=None,
        error_code=None,
        error_message=None,
        metadata={},
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )


async def test_conversation_update_is_single_statement() -> None:
    async with _session_with_statements() as (session, statements):
        repo = SQLAlchemyConversationRepository(session)
        now = utcnow()
        conv = await repo.create(
            Conversation(
                id=None, title="t", status="active", owner_id=1, created_at=now, updated_at=now
            )
        )

        statements.clear()
        conv.title = "renamed"
        updated = await repo.update(conv)

        assert updated.title == "renamed"
        assert _verbs(statements) == ["UPDATE"], f"expected single UPDATE, got: {statements}"

        # 写入确实生效（重新读取校验，不依赖返回值）
        fetched = await repo.get_by_id(conv.id)
        assert fetched is not None and fetched.title == "renamed"


async def test_document_claim_uses_single_returning_statement() -> None:
    async with _session_with_statements() as (session, statements):
        repo = SQLAlchemyDocumentRepository(session)
        doc = await repo.create(_pending_document(utcnow()))

        statements.clear()
        claimed = await repo.try_mark_parsing(doc.id)

        assert claimed is not None and claimed.status == "parsing"
        assert _verbs(statements) == [
            "UPDATE"
        ], f"expected single UPDATE..RETURNING, got: {statements}"

        # 已认领（parsing）后再次认领必须失败
        assert await repo.try_mark_parsing(doc.id) is None


async def test_file_asset_duplicate_key_maps_to_domain_conflict() -> None:
    """并发同 key 插入撞 uq_file_assets_key 必须映射为域冲突，而不是裸 IntegrityError/500。"""
    async with _session_with_statements() as (session, _):
        repo = SQLAlchemyFileAssetRepository(session)
        now = utcnow()

        def _asset() -> FileAsset:
            return FileAsset(
                id=None, owner_id=1, key="uploads/dup.bin", created_at=now, updated_at=now
            )

        await repo.create(_asset())
        with pytest.raises(FileAssetKeyConflictException):
            await repo.create(_asset())


async def test_document_list_defers_content_md() -> None:
    async with _session_with_statements() as (session, statements):
        repo = SQLAlchemyDocumentRepository(session)
        now = utcnow()
        ready = _pending_document(now)
        ready.status = "ready"
        ready.parser = "markitdown"
        ready.content_md = "# big markdown body"
        doc = await repo.create(ready)

        statements.clear()
        listed = await repo.list(owner_id=1)

        assert len(listed) == 1
        # 列表实体不携带正文，且 SQL 未选取 content_md 列
        assert listed[0].content_md is None
        select_sql = statements[0].lower()
        assert "content_md" not in select_sql, f"list query still selects content_md: {select_sql}"

        # 详情路径仍加载完整正文
        full = await repo.get_by_id(doc.id)
        assert full is not None and full.content_md == "# big markdown body"
