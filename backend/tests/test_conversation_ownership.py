# input: Conversation 实体/仓储 + 异常处理器 + 会话服务/路由（内存 sqlite + fake + FastAPI test app）
# output: Epic-1 Story 1.1/1.2 会话归属验收测试
# pos: 后端测试 - conversations 归属地基与端点闭环验证；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Ownership tests for the conversation aggregate (Epic 1, Story 1.1 + 1.2).

覆盖：实体 owner 字段与 belongs_to、仓储 owner 过滤、遗留 NULL 行语义、
CONVERSATION_NOT_FOUND / DOCUMENT_NOT_FOUND 的 404 渲染。
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from core.exceptions import register_exception_handlers
from domain.conversation.entity import Conversation
from domain.conversation.exceptions import ConversationNotFoundException
from domain.document.exceptions import DocumentNotFoundException
from infrastructure.models.conversation import ConversationModel
from infrastructure.repositories.conversation_repository import (
    SQLAlchemyConversationRepository,
)


# ---------------------------------------------------------------------------
# Story 1.1 — entity
# ---------------------------------------------------------------------------


def test_entity_owner_id_and_belongs_to() -> None:
    conv = Conversation(id=1, title="t", owner_id=7)
    assert conv.belongs_to(7)
    assert not conv.belongs_to(8)


def test_entity_legacy_null_owner_belongs_to_nobody() -> None:
    conv = Conversation(id=1, title="t")
    assert conv.owner_id is None
    assert not conv.belongs_to(7)


# ---------------------------------------------------------------------------
# Story 1.1 — repository owner filter (in-memory sqlite)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _session():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(ConversationModel.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


async def _seed(repo: SQLAlchemyConversationRepository) -> None:
    await repo.create(Conversation(title="a-1", owner_id=1))
    await repo.create(Conversation(title="a-2", owner_id=1))
    await repo.create(Conversation(title="b-1", owner_id=2))
    await repo.create(Conversation(title="orphan", owner_id=None))


async def test_repo_filter_by_owner() -> None:
    async with _session() as session:
        repo = SQLAlchemyConversationRepository(session)
        await _seed(repo)

        rows = await repo.list(owner_id=1, skip=0, limit=20)
        assert {c.title for c in rows} == {"a-1", "a-2"}
        assert all(c.owner_id == 1 for c in rows)
        assert await repo.count(owner_id=1) == 2
        assert await repo.count(owner_id=2) == 1


async def test_repo_legacy_null_rows_match_no_owner() -> None:
    async with _session() as session:
        repo = SQLAlchemyConversationRepository(session)
        await _seed(repo)

        for owner in (1, 2, 999):
            rows = await repo.list(owner_id=owner, skip=0, limit=20)
            assert "orphan" not in {c.title for c in rows}


async def test_repo_no_filter_keeps_existing_behaviour() -> None:
    async with _session() as session:
        repo = SQLAlchemyConversationRepository(session)
        await _seed(repo)

        rows = await repo.list(skip=0, limit=20)
        assert len(rows) == 4
        assert await repo.count() == 4


async def test_repo_roundtrips_owner_id() -> None:
    async with _session() as session:
        repo = SQLAlchemyConversationRepository(session)
        created = await repo.create(Conversation(title="mine", owner_id=42))
        assert created.owner_id == 42

        fetched = await repo.get_by_id(created.id)
        assert fetched is not None and fetched.owner_id == 42

        fetched.update_title("renamed")
        updated = await repo.update(fetched)
        assert updated.owner_id == 42


# ---------------------------------------------------------------------------
# Story 1.1 — not-found business codes render as HTTP 404 (was default 400)
# ---------------------------------------------------------------------------


def _error_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom/conversation")
    async def boom_conversation():
        raise ConversationNotFoundException(1)

    @app.get("/boom/document")
    async def boom_document():
        raise DocumentNotFoundException(1)

    return app


@pytest.mark.asyncio
async def test_conversation_not_found_404() -> None:
    async with AsyncClient(app=_error_app(), base_url="http://test") as client:
        resp = await client.get("/boom/conversation")
    assert resp.status_code == 404
    assert resp.json()["error"]["message_key"] == "conversation.not_found"


@pytest.mark.asyncio
async def test_document_not_found_404() -> None:
    async with AsyncClient(app=_error_app(), base_url="http://test") as client:
        resp = await client.get("/boom/document")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Story 1.2 — service-level ownership（fake UoW，套 test_chat_service_stream 模式）
# ---------------------------------------------------------------------------


class _FakeConversationRepo:
    def __init__(self):
        self._items: dict[int, Conversation] = {}
        self._next_id = 1

    async def create(self, conversation: Conversation) -> Conversation:
        conversation.id = self._next_id
        self._next_id += 1
        self._items[conversation.id] = conversation
        return conversation

    async def update(self, conversation: Conversation) -> Conversation:
        self._items[conversation.id] = conversation
        return conversation

    async def get_by_id(self, conversation_id: int, *, include_deleted: bool = False):
        conv = self._items.get(conversation_id)
        if conv is None:
            return None
        if not include_deleted and conv.deleted_at is not None:
            return None
        return conv

    async def list(self, *, owner_id=None, status=None, skip=0, limit=20):
        rows = [
            c
            for c in self._items.values()
            if c.deleted_at is None
            and (owner_id is None or c.owner_id == owner_id)
            and (status is None or c.status == status)
        ]
        return rows[skip : skip + limit]

    async def count(self, *, owner_id=None, status=None):
        return len(await self.list(owner_id=owner_id, status=status, limit=10**9))


class _FakeMessageRepo:
    async def list_by_conversation(self, conversation_id, *, skip=0, limit=100):
        return []

    async def count_by_conversation(self, conversation_id):
        return 0


class _FakeRunRepo:
    async def list_by_conversation(self, conversation_id, *, skip=0, limit=50):
        return []


class _FakeUoW:
    def __init__(self, conv_repo: _FakeConversationRepo):
        self.conversation_repository = conv_repo
        self.message_repository = _FakeMessageRepo()
        self.run_repository = _FakeRunRepo()

    def __call__(self, **kwargs):  # 兼容 uow_factory(readonly=True) 调用形式
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def commit(self):
        return None


def _conv_service():
    from application.services.conversation_service import ConversationApplicationService

    repo = _FakeConversationRepo()
    uow = _FakeUoW(repo)
    return ConversationApplicationService(uow_factory=uow), repo


def _create_dto(title="t"):
    from application.dto import CreateConversationDTO

    return CreateConversationDTO(title=title)


async def test_service_create_sets_owner_and_owner_full_access() -> None:
    service, _ = _conv_service()
    created = await service.create_conversation(_create_dto(), owner_id=1)

    got = await service.get_conversation(created.id, owner_id=1)
    assert got.id == created.id

    from application.dto import UpdateConversationDTO

    updated = await service.update_conversation(
        created.id, UpdateConversationDTO(title="new"), owner_id=1
    )
    assert updated.title == "new"

    messages, total = await service.list_messages(created.id, owner_id=1)
    assert (messages, total) == ([], 0)
    assert await service.list_runs(created.id, owner_id=1) == []

    deleted = await service.delete_conversation(created.id, owner_id=1)
    assert deleted.status == "archived"


async def test_service_list_scoped_by_owner() -> None:
    service, _ = _conv_service()
    await service.create_conversation(_create_dto("mine-1"), owner_id=1)
    await service.create_conversation(_create_dto("mine-2"), owner_id=1)
    await service.create_conversation(_create_dto("theirs"), owner_id=2)

    items, total = await service.list_conversations(owner_id=1)
    assert total == 2
    assert {c.title for c in items} == {"mine-1", "mine-2"}


async def test_service_non_owner_404_on_all_reads_and_writes() -> None:
    service, _ = _conv_service()
    created = await service.create_conversation(_create_dto(), owner_id=1)

    from application.dto import UpdateConversationDTO

    with pytest.raises(ConversationNotFoundException):
        await service.get_conversation(created.id, owner_id=2)
    with pytest.raises(ConversationNotFoundException):
        await service.update_conversation(
            created.id, UpdateConversationDTO(title="x"), owner_id=2
        )
    with pytest.raises(ConversationNotFoundException):
        await service.delete_conversation(created.id, owner_id=2)
    with pytest.raises(ConversationNotFoundException):
        await service.list_messages(created.id, owner_id=2)
    with pytest.raises(ConversationNotFoundException):
        await service.list_runs(created.id, owner_id=2)


async def test_service_missing_id_same_404_as_non_owner() -> None:
    service, _ = _conv_service()
    with pytest.raises(ConversationNotFoundException):
        await service.get_conversation(999, owner_id=1)


# ---------------------------------------------------------------------------
# Story 1.2 — route wiring（真实路由 + 覆盖 service/current_user 依赖）
# ---------------------------------------------------------------------------


def _routes_app(service) -> FastAPI:
    from api.dependencies import get_conversation_service, get_current_user
    from api.routes.conversations import router as conversations_router
    from application.dto import UserDTO

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(conversations_router, prefix="/api/v1")
    app.dependency_overrides[get_conversation_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: UserDTO(
        id=2, username="bob", email="bob@example.com"
    )
    return app


@pytest.mark.asyncio
async def test_routes_pass_current_user_as_owner() -> None:
    service, repo = _conv_service()
    # 用户 1 的会话；路由的 current_user 是用户 2
    owned_by_other = await service.create_conversation(_create_dto("alice"), owner_id=1)

    app = _routes_app(service)
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 越权详情 → 404
        resp = await client.get(f"/api/v1/conversations/{owned_by_other.id}")
        assert resp.status_code == 404
        # 列表只见自己的（用户 2 现在没有会话）
        resp = await client.get("/api/v1/conversations")
        assert resp.status_code == 200
        assert resp.json()["data"]["total"] == 0
        # 创建会话 → owner 写入 current_user(2)
        resp = await client.post("/api/v1/conversations", json={"title": "bob's"})
        assert resp.status_code in (200, 201)
        created_id = resp.json()["data"]["id"]
        assert repo._items[created_id].owner_id == 2
