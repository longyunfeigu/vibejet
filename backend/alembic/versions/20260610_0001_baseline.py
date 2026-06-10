# input: infrastructure/models 全部 ORM 模型定义（与之严格对齐）
# output: baseline schema（users/conversations/runs/messages/agent_configs/file_assets）
# owner: wanhua.gu
# pos: 数据库迁移 - 基线版本 0001，后续 schema 变更一律在其上 autogenerate；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""baseline schema

Revision ID: 0001
Revises:
Create Date: 2026-06-10

Hand-written baseline covering every ORM model in infrastructure/models.
Column definitions mirror the models exactly (types, nullability,
server defaults, comments, indexes).
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, comment="主键ID"),
        sa.Column("username", sa.String(50), nullable=False, comment="用户名（唯一）"),
        sa.Column("email", sa.String(255), nullable=False, comment="邮箱（唯一）"),
        sa.Column("hashed_password", sa.String(255), nullable=False, comment="密码哈希"),
        sa.Column("full_name", sa.String(100), nullable=True, comment="显示名"),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="是否激活",
        ),
        sa.Column(
            "is_superuser",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="是否超级用户",
        ),
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
        comment="用户表，认证主体",
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, comment="主键ID"),
        sa.Column("title", sa.String(255), nullable=False, comment="对话标题"),
        sa.Column("system_prompt", sa.Text(), nullable=True, comment="系统提示词"),
        sa.Column("model", sa.String(100), nullable=True, comment="默认使用的模型"),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'active'"),
            comment="对话状态：active/archived",
        ),
        sa.Column("metadata", sa.JSON(), nullable=True, comment="扩展元数据（JSON）"),
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
        comment="对话表，记录 AI 对话会话",
    )
    op.create_index("ix_conversations_status", "conversations", ["status"])
    op.create_index("ix_conversations_created_at", "conversations", ["created_at"])

    op.create_table(
        "runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, comment="主键ID"),
        sa.Column(
            "conversation_id",
            sa.Integer(),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
            comment="所属对话ID",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'running'"),
            comment="Run 状态：running/completed/failed",
        ),
        sa.Column("model", sa.String(100), nullable=True, comment="使用的模型"),
        sa.Column(
            "prompt_tokens",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="输入 token 数",
        ),
        sa.Column(
            "completion_tokens",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="输出 token 数",
        ),
        sa.Column(
            "total_tokens",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="总 token 数",
        ),
        sa.Column("error_message", sa.Text(), nullable=True, comment="错误信息"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True, comment="开始时间"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True, comment="完成时间"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="创建时间",
        ),
        comment="Run 表，记录 LLM 调用追踪",
    )
    op.create_index("ix_runs_conversation_id", "runs", ["conversation_id"])
    op.create_index("ix_runs_status", "runs", ["status"])

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, comment="主键ID"),
        sa.Column(
            "conversation_id",
            sa.Integer(),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
            comment="所属对话ID",
        ),
        sa.Column("role", sa.String(20), nullable=False, comment="消息角色：system/user/assistant"),
        sa.Column("content", sa.Text(), nullable=False, comment="消息内容"),
        sa.Column(
            "run_id",
            sa.Integer(),
            sa.ForeignKey("runs.id", ondelete="SET NULL"),
            nullable=True,
            comment="关联的 Run ID",
        ),
        sa.Column(
            "token_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Token 数量",
        ),
        sa.Column("metadata", sa.JSON(), nullable=True, comment="扩展元数据（JSON）"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="创建时间",
        ),
        comment="消息表，记录对话中的消息",
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index(
        "ix_messages_conversation_created", "messages", ["conversation_id", "created_at"]
    )

    op.create_table(
        "agent_configs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, comment="主键ID"),
        sa.Column("name", sa.String(100), nullable=False, comment="配置名称（唯一）"),
        sa.Column("system_prompt", sa.Text(), nullable=True, comment="系统提示词"),
        sa.Column("model", sa.String(100), nullable=True, comment="使用的模型"),
        sa.Column("temperature", sa.Float(), nullable=True, comment="温度参数"),
        sa.Column("max_tokens", sa.Integer(), nullable=True, comment="最大 token 数"),
        sa.Column("metadata", sa.JSON(), nullable=True, comment="扩展元数据（JSON）"),
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
        comment="Agent 配置表，记录可复用的 Agent 配置",
    )
    op.create_index("ix_agent_configs_name", "agent_configs", ["name"], unique=True)

    op.create_table(
        "file_assets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, comment="主键ID"),
        sa.Column(
            "owner_id",
            sa.Integer(),
            nullable=True,
            comment="归属用户ID（可为空；示例项目未强制外键约束）",
        ),
        sa.Column(
            "storage_type",
            sa.String(16),
            nullable=False,
            server_default=sa.text("'local'"),
            comment="存储类型：local/s3/oss",
        ),
        sa.Column("bucket", sa.String(255), nullable=True, comment="存储桶/容器名称"),
        sa.Column("region", sa.String(64), nullable=True, comment="区域名（可为空）"),
        sa.Column("key", sa.String(512), nullable=False, comment="对象存储中的Key（路径）"),
        sa.Column(
            "unique_key_hash",
            sa.String(64),
            nullable=False,
            unique=True,
            comment="唯一键哈希：SHA-256(storage_type|bucket|key)",
        ),
        sa.Column(
            "size",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("0"),
            comment="文件大小（字节）",
        ),
        sa.Column("etag", sa.String(64), nullable=True, comment="存储返回的ETag/校验值"),
        sa.Column("content_type", sa.String(100), nullable=True, comment="MIME类型"),
        sa.Column("original_filename", sa.String(255), nullable=True, comment="原始文件名"),
        sa.Column("kind", sa.String(50), nullable=True, comment="业务分类，如 avatar/document"),
        sa.Column(
            "is_public",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="是否公共可读",
        ),
        sa.Column("metadata", sa.JSON(), nullable=True, comment="扩展元数据（JSON）"),
        sa.Column("url", sa.String(1024), nullable=True, comment="公共/CDN URL快照（可选）"),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'active'"),
            comment="文件状态：pending/active/deleted",
        ),
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
        comment="文件资源表，记录对象存储中的文件元数据",
    )
    op.create_index("ix_file_assets_created_at", "file_assets", ["created_at"])
    op.create_index("ix_file_assets_owner_created", "file_assets", ["owner_id", "created_at"])


def downgrade() -> None:
    op.drop_table("file_assets")
    op.drop_table("agent_configs")
    op.drop_table("messages")
    op.drop_table("runs")
    op.drop_table("conversations")
    op.drop_table("users")
