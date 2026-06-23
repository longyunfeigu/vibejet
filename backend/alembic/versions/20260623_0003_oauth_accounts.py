# input: infrastructure/models/user.py ORM 定义（与之严格对齐）
# output: oauth_accounts 表 schema + users.hashed_password 改可空（迁移版本 0003）
# pos: 数据库迁移 - 0003 新增联合登录身份表并放开本地密码非空约束；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""add oauth_accounts table; make users.hashed_password nullable

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-23

Hand-written migration mirroring infrastructure/models/user.py
(OAuthAccountModel + UserModel.hashed_password nullability).
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 联合登录用户无本地密码 → 放开 users.hashed_password 非空约束
    # 用 batch 模式跨库兼容（SQLite 重建表，Postgres 普通 ALTER）
    with op.batch_alter_table("users") as batch:
        batch.alter_column(
            "hashed_password",
            existing_type=sa.String(255),
            nullable=True,
        )

    op.create_table(
        "oauth_accounts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, comment="主键ID"),
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


def downgrade() -> None:
    op.drop_index("ix_oauth_user_id", table_name="oauth_accounts")
    op.drop_index("uq_oauth_provider_sub", table_name="oauth_accounts")
    op.drop_table("oauth_accounts")
    # 注意：若已存在无密码（联合登录）用户，此降级会因 NOT NULL 失败，需先清理
    with op.batch_alter_table("users") as batch:
        batch.alter_column(
            "hashed_password",
            existing_type=sa.String(255),
            nullable=False,
        )
