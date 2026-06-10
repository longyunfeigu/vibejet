# input: domain.common（BaseEntity、异常），纯业务逻辑
# output: Document 领域实体（文档解析聚合根，pending/parsing/ready/failed 状态机）
# owner: wanhua.gu
# pos: 领域层 - 文档聚合根（引用 file_asset，持有解析产物 Markdown）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Domain entity for the document aggregate.

A ``Document`` is the semantic-layer view of an uploaded file: it references
a ``FileAsset`` (byte-layer fact) and owns the parse lifecycle that turns the
raw bytes into canonical Markdown consumable by AI features.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from domain.common.entity import BaseEntity, utcnow
from domain.common.exceptions import DomainValidationException
from domain.document.exceptions import DocumentAlreadyProcessingException

_DOCUMENT_STATUSES = {"pending", "parsing", "ready", "failed"}


@dataclass
class Document(BaseEntity[int]):
    """Aggregate root describing a parsed (or to-be-parsed) document.

    State machine: pending → parsing → ready | failed.
    ``ready`` and ``failed`` may go back to ``pending`` via :meth:`reset_for_reparse`.
    """

    owner_id: Optional[int] = None
    file_asset_id: int = 0
    title: Optional[str] = None
    source_filename: Optional[str] = None
    content_type: Optional[str] = None
    parser: Optional[str] = None
    status: str = "pending"
    content_md: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.status = self.status or "pending"
        if self.status not in _DOCUMENT_STATUSES:
            raise DomainValidationException(
                f"非法的文档状态: {self.status}",
                field="status",
                details={"allowed": sorted(_DOCUMENT_STATUSES)},
            )
        if self.file_asset_id is None or self.file_asset_id <= 0:
            raise DomainValidationException(
                "文档必须关联一个文件资产",
                field="file_asset_id",
            )
        if self.metadata is None:
            self.metadata = {}

    # ── 状态机 ──────────────────────────────────────────────────────

    def start_parsing(self) -> None:
        """pending/failed/ready → parsing；parsing 中禁止重复进入。"""
        if self.status == "parsing":
            raise DocumentAlreadyProcessingException(self.id)
        self.status = "parsing"
        self.error_code = None
        self.error_message = None
        self._touch()

    def mark_ready(
        self,
        *,
        content_md: str,
        parser: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        self.status = "ready"
        self.content_md = content_md
        self.parser = parser
        self.error_code = None
        self.error_message = None
        if metadata:
            self.metadata = {**self.metadata, **metadata}
        self._touch()

    def mark_failed(self, *, error_code: str, error_message: str, parser: Optional[str] = None) -> None:
        self.status = "failed"
        self.error_code = error_code
        self.error_message = error_message
        if parser:
            self.parser = parser
        self._touch()

    def reset_for_reparse(self) -> None:
        """ready/failed/pending → pending（清空旧产物）；parsing 中禁止。"""
        if self.status == "parsing":
            raise DocumentAlreadyProcessingException(self.id)
        self.status = "pending"
        self.content_md = None
        self.error_code = None
        self.error_message = None
        self._touch()

    def soft_delete(self) -> None:
        self.deleted_at = utcnow()
        self._touch()

    # ── 查询语义 ────────────────────────────────────────────────────

    def is_ready(self) -> bool:
        return self.status == "ready"

    def belongs_to(self, user_id: int) -> bool:
        return self.owner_id == user_id
