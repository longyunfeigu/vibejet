# input: SQLAlchemyDocumentRepository + 内存 SQLite（aiosqlite）
# output: 文档仓储原子认领（try_mark_parsing）行为测试
# owner: wanhua.gu
# pos: 后端测试 - 文档仓储条件更新并发语义验证；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Tests for SQLAlchemyDocumentRepository.try_mark_parsing (atomic claim)."""

from __future__ import annotations

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from application.utils.time import utcnow
from domain.document import Document
from infrastructure.models.document import DocumentModel
from infrastructure.repositories.document_repository import SQLAlchemyDocumentRepository


@asynccontextmanager
async def _session():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(DocumentModel.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as s:
            yield s
    finally:
        await engine.dispose()


async def _create_doc(repo: SQLAlchemyDocumentRepository, **overrides) -> Document:
    now = utcnow()
    defaults = {
        "id": None,
        "file_asset_id": 10,
        "status": "pending",
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return await repo.create(Document(**defaults))


async def test_try_mark_parsing_claims_failed_document_and_clears_errors() -> None:
    async with _session() as session:
        repo = SQLAlchemyDocumentRepository(session)
        doc = await _create_doc(
            repo, status="failed", error_code="old", error_message="old failure"
        )

        claimed = await repo.try_mark_parsing(doc.id)

        assert claimed is not None
        assert claimed.status == "parsing"
        assert claimed.error_code is None
        assert claimed.error_message is None


async def test_try_mark_parsing_rejects_second_claim() -> None:
    async with _session() as session:
        repo = SQLAlchemyDocumentRepository(session)
        doc = await _create_doc(repo)

        first = await repo.try_mark_parsing(doc.id)
        second = await repo.try_mark_parsing(doc.id)

        assert first is not None
        assert second is None  # 已在 parsing，条件 UPDATE 不命中


async def test_try_mark_parsing_rejects_soft_deleted() -> None:
    async with _session() as session:
        repo = SQLAlchemyDocumentRepository(session)
        doc = await _create_doc(repo, deleted_at=utcnow())

        assert await repo.try_mark_parsing(doc.id) is None


async def test_try_mark_parsing_rejects_missing() -> None:
    async with _session() as session:
        repo = SQLAlchemyDocumentRepository(session)
        assert await repo.try_mark_parsing(999) is None
