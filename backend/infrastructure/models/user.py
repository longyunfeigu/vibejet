# input: SQLAlchemy Base 基类
# output: UserModel ORM 模型（users 表）
# owner: wanhua.gu
# pos: 基础设施层 - 用户聚合 ORM 模型定义；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""User aggregate database model definition."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, text
from sqlalchemy.sql import func

from .base import Base


class UserModel(Base):
    """ORM mapping for users table."""

    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_username", "username", unique=True),
        Index("ix_users_email", "email", unique=True),
        {
            "comment": "用户表，认证主体",
        },
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    username = Column(String(50), nullable=False, unique=True, comment="用户名（唯一）")
    email = Column(String(255), nullable=False, unique=True, comment="邮箱（唯一）")
    hashed_password = Column(String(255), nullable=False, comment="密码哈希")
    full_name = Column(String(100), nullable=True, comment="显示名")
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        comment="是否激活",
    )
    is_superuser = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        comment="是否超级用户",
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
        return f"<UserModel(id={self.id}, username='{self.username}')>"
