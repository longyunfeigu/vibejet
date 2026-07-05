# input: infrastructure/models 全部 ORM 模型定义（与之严格对齐）
# output: 全量 init schema（users/oauth_accounts/conversations/llm_runs/messages/agent_configs/file_assets/documents）
# pos: 数据库迁移 - 唯一 init 版本 0001，后续 schema 变更一律在其上 autogenerate；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""init schema

Revision ID: 0001
Revises:
Create Date: 2026-07-04

Hand-written single init migration covering every ORM model in
infrastructure/models. Column definitions mirror the models exactly
(types, nullability, server defaults, comments, indexes, constraints).

历史说明：本文件由原 0001-0007 增量链 squash 而来（0001-0006 见 git history，
0007 索引调优未曾提交），并在 2026-07-04 做了一轮 schema 规范化：
runs → llm_runs、物理列 metadata → extra_metadata、全部约束按
infrastructure/models/base.py 的 naming_convention 显式命名、封闭枚举列加
CHECK 约束。规范化后与旧链任何版本都不等价——模板期无生产数据，
旧库一律重建（`alembic upgrade head` 于空库）。
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
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("username", sa.String(50), nullable=False, comment="用户名（唯一）"),
        sa.Column("email", sa.String(255), nullable=False, comment="邮箱（唯一）"),
        sa.Column(
            "hashed_password",
            sa.String(255),
            nullable=True,
            comment="密码哈希（联合登录用户为空）",
        ),
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
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        comment="用户表，认证主体",
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "oauth_accounts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="所属用户ID"),
        sa.Column("provider", sa.String(32), nullable=False, comment="身份提供方，如 google"),
        sa.Column(
            "provider_sub",
            sa.String(255),
            nullable=False,
            comment="提供方稳定用户标识(sub)",
        ),
        sa.Column("email", sa.String(255), nullable=True, comment="提供方返回的邮箱（参考）"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="创建时间",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_oauth_accounts"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="fk_oauth_accounts_user_id",
        ),
        comment="联合登录身份表（provider+provider_sub 唯一）",
    )
    op.create_index(
        "uq_oauth_provider_sub",
        "oauth_accounts",
        ["provider", "provider_sub"],
        unique=True,
    )
    op.create_index("ix_oauth_user_id", "oauth_accounts", ["user_id"])

    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("title", sa.String(255), nullable=False, comment="对话标题"),
        sa.Column(
            "owner_id",
            sa.Integer(),
            nullable=True,
            comment="归属用户ID（软引用 users.id，与 file_assets/documents 一致；NULL 为遗留孤儿行）",
        ),
        sa.Column("system_prompt", sa.Text(), nullable=True, comment="系统提示词"),
        sa.Column("model", sa.String(100), nullable=True, comment="默认使用的模型"),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'active'"),
            comment="对话状态：active/archived",
        ),
        sa.Column("extra_metadata", sa.JSON(), nullable=True, comment="扩展元数据（JSON）"),
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
        sa.PrimaryKeyConstraint("id", name="pk_conversations"),
        sa.CheckConstraint("status IN ('active', 'archived')", name=op.f("ck_conversations_status")),
        comment="对话表，记录 AI 对话会话",
    )
    # 列表按 owner_id 过滤 + updated_at desc 排序（最近活跃优先），复合索引与之对齐
    op.create_index(
        "ix_conversations_owner_updated", "conversations", ["owner_id", "updated_at"]
    )

    op.create_table(
        "llm_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("conversation_id", sa.Integer(), nullable=False, comment="所属对话ID"),
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
        sa.PrimaryKeyConstraint("id", name="pk_llm_runs"),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            ondelete="CASCADE",
            name="fk_llm_runs_conversation_id",
        ),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'failed')", name=op.f("ck_llm_runs_status")
        ),
        comment="LLM Run 表，记录 LLM 调用追踪",
    )
    # list_by_conversation 按 conversation_id 过滤 + created_at desc 排序，复合索引与之对齐
    op.create_index(
        "ix_llm_runs_conversation_created", "llm_runs", ["conversation_id", "created_at"]
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("conversation_id", sa.Integer(), nullable=False, comment="所属对话ID"),
        sa.Column("role", sa.String(20), nullable=False, comment="消息角色：system/user/assistant"),
        sa.Column("content", sa.Text(), nullable=False, comment="消息内容"),
        sa.Column("run_id", sa.Integer(), nullable=True, comment="关联的 Run ID"),
        sa.Column(
            "token_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Token 数量",
        ),
        sa.Column("extra_metadata", sa.JSON(), nullable=True, comment="扩展元数据（JSON）"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="创建时间",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_messages"),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            ondelete="CASCADE",
            name="fk_messages_conversation_id",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["llm_runs.id"],
            ondelete="SET NULL",
            name="fk_messages_run_id",
        ),
        sa.CheckConstraint("role IN ('system', 'user', 'assistant')", name=op.f("ck_messages_role")),
        comment="消息表，记录对话中的消息",
    )
    # 复合索引前缀即覆盖 conversation_id 单列用途（含 CASCADE 查找），不另建单列索引
    op.create_index(
        "ix_messages_conversation_created", "messages", ["conversation_id", "created_at"]
    )

    op.create_table(
        "agent_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("name", sa.String(100), nullable=False, comment="配置名称（唯一）"),
        sa.Column("system_prompt", sa.Text(), nullable=True, comment="系统提示词"),
        sa.Column("model", sa.String(100), nullable=True, comment="使用的模型"),
        sa.Column("temperature", sa.Float(), nullable=True, comment="温度参数"),
        sa.Column("max_tokens", sa.Integer(), nullable=True, comment="最大 token 数"),
        sa.Column("extra_metadata", sa.JSON(), nullable=True, comment="扩展元数据（JSON）"),
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
        sa.PrimaryKeyConstraint("id", name="pk_agent_configs"),
        # 无 deleted_at：共享配置资源，删除即硬删，无恢复语义
        comment="Agent 配置表，记录可复用的 Agent 配置",
    )
    op.create_index("ix_agent_configs_name", "agent_configs", ["name"], unique=True)

    op.create_table(
        "file_assets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
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
        sa.Column(
            "key",
            sa.String(512),
            nullable=False,
            comment="对象存储中的Key（路径），全局唯一（uq_file_assets_key）",
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
        sa.Column("extra_metadata", sa.JSON(), nullable=True, comment="扩展元数据（JSON）"),
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
        sa.PrimaryKeyConstraint("id", name="pk_file_assets"),
        sa.CheckConstraint(
            "storage_type IN ('local', 's3', 'oss')", name=op.f("ck_file_assets_storage_type")
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'active', 'deleted')", name=op.f("ck_file_assets_status")
        ),
        comment="文件资源表，记录对象存储中的文件元数据",
    )
    op.create_index("ix_file_assets_owner_created", "file_assets", ["owner_id", "created_at"])
    # key 由服务端生成（含 uuid），全局唯一；唯一约束直接建在 key 上（upsert 每次按 key 查）
    op.create_index("uq_file_assets_key", "file_assets", ["key"], unique=True)

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
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
        sa.Column(
            "extra_metadata", sa.JSON(), nullable=True, comment="扩展元数据（JSON，如页数、解析耗时）"
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
        sa.PrimaryKeyConstraint("id", name="pk_documents"),
        sa.CheckConstraint(
            "status IN ('pending', 'parsing', 'ready', 'failed')", name=op.f("ck_documents_status")
        ),
        comment="文档表，记录文件解析为 Markdown 的语义层聚合",
    )
    op.create_index("ix_documents_owner_created", "documents", ["owner_id", "created_at"])
    op.create_index("ix_documents_file_asset_id", "documents", ["file_asset_id"])


def downgrade() -> None:
    op.drop_table("documents")
    op.drop_table("file_assets")
    op.drop_table("agent_configs")
    op.drop_table("messages")
    op.drop_table("llm_runs")
    op.drop_table("conversations")
    op.drop_table("oauth_accounts")
    op.drop_table("users")
