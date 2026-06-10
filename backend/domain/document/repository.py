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
