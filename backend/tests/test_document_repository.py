"""Tests for SQLAlchemyDocumentRepository.try_mark_parsing (atomic claim)."""

from __future__ import annotations

from application.utils.time import utcnow
from domain.document import Document
from infrastructure.repositories.document_repository import SQLAlchemyDocumentRepository


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


async def test_try_mark_parsing_claims_pending_and_clears_stale_errors(sqlite_session) -> None:
    async with sqlite_session() as session:
        repo = SQLAlchemyDocumentRepository(session)
        doc = await _create_doc(
            repo, status="pending", error_code="old", error_message="old failure"
        )

        claimed = await repo.try_mark_parsing(doc.id)

        assert claimed is not None
        assert claimed.status == "parsing"
        assert claimed.error_code is None
        assert claimed.error_message is None


async def test_try_mark_parsing_rejects_failed_without_reset(sqlite_session) -> None:
    """failed 必须先经 reparse 重置为 pending 才能再次认领。"""
    async with sqlite_session() as session:
        repo = SQLAlchemyDocumentRepository(session)
        doc = await _create_doc(repo, status="failed", error_code="x", error_message="x")

        assert await repo.try_mark_parsing(doc.id) is None


async def test_try_mark_parsing_rejects_second_claim(sqlite_session) -> None:
    async with sqlite_session() as session:
        repo = SQLAlchemyDocumentRepository(session)
        doc = await _create_doc(repo)

        first = await repo.try_mark_parsing(doc.id)
        second = await repo.try_mark_parsing(doc.id)

        assert first is not None
        assert second is None  # 已在 parsing，条件 UPDATE 不命中


async def test_try_mark_parsing_rejects_soft_deleted(sqlite_session) -> None:
    async with sqlite_session() as session:
        repo = SQLAlchemyDocumentRepository(session)
        doc = await _create_doc(repo, deleted_at=utcnow())

        assert await repo.try_mark_parsing(doc.id) is None


async def test_try_mark_parsing_rejects_missing(sqlite_session) -> None:
    async with sqlite_session() as session:
        repo = SQLAlchemyDocumentRepository(session)
        assert await repo.try_mark_parsing(999) is None


async def test_try_mark_parsing_rejects_ready_document(sqlite_session) -> None:
    """ready 不可直接认领：排队的重复任务在前序完成后必须认领失败（防重复计费）。"""
    async with sqlite_session() as session:
        repo = SQLAlchemyDocumentRepository(session)
        doc = await _create_doc(repo, status="ready", content_md="# done")

        assert await repo.try_mark_parsing(doc.id) is None


async def test_update_if_claimed_accepts_current_claim(sqlite_session) -> None:
    async with sqlite_session() as session:
        repo = SQLAlchemyDocumentRepository(session)
        doc = await _create_doc(repo)
        claimed = await repo.try_mark_parsing(doc.id)
        claimed_at = claimed.updated_at  # mark_ready 会 _touch，须先取认领 token

        claimed.mark_ready(content_md="# v1", parser="markitdown")
        ok = await repo.update_if_claimed(claimed, claimed_at=claimed_at)

        assert ok is True
        stored = await repo.get_by_id(doc.id)
        assert stored.status == "ready"
        assert stored.content_md == "# v1"


async def test_update_if_claimed_rejects_superseded_claim(sqlite_session) -> None:
    """僵尸 worker：stale 恢复 + 新任务重新认领后，旧认领的落盘必须被拒绝。"""
    async with sqlite_session() as session:
        repo = SQLAlchemyDocumentRepository(session)
        doc = await _create_doc(repo)

        old = await repo.try_mark_parsing(doc.id)
        old_claimed_at = old.updated_at

        # 模拟 stale 恢复：重置 pending 后被新任务再次认领（updated_at 改变）
        old_entity = await repo.get_by_id(doc.id)
        old_entity.status = "pending"
        await repo.update(old_entity)
        new = await repo.try_mark_parsing(doc.id)
        assert new is not None

        old.mark_ready(content_md="# zombie", parser="markitdown")
        assert await repo.update_if_claimed(old, claimed_at=old_claimed_at) is False

        stored = await repo.get_by_id(doc.id)
        assert stored.status == "parsing"  # 仍属于新任务
        assert stored.content_md is None
