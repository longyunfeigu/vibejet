# input: infrastructure/models/document.py ORM 定义（与之严格对齐）
# output: documents 表 schema（迁移版本 0002）
# owner: wanhua.gu
# pos: 数据库迁移 - 0002 新增 documents 表（文档解析聚合）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""add documents table

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-10

Hand-written migration mirroring infrastructure/models/document.py exactly
(types, nullability, server defaults, comments, indexes).
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, comment="主键ID"),
        sa.Column(
            "owner_id",
            sa.Integer(),
            nullable=True,
            comment="归属用户ID（可为空；示例项目未强制外键约束）",
        ),
        sa.Column(
            "file_asset_id",
            sa.Integer(),
            nullable=False,
            comment="关联的文件资产ID（逻辑外键，未强制约束）",
        ),
        sa.Column("title", sa.String(255), nullable=True, comment="文档标题（默认取原始文件名）"),
        sa.Column("source_filename", sa.String(255), nullable=True, comment="原始文件名快照"),
        sa.Column("content_type", sa.String(100), nullable=True, comment="源文件 MIME 类型快照"),
        sa.Column(
            "parser",
            sa.String(32),
            nullable=True,
            comment="完成解析所用的解析器：markitdown/textin",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
            comment="解析状态：pending/parsing/ready/failed",
        ),
        sa.Column(
            "content_md",
            sa.Text(),
            nullable=True,
            comment="解析产物（规范化 Markdown），ready 时非空",
        ),
        sa.Column(
            "error_code",
            sa.String(64),
            nullable=True,
            comment="失败错误码（如 document.parse.empty_content）",
        ),
        sa.Column("error_message", sa.Text(), nullable=True, comment="失败错误详情"),
        sa.Column("metadata", sa.JSON(), nullable=True, comment="扩展元数据（JSON，如页数、解析耗时）"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="创建时间",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="更新时间",
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="删除时间（软删除）"),
        comment="文档表，记录文件解析为 Markdown 的语义层聚合",
    )
    op.create_index("ix_documents_created_at", "documents", ["created_at"])
    op.create_index("ix_documents_owner_created", "documents", ["owner_id", "created_at"])
    op.create_index("ix_documents_file_asset_id", "documents", ["file_asset_id"])


def downgrade() -> None:
    op.drop_index("ix_documents_file_asset_id", table_name="documents")
    op.drop_index("ix_documents_owner_created", table_name="documents")
    op.drop_index("ix_documents_created_at", table_name="documents")
    op.drop_table("documents")
