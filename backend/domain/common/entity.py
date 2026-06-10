# input: 仅标准库（datetime/dataclasses）
# output: BaseEntity 领域实体基类, ensure_utc/utcnow 时间工具
# owner: wanhua.gu
# pos: 领域层公共原语 - 所有聚合实体的基类（id/时间戳/软删行为）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Shared domain entity primitives.

All aggregate entities should inherit :class:`BaseEntity` instead of
re-declaring id/timestamp fields and UTC normalization by hand.
Fields not persisted by a given aggregate's ORM model simply stay ``None``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Generic, Optional, TypeVar

IdT = TypeVar("IdT")


def utcnow() -> datetime:
    """Timezone-aware UTC now."""
    return datetime.now(timezone.utc)


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Normalize a datetime to UTC; naive datetimes are assumed to be UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# Backwards-compatible alias (older code/tests imported the private name)
_ensure_utc = ensure_utc


@dataclass
class BaseEntity(Generic[IdT]):
    id: Optional[IdT] = field(default=None, kw_only=True)
    created_at: Optional[datetime] = field(default=None, kw_only=True)
    updated_at: Optional[datetime] = field(default=None, kw_only=True)
    deleted_at: Optional[datetime] = field(default=None, kw_only=True)

    def __post_init__(self) -> None:
        self.created_at = ensure_utc(self.created_at)
        self.updated_at = ensure_utc(self.updated_at)
        self.deleted_at = ensure_utc(self.deleted_at)

    def _touch(self) -> None:
        now = utcnow()
        self.updated_at = now
        if self.created_at is None:
            self.created_at = now

    def mark_deleted(self) -> None:
        self.deleted_at = utcnow()
        self._touch()

    def restore(self) -> None:
        self.deleted_at = None
        self._touch()

    def is_deleted(self) -> bool:
        return self.deleted_at is not None
