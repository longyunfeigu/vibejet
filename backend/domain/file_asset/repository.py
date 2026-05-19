"""Repository abstraction for file assets.

Delete semantics（重要）:

- **软删除**：通过领域行为 + ``update`` 完成，不在仓储层提供独立方法。
  调用方负责 ``asset.mark_deleted()`` 然后 ``repo.update(asset)``，仓储默认查询会
  排除 ``deleted_at IS NOT NULL`` 的行（``include_deleted=True`` 可显式取出）。
- **物理删除**：``hard_delete`` / ``hard_delete_by_key`` 直接 ``DELETE FROM`` 数据行，
  仅供 purge / 数据清理流程使用。命名带 ``hard_`` 前缀以便与软删显式区分，
  避免新人误把 ``delete`` 当作软删入口。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from .entity import FileAsset


class FileAssetRepository(ABC):
    """Contract for persisting and querying file assets.

    软删除约定见模块 docstring：软删走 ``update + mark_deleted``，
    ``hard_delete*`` 才是物理删除。
    """

    @abstractmethod
    async def create(self, asset: FileAsset) -> FileAsset: ...

    @abstractmethod
    async def update(self, asset: FileAsset) -> FileAsset: ...

    @abstractmethod
    async def hard_delete(self, asset_id: int) -> None:
        """物理删除指定 id 的资产记录（DELETE FROM），不可恢复。

        软删除请使用 ``asset.mark_deleted()`` + ``update(asset)``。
        """
        ...

    @abstractmethod
    async def hard_delete_by_key(self, key: str) -> None:
        """物理删除指定 storage key 的资产记录（DELETE FROM），不可恢复。

        软删除请使用 ``asset.mark_deleted()`` + ``update(asset)``。
        """
        ...

    @abstractmethod
    async def get_by_id(
        self, asset_id: int, *, include_deleted: bool = False
    ) -> Optional[FileAsset]: ...

    @abstractmethod
    async def get_by_key(
        self, key: str, *, include_deleted: bool = False
    ) -> Optional[FileAsset]: ...

    @abstractmethod
    async def list(
        self,
        *,
        owner_id: Optional[int] = None,
        kind: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[FileAsset]: ...

    @abstractmethod
    async def count(
        self,
        *,
        owner_id: Optional[int] = None,
        kind: Optional[str] = None,
        status: Optional[str] = None,
    ) -> int: ...
