# input: 无外部依赖（纯抽象）
# output: AbstractUnitOfWork 事务边界抽象
# owner: wanhua.gu
# pos: 应用层端口 - 事务生命周期抽象，保持 repository-agnostic；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Application-layer Unit of Work port.

This base owns transaction lifecycle behavior only. Concrete repository
attributes are intentionally typed at each application service boundary
(via service-local ``Protocol``\\ s) so a new module does not require
changing one global UoW interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class AbstractUnitOfWork(ABC):
    """Application transaction boundary abstraction."""

    def __init__(self, *, readonly: bool = False) -> None:
        self._committed = False
        self._readonly = readonly

    async def __aenter__(self) -> "AbstractUnitOfWork":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if exc:
            await self.rollback()
        else:
            # 只在非只读且未显式提交时自动提交
            if not self._readonly and not self._committed:
                await self.commit()

    @abstractmethod
    async def commit(self) -> None:
        """Commit the current transaction."""
        ...

    @abstractmethod
    async def rollback(self) -> None:
        """Roll back the current transaction."""
        ...
