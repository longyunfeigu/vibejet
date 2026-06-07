"""Application-layer Unit of Work port.

This base owns transaction lifecycle behavior only. Concrete repository
attributes are intentionally typed at each application service boundary so a
new module does not require changing one global UoW interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AbstractUnitOfWork(ABC):
    """Application transaction boundary abstraction."""

    def __init__(self, *, readonly: bool = False) -> None:
        self._committed = False
        self._readonly = readonly
        self._repositories: dict[str, Any] = {}

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

    def register_repository(self, name: str, repo: Any) -> None:
        self._repositories[name] = repo

    def get_repository(self, name: str) -> Any:
        return self._repositories.get(name)
