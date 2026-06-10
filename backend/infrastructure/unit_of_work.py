# input: SQLAlchemy AsyncSession 工厂, infrastructure.repositories 各仓储实现
# output: SQLAlchemyUnitOfWork（仓储懒实例化的事务边界实现）
# owner: wanhua.gu
# pos: 基础设施层 - UoW 具体实现；新聚合只需在 _REPOSITORY_FACTORIES 加一行；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""SQLAlchemy Unit of Work 实现。

仓储通过 ``_REPOSITORY_FACTORIES`` 注册表 + ``__getattr__`` 懒实例化：
- 每个 UoW 只构造实际被访问的仓储
- 新增聚合只需要在注册表中加一行，不需要改动任何方法
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from application.ports.unit_of_work import AbstractUnitOfWork
from infrastructure.database import AsyncSessionLocal
from infrastructure.repositories.agent_config_repository import (
    SQLAlchemyAgentConfigRepository,
)
from infrastructure.repositories.conversation_repository import (
    SQLAlchemyConversationRepository,
)
from infrastructure.repositories.file_asset_repository import (
    SQLAlchemyFileAssetRepository,
)
from infrastructure.repositories.message_repository import (
    SQLAlchemyMessageRepository,
)
from infrastructure.repositories.run_repository import (
    SQLAlchemyRunRepository,
)
from infrastructure.repositories.user_repository import (
    SQLAlchemyUserRepository,
)


class SQLAlchemyUnitOfWork(AbstractUnitOfWork):
    """基于SQLAlchemy的Unit of Work"""

    # 仓储注册表：属性名 -> 以 session 为构造参数的工厂
    _REPOSITORY_FACTORIES: dict[str, Callable[[AsyncSession], Any]] = {
        "file_asset_repository": SQLAlchemyFileAssetRepository,
        "conversation_repository": SQLAlchemyConversationRepository,
        "message_repository": SQLAlchemyMessageRepository,
        "run_repository": SQLAlchemyRunRepository,
        "agent_config_repository": SQLAlchemyAgentConfigRepository,
        "user_repository": SQLAlchemyUserRepository,
    }

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

    def __getattr__(self, name: str) -> Any:
        # 仅在实例属性缺失时触发：按注册表懒实例化仓储并缓存
        factory = self._REPOSITORY_FACTORIES.get(name)
        if factory is None:
            raise AttributeError(f"{type(self).__name__!r} object has no attribute {name!r}")
        session = self.__dict__.get("session")
        if session is None:
            raise RuntimeError("UnitOfWork not entered. Use `async with uow_factory() as uow:`")
        repo = factory(session)
        setattr(self, name, repo)
        return repo

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        if self.session is None:
            self.session = self._session_factory()
        # 仅在非只读模式下显式开启事务
        if not self._readonly:
            await self.session.begin()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        try:
            await super().__aexit__(exc_type, exc, tb)
        finally:
            if self.session is not None:
                # commit/rollback 后事务通常已结束；只读模式下这里收掉隐式事务
                if self.session.in_transaction():
                    await self.session.rollback()
                if self._external_session is None:
                    await self.session.close()
                    self.session = None
            # 丢弃绑定在已关闭 session 上的仓储缓存
            for repo_name in self._REPOSITORY_FACTORIES:
                self.__dict__.pop(repo_name, None)

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
