# input: 领域实体 Document
# output: DocumentRepository ABC 仓储接口
# owner: wanhua.gu
# pos: 领域层 - 文档聚合仓储接口定义；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Repository abstraction for the document aggregate."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from .entity import Document


class DocumentRepository(ABC):
    """Contract for persisting and querying documents."""

    @abstractmethod
    async def create(self, document: Document) -> Document: ...

    @abstractmethod
    async def update(self, document: Document) -> Document: ...

    @abstractmethod
    async def get_by_id(
        self, document_id: int, *, include_deleted: bool = False
    ) -> Optional[Document]: ...

    @abstractmethod
    async def try_mark_parsing(self, document_id: int) -> Optional[Document]:
        """原子认领解析：仅 status == pending 时置为 parsing 并清空错误，返回更新后实体。

        非 pending（含 parsing/ready/failed）/ 不存在 / 已软删 → 返回 None。
        所有合法调度路径（建档、reparse、stale 恢复）都先重置为 pending，
        因此收紧到 pending 可同时挡住并发认领与排队后的串行重复认领（重复计费）。
        """
        ...

    @abstractmethod
    async def update_if_claimed(self, document: Document, *, claimed_at) -> bool:
        """条件落盘：仅当行仍处于本次认领（status=parsing 且 updated_at=claimed_at）时整行更新。

        防止僵尸 worker（stale 恢复后迟到的旧任务）覆写新一轮解析结果。
        返回 False 表示认领已失效，调用方应丢弃本次结果。
        """
        ...

    @abstractmethod
    async def list(
        self,
        *,
        owner_id: Optional[int] = None,
        file_asset_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Document]: ...

    @abstractmethod
    async def count(
        self,
        *,
        owner_id: Optional[int] = None,
        file_asset_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> int: ...
