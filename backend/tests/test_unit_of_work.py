# input: SQLAlchemyUnitOfWork + 内存 SQLite（aiosqlite）
# output: UoW 事务语义行为测试（自动提交/回滚/只读保护/懒仓储）
# pos: 后端测试 - UoW 干净退出自动 commit、异常回滚、readonly 写保护语义验证；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Tests for SQLAlchemyUnitOfWork transaction semantics.

验收标准（对应 AbstractUnitOfWork docstring）：
- Given 非只读 UoW，When 块内写入且干净退出（不显式 commit），Then 写入落库
- Given 非只读 UoW，When 块内抛异常，Then 写入回滚
- Given 中途显式 commit，When 之后继续写入并干净退出，Then 两批写入都落库
- Given 只读 UoW，When 显式调用 commit()，Then 抛 RuntimeError
- Given 只读 UoW，When 发生任何写入（ORM flush 或 Core INSERT/UPDATE/DELETE），
  Then 立即抛 RuntimeError（不静默丢弃）
- Given 未进入的 UoW，When 访问仓储，Then 抛 RuntimeError
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from application.utils.time import utcnow
from domain.document import Document
from infrastructure.models.document import DocumentModel
from infrastructure.unit_of_work import SQLAlchemyUnitOfWork


@asynccontextmanager
async def _uow_factory():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(DocumentModel.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield lambda **kwargs: SQLAlchemyUnitOfWork(session_factory=session_factory, **kwargs)
    finally:
        await engine.dispose()


def _new_doc() -> Document:
    now = utcnow()
    return Document(
        id=None,
        file_asset_id=10,
        status="pending",
        created_at=now,
        updated_at=now,
    )


async def test_clean_exit_commits_without_explicit_commit() -> None:
    async with _uow_factory() as factory:
        async with factory() as uow:
            doc = await uow.document_repository.create(_new_doc())

        async with factory(readonly=True) as uow:
            assert await uow.document_repository.get_by_id(doc.id) is not None


async def test_exception_rolls_back_writes() -> None:
    async with _uow_factory() as factory:
        doc_id = None
        with pytest.raises(ValueError):
            async with factory() as uow:
                doc = await uow.document_repository.create(_new_doc())
                doc_id = doc.id
                raise ValueError("boom")

        # 防空洞断言：写入必须真实发生过（flush 已分配 id），回滚验证才有意义
        assert doc_id is not None
        async with factory(readonly=True) as uow:
            assert await uow.document_repository.get_by_id(doc_id) is None


async def test_writes_after_midscope_commit_are_committed_on_exit() -> None:
    async with _uow_factory() as factory:
        async with factory() as uow:
            first = await uow.document_repository.create(_new_doc())
            await uow.commit()
            second = await uow.document_repository.create(_new_doc())

        async with factory(readonly=True) as uow:
            assert await uow.document_repository.get_by_id(first.id) is not None
            assert await uow.document_repository.get_by_id(second.id) is not None


async def test_readonly_commit_raises() -> None:
    async with _uow_factory() as factory:
        async with factory(readonly=True) as uow:
            with pytest.raises(RuntimeError, match="read-only"):
                await uow.commit()


async def test_readonly_write_attempt_raises_instead_of_silent_discard() -> None:
    async with _uow_factory() as factory:
        with pytest.raises(RuntimeError, match="read-only"):
            async with factory(readonly=True) as uow:
                await uow.document_repository.create(_new_doc())


async def test_readonly_core_dml_raises_instead_of_silent_discard() -> None:
    """Core UPDATE（不经过 ORM flush）在只读 UoW 下同样必须报错。"""
    async with _uow_factory() as factory:
        async with factory() as uow:
            doc = await uow.document_repository.create(_new_doc())

        with pytest.raises(RuntimeError, match="read-only"):
            async with factory(readonly=True) as uow:
                # try_mark_parsing 内部是 session.execute(update(...)) 条件更新
                await uow.document_repository.try_mark_parsing(doc.id)

        # 未被静默提交或丢弃：文档仍是 pending
        async with factory(readonly=True) as uow:
            unchanged = await uow.document_repository.get_by_id(doc.id)
            assert unchanged is not None and unchanged.status == "pending"


async def test_repository_access_before_enter_raises() -> None:
    async with _uow_factory() as factory:
        uow = factory()
        with pytest.raises(RuntimeError, match="not entered"):
            _ = uow.document_repository
