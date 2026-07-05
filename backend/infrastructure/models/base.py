"""
数据库模型基类（SQLAlchemy 2.0 风格）
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# 约束命名约定：保证 create_all 与迁移建出的约束名跨方言一致，
# 后续 ALTER/DROP 可按名引用（未命名约束的名字由方言自动生成，跨环境不稳定）
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


# 元数据对象用于数据库迁移
metadata = Base.metadata
