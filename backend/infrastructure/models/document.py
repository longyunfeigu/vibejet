# input: SQLAlchemy Base, infrastructure.models.base
# output: DocumentModel ORM 映射（documents 表）
# pos: 基础设施层 - 文档聚合 ORM 模型（解析状态 + Markdown 产物列）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Document database model definitions."""

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Index,
    Integer,
    JSON,
    String,
    Text,
    text,
)
from sqlalchemy.sql import func

from .base import Base


class DocumentModel(Base):
    """ORM mapping for documents table."""

    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_created_at", "created_at"),
        Index("ix_documents_owner_created", "owner_id", "created_at"),
        Index("ix_documents_file_asset_id", "file_asset_id"),
        {
            "comment": "文档表，记录文件解析为 Markdown 的语义层聚合",
        },
    )

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="主键ID",
    )
    owner_id = Column(
        Integer,
        nullable=True,
        comment="归属用户ID（可为空；示例项目未强制外键约束）",
    )
    file_asset_id = Column(
        Integer,
        nullable=False,
        comment="关联的文件资产ID（逻辑外键，未强制约束）",
    )
    title = Column(
        String(255),
        nullable=True,
        comment="文档标题（默认取原始文件名）",
    )
    source_filename = Column(
        String(255),
        nullable=True,
        comment="原始文件名快照",
    )
    content_type = Column(
        String(100),
        nullable=True,
        comment="源文件 MIME 类型快照",
    )
    parser = Column(
        String(32),
        nullable=True,
        comment="完成解析所用的解析器：markitdown/textin",
    )
    status = Column(
        String(20),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
        comment="解析状态：pending/parsing/ready/failed",
    )
    content_md = Column(
        Text,
        nullable=True,
        comment="解析产物（规范化 Markdown），ready 时非空",
    )
    error_code = Column(
        String(64),
        nullable=True,
        comment="失败错误码（如 document.parse.empty_content）",
    )
    error_message = Column(
        Text,
        nullable=True,
        comment="失败错误详情",
    )
    extra_metadata = Column(
        "metadata",
        JSON,
        nullable=True,
        default=dict,
        comment="扩展元数据（JSON，如页数、解析耗时）",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        comment="创建时间",
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )
    deleted_at = Column(
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
