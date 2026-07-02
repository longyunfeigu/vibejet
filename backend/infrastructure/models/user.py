# input: SQLAlchemy Base 基类
# output: UserModel ORM 模型（users 表）, OAuthAccountModel（oauth_accounts 表）
# owner: wanhua.gu
# pos: 基础设施层 - 用户聚合及其联合登录身份 ORM 模型定义；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""User aggregate database model definition."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, text
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
    # 唯一性由 __table_args__ 中的唯一索引承担（与 baseline migration 对齐）
    username = Column(String(50), nullable=False, comment="用户名（唯一）")
    email = Column(String(255), nullable=False, comment="邮箱（唯一）")
    # 联合登录用户（如 Google）无本地密码，故可空
    hashed_password = Column(String(255), nullable=True, comment="密码哈希（联合登录用户为空）")
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


class OAuthAccountModel(Base):
    """ORM mapping for the oauth_accounts table (federated login identities)."""

    __tablename__ = "oauth_accounts"
    __table_args__ = (
        Index("uq_oauth_provider_sub", "provider", "provider_sub", unique=True),
        Index("ix_oauth_user_id", "user_id"),
        {
            "comment": "联合登录身份表（provider+provider_sub 唯一）",
        },
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属用户ID",
    )
    provider = Column(String(32), nullable=False, comment="身份提供方，如 google")
    provider_sub = Column(String(255), nullable=False, comment="提供方稳定用户标识(sub)")
    email = Column(String(255), nullable=True, comment="提供方返回的邮箱（参考）")
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        comment="创建时间",
    )

    def __repr__(self) -> str:
        return f"<OAuthAccountModel(provider='{self.provider}', user_id={self.user_id})>"
