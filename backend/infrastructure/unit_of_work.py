# input: SQLAlchemy AsyncSession 工厂, infrastructure.repositories 各仓储实现
# output: SQLAlchemyUnitOfWork（typed cached_property 懒实例化的事务边界实现）
# owner: wanhua.gu
# pos: 基础设施层 - UoW 具体实现；新聚合 = 新增一个 cached_property；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""SQLAlchemy Unit of Work 实现。

仓储以带类型标注的 ``cached_property`` 暴露：
- 每个 UoW 只构造实际被访问的仓储（首次访问时实例化并缓存）
- mypy 可静态校验本类满足各应用服务的 service-local UoW Protocol
- 新增聚合只需要新增一个 cached_property

事务语义（见 application.ports.unit_of_work）：干净退出自动 commit，异常自动
rollback。readonly=True 时 commit() 抛异常；误写（ORM flush 或经 session 发出的
INSERT/UPDATE/DELETE）会立即报错，而不是退出时被静默回滚丢弃。
"""

from __future__ import annotations

from functools import cached_property
from typing import Callable, Optional

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from application.ports.unit_of_work import AbstractUnitOfWork
from domain.conversation.repository import (
    AgentConfigRepository,
    ConversationRepository,
    MessageRepository,
    RunRepository,
)
from domain.document.repository import DocumentRepository
from domain.file_asset.repository import FileAssetRepository
from domain.user.repository import UserRepository
from infrastructure.database import AsyncSessionLocal
from infrastructure.repositories.agent_config_repository import SQLAlchemyAgentConfigRepository
from infrastructure.repositories.conversation_repository import SQLAlchemyConversationRepository
from infrastructure.repositories.document_repository import SQLAlchemyDocumentRepository
from infrastructure.repositories.file_asset_repository import SQLAlchemyFileAssetRepository
from infrastructure.repositories.message_repository import SQLAlchemyMessageRepository
from infrastructure.repositories.run_repository import SQLAlchemyRunRepository
from infrastructure.repositories.user_repository import SQLAlchemyUserRepository

# 只读 UoW 在 session.info 上打的标记；守卫为模块级一次性注册（而不是每个
# readonly UoW 进出时 listen/remove），读热路径上只付两次 dict 操作的成本
_READONLY_FLAG = "uow_readonly"

_READONLY_ERROR = (
    "read-only UnitOfWork: write detected. Use a non-readonly UnitOfWork for write operations."
)


@event.listens_for(Session, "before_flush")
def _reject_readonly_flush(session: Session, flush_context, instances) -> None:
    if session.info.get(_READONLY_FLAG):
        raise RuntimeError(_READONLY_ERROR)


@event.listens_for(Session, "do_orm_execute")
def _reject_readonly_dml(execute_state) -> None:
    # 拦截不经过 ORM flush 的 Core DML（如仓储里的条件 UPDATE）；
    # 原生 text() 语句不在覆盖范围内
    if execute_state.session.info.get(_READONLY_FLAG) and (
        execute_state.is_insert or execute_state.is_update or execute_state.is_delete
    ):
        raise RuntimeError(_READONLY_ERROR)


class SQLAlchemyUnitOfWork(AbstractUnitOfWork):
    """基于SQLAlchemy的Unit of Work（session 由 UoW 自建自管，一次一个）"""

    def __init__(
        self,
        session_factory: Callable[[], AsyncSession] = AsyncSessionLocal,
        *,
        readonly: bool = False,
    ) -> None:
        super().__init__(readonly=readonly)
        self._session_factory = session_factory
        self.session: Optional[AsyncSession] = None

    def _require_session(self) -> AsyncSession:
        if self.session is None:
            raise RuntimeError("UnitOfWork not entered. Use `async with uow_factory() as uow:`")
        return self.session

    # ------------------------------------------------------------------
    # Repositories（懒实例化 + 实例级缓存，退出时统一清理）
    # ------------------------------------------------------------------

    @cached_property
    def file_asset_repository(self) -> FileAssetRepository:
        return SQLAlchemyFileAssetRepository(self._require_session())

    @cached_property
    def conversation_repository(self) -> ConversationRepository:
        return SQLAlchemyConversationRepository(self._require_session())

    @cached_property
    def document_repository(self) -> DocumentRepository:
        return SQLAlchemyDocumentRepository(self._require_session())

    @cached_property
    def message_repository(self) -> MessageRepository:
        return SQLAlchemyMessageRepository(self._require_session())

    @cached_property
    def run_repository(self) -> RunRepository:
        return SQLAlchemyRunRepository(self._require_session())

    @cached_property
    def agent_config_repository(self) -> AgentConfigRepository:
        return SQLAlchemyAgentConfigRepository(self._require_session())

    @cached_property
    def user_repository(self) -> UserRepository:
        return SQLAlchemyUserRepository(self._require_session())

    def _clear_repository_cache(self) -> None:
        # 走 MRO，子类新增的 cached_property 仓储同样会被清理
        for klass in type(self).__mro__:
            for name, member in vars(klass).items():
                if isinstance(member, cached_property):
                    self.__dict__.pop(name, None)

    # ------------------------------------------------------------------
    # Transaction lifecycle
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        self.session = self._session_factory()
        try:
            if self._readonly:
                # 只读模式不显式开事务（依赖 autobegin），靠 session.info 标记触发守卫
                self.session.sync_session.info[_READONLY_FLAG] = True
            else:
                await self.session.begin()
        except BaseException:
            session, self.session = self.session, None
            await session.close()
            raise
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        try:
            await super().__aexit__(exc_type, exc, tb)
        finally:
            if self.session is not None:
                self.session.sync_session.info.pop(_READONLY_FLAG, None)
                # commit/rollback 后事务通常已结束；只读模式下这里收掉隐式事务
                if self.session.in_transaction():
                    await self.session.rollback()
                await self.session.close()
                self.session = None
            # 丢弃绑定在已关闭 session 上的仓储缓存
            self._clear_repository_cache()

    async def commit(self) -> None:
        if self._readonly:
            raise RuntimeError("read-only UnitOfWork cannot commit")
        if self.session is not None:
            # 不做 in_transaction 前置判断：commit 自带 flush，
            # 保证 pending 而未触发 autobegin 的写入也被提交
            await self.session.commit()

    async def rollback(self) -> None:
        if self.session is not None and self.session.in_transaction():
            await self.session.rollback()
