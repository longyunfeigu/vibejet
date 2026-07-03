# input: infrastructure/models/conversation.py ORM 定义（与之严格对齐）
# output: conversations.owner_id 列 + (owner_id, created_at) 索引（迁移版本 0004）
# pos: 数据库迁移 - 0004 会话表补归属列，形状对齐 file_assets/documents；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""add conversations.owner_id for ownership enforcement

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-03

Hand-written migration mirroring infrastructure/models/conversation.py.
可空、不回填：遗留行 owner_id 为 NULL，视为孤儿、对所有用户不可见
（Epic-1 decisions.md D4）。
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column(
            "owner_id",
            sa.Integer(),
            nullable=True,
            comment="归属用户ID（软引用 users.id，与 file_assets/documents 一致；NULL 为遗留孤儿行）",
        ),
    )
    op.create_index(
        "ix_conversations_owner_created",
        "conversations",
        ["owner_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_conversations_owner_created", table_name="conversations")
    op.drop_column("conversations", "owner_id")
