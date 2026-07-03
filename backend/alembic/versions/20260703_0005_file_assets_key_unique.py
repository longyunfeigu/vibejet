# input: infrastructure/models/file_asset.py ORM 定义（与之严格对齐）
# output: file_assets.key 唯一索引 uq_file_assets_key，删除派生列 unique_key_hash（迁移版本 0005）
# pos: 数据库迁移 - 0005 文件资产表唯一键收敛到 key 本身；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""file_assets: unique index on key, drop derived unique_key_hash

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-03

key 由服务端生成（含 uuid），本就全局唯一；原 SHA-256(storage_type|bucket|key)
派生列是多余的间接层，且导致 schema（key 不唯一）与代码假设（get_by_key 单行）
不一致。唯一约束直接建在 key 上，顺带补上 key 的查询索引（upsert 每次都按 key 查）。

若历史数据存在重复 key（理论上不应发生），create_index 会失败，需先人工去重。
删列走 batch_alter_table：SQLite（本地 dev）不支持直接 DROP 带约束的列，
batch 模式重建表；Postgres 下退化为普通 ALTER。
"""

from __future__ import annotations

import hashlib

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("uq_file_assets_key", "file_assets", ["key"], unique=True)
    with op.batch_alter_table("file_assets") as batch_op:
        batch_op.drop_column("unique_key_hash")


def downgrade() -> None:
    op.add_column(
        "file_assets",
        sa.Column(
            "unique_key_hash",
            sa.String(64),
            nullable=True,
            comment="唯一键哈希：SHA-256(storage_type|bucket|key)",
        ),
    )
    # 派生列回填走 Python 侧 sha256，保持方言无关（与原仓储 _calc_unique_hash 同算法）
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, storage_type, bucket, key FROM file_assets")).fetchall()
    for row in rows:
        raw = f"{row.storage_type}|{row.bucket or ''}|{row.key}"
        conn.execute(
            sa.text("UPDATE file_assets SET unique_key_hash = :h WHERE id = :i"),
            {"h": hashlib.sha256(raw.encode("utf-8")).hexdigest(), "i": row.id},
        )
    with op.batch_alter_table("file_assets") as batch_op:
        batch_op.alter_column("unique_key_hash", existing_type=sa.String(64), nullable=False)
        batch_op.create_unique_constraint("file_assets_unique_key_hash_key", ["unique_key_hash"])
    op.drop_index("uq_file_assets_key", table_name="file_assets")
