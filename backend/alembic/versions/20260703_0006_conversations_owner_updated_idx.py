# input: infrastructure/models/conversation.py ORM 定义（与之严格对齐）
# output: conversations (owner_id, updated_at) 索引替换 (owner_id, created_at)（迁移版本 0006）
# pos: 数据库迁移 - 0006 会话列表排序索引对齐"最近活跃"语义；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""conversations: replace owner/created index with owner/updated

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-03

会话列表按 updated_at desc 排序（聊天活动会 bump updated_at，最近活跃优先），
原 (owner_id, created_at) 索引与排序键不匹配，替换为 (owner_id, updated_at)。
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_conversations_owner_created", table_name="conversations")
    op.create_index("ix_conversations_owner_updated", "conversations", ["owner_id", "updated_at"])


def downgrade() -> None:
    op.drop_index("ix_conversations_owner_updated", table_name="conversations")
    op.create_index("ix_conversations_owner_created", "conversations", ["owner_id", "created_at"])
