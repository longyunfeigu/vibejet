"""Document database model definitions."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, CheckConstraint, DateTime, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base


class DocumentModel(Base):
    """ORM mapping for documents table."""

    __tablename__ = "documents"
    __table_args__ = (
        # 列表以 owner_id 打头走复合索引；孤立 created_at 索引无查询使用，不建
        Index("ix_documents_owner_created", "owner_id", "created_at"),
        Index("ix_documents_file_asset_id", "file_asset_id"),
        CheckConstraint("status IN ('pending', 'parsing', 'ready', 'failed')", name="status"),
        {
            "comment": "文档表，记录文件解析为 Markdown 的语义层聚合",
        },
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="主键ID",
    )
    owner_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="归属用户ID（可为空；示例项目未强制外键约束）",
    )
    file_asset_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="关联的文件资产ID（逻辑外键，未强制约束）",
    )
    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="文档标题（默认取原始文件名）",
    )
    source_filename: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="原始文件名快照",
    )
    content_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="源文件 MIME 类型快照",
    )
    parser: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        comment="完成解析所用的解析器：markitdown/textin",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
        comment="解析状态：pending/parsing/ready/failed",
    )
    content_md: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="解析产物（规范化 Markdown），ready 时非空",
    )
    error_code: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="失败错误码（如 document.parse.empty_content）",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="失败错误详情",
    )
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        comment="扩展元数据（JSON，如页数、解析耗时）",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="删除时间（软删除）",
    )

    def __repr__(self) -> str:
        return "<DocumentModel(id={id}, file_asset_id={fa}, status='{status}')>".format(
            id=self.id,
            fa=self.file_asset_id,
            status=self.status,
        )
