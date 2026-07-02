# input: 无外部依赖（纯抽象）
# output: AbstractUnitOfWork 事务边界抽象
# owner: wanhua.gu
# pos: 应用层端口 - 事务生命周期抽象，保持 repository-agnostic；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Application-layer Unit of Work port.

This base owns transaction lifecycle behavior only. Concrete repository
attributes are intentionally typed at each application service boundary
(via service-local ``Protocol``\\ s) so a new module does not require
changing one global UoW interface.

事务语义：
- 块内异常 → rollback
- 干净退出且非只读 → commit（中途显式 commit 之后产生的新写入同样会被提交）
- 只读（readonly=True）→ 永不提交；显式调用 commit() 是使用错误，由实现抛异常，
  误写同样由实现负责报错而不是静默丢弃
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class AbstractUnitOfWork(ABC):
    """Application transaction boundary abstraction."""

    def __init__(self, *, readonly: bool = False) -> None:
        self._readonly = readonly

    async def __aenter__(self) -> "AbstractUnitOfWork":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        # 按 exc_type 判断而非 exc 真值：falsy 异常实例也必须走回滚
        if exc_type is not None:
            await self.rollback()
        elif not self._readonly:
            await self.commit()

    @abstractmethod
    async def commit(self) -> None:
        """Commit the current transaction."""
        ...

    @abstractmethod
    async def rollback(self) -> None:
        """Roll back the current transaction."""
        ...
