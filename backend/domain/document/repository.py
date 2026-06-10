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
        """原子认领解析：status ∉ {parsing} 时置为 parsing 并清空错误，返回更新后实体。

        已是 parsing / 不存在 / 已软删 → 返回 None。
        这是并发安全的 check-and-set，防止同一文档被重复解析（重复计费）。
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
