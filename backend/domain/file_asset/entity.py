# input: domain.common（BaseEntity、异常），纯业务逻辑
# output: FileAsset 领域实体（对象存储文件聚合根）
# owner: unknown
# pos: 领域层 - 文件资产聚合根（继承 BaseEntity 公共原语，status 驱动软删）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Domain entity representing a stored file asset."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from domain.common.entity import BaseEntity, utcnow
from domain.common.exceptions import DomainValidationException

_ALLOWED_STATUSES = {"pending", "active", "deleted"}


@dataclass
class FileAsset(BaseEntity[int]):
    """Aggregate root describing a file stored in object storage."""

    owner_id: Optional[int] = None
    storage_type: str = "local"
    bucket: Optional[str] = None
    region: Optional[str] = None
    key: str = ""
    size: int = 0
    etag: Optional[str] = None
    content_type: Optional[str] = None
    original_filename: Optional[str] = None
    kind: Optional[str] = None
    is_public: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    url: Optional[str] = None
    status: str = "pending"

    def __post_init__(self) -> None:
        super().__post_init__()
        self.status = self.status or "pending"
        self._validate_status(self.status)
        if self.metadata is None:
            self.metadata = {}

    @staticmethod
    def _validate_status(status: str) -> None:
        if status not in _ALLOWED_STATUSES:
            raise DomainValidationException(
                f"非法的文件状态: {status}",
                field="status",
                details={"allowed": sorted(_ALLOWED_STATUSES)},
            )

    def mark_pending(self) -> None:
        self.status = "pending"
        self.deleted_at = None
        self._touch()

    def mark_active(self) -> None:
        self.status = "active"
        self.deleted_at = None
        self._touch()

    def mark_deleted(self) -> None:
        # 文件资产的软删由 status 驱动，同时记录 deleted_at
        self.status = "deleted"
        self.deleted_at = utcnow()
        self._touch()

    def update_object_metadata(
        self,
        *,
        size: Optional[int] = None,
        etag: Optional[str] = None,
        content_type: Optional[str] = None,
        url: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        if size is not None:
            self.size = size
        if etag is not None:
            self.etag = etag
        if content_type is not None:
            self.content_type = content_type
        if url is not None:
            self.url = url
        if metadata is not None:
            self.metadata = metadata
        self._touch()

    def is_deleted(self) -> bool:
        return self.status == "deleted"

    def belongs_to(self, user_id: int) -> bool:
        return self.owner_id == user_id
