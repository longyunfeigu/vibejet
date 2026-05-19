"""SQLAlchemy Unit of Work 实现"""

from __future__ import annotations

from typing import Optional, Callable
import inspect

from sqlalchemy.ext.asyncio import AsyncSession

from domain.common.unit_of_work import AbstractUnitOfWork
from infrastructure.database import AsyncSessionLocal
from infrastructure.repositories.file_asset_repository import (
    SQLAlchemyFileAssetRepository,
)
from infrastructure.repositories.conversation_repository import (
    SQLAlchemyConversationRepository,
)
from infrastructure.repositories.message_repository import (
    SQLAlchemyMessageRepository,
)
from infrastructure.repositories.run_repository import (
    SQLAlchemyRunRepository,
)
from infrastructure.repositories.agent_config_repository import (
    SQLAlchemyAgentConfigRepository,
)


class SQLAlchemyUnitOfWork(AbstractUnitOfWork):
    """基于SQLAlchemy的Unit of Work"""

    def __init__(
        self,
        session_factory: Callable[[], AsyncSession] = AsyncSessionLocal,
        session: Optional[AsyncSession] = None,
        *,
        readonly: bool = False,
    ) -> None:
        super().__init__(readonly=readonly)
        self._session_factory = session_factory
        self._external_session = session
        self.session: Optional[AsyncSession] = session
        self.file_asset_repository = None  # type: ignore[assignment]

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        if self.session is None:
            self.session = self._session_factory()
        self.file_asset_repository = SQLAlchemyFileAssetRepository(self.session)
        self.register_repository("file_asset_repository", self.file_asset_repository)
        self.conversation_repository = SQLAlchemyConversationRepository(self.session)
        self.register_repository("conversation_repository", self.conversation_repository)
        self.message_repository = SQLAlchemyMessageRepository(self.session)
        self.register_repository("message_repository", self.message_repository)
        self.run_repository = SQLAlchemyRunRepository(self.session)
        self.register_repository("run_repository", self.run_repository)
        self.agent_config_repository = SQLAlchemyAgentConfigRepository(self.session)
        self.register_repository("agent_config_repository", self.agent_config_repository)
        # 仅在非只读模式下显式开启事务
        if not self._readonly:
            self._transaction = await self.session.begin()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        try:
            await super().__aexit__(exc_type, exc, tb)
        finally:
            # 事务在 commit/rollback 后通常会结束，这里仅在仍然活动时做安全关闭
            tx = getattr(self, "_transaction", None)
            if tx is not None and getattr(tx, "is_active", False):
                close = getattr(tx, "close", None)
                if callable(close):
                    res = close()
                    if inspect.isawaitable(res):
                        await res
            if self._external_session is None and self.session is not None:
                await self.session.close()
                self.session = None
            self.file_asset_repository = None  # type: ignore[assignment]
            self.conversation_repository = None  # type: ignore[assignment]
            self.message_repository = None  # type: ignore[assignment]
            self.run_repository = None  # type: ignore[assignment]
            self.agent_config_repository = None  # type: ignore[assignment]
            self._repositories.clear()

    async def commit(self) -> None:
        if self._readonly:
            # 只读情况下不提交
            self._committed = True
            return
        if self.session and self.session.in_transaction():
            await self.session.commit()
        self._committed = True

    async def rollback(self) -> None:
        if self.session and self.session.in_transaction():
            await self.session.rollback()
        self._committed = False
