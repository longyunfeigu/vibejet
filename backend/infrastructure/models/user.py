"""User aggregate database model definition."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column
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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    # 唯一性由 __table_args__ 中的唯一索引承担（与 baseline migration 对齐）
    username: Mapped[str] = mapped_column(String(50), nullable=False, comment="用户名（唯一）")
    email: Mapped[str] = mapped_column(String(255), nullable=False, comment="邮箱（唯一）")
    # 联合登录用户（如 Google）无本地密码，故可空
    hashed_password: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="密码哈希（联合登录用户为空）"
    )
    full_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="显示名")
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        comment="是否激活",
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        comment="是否超级用户",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属用户ID",
    )
    provider: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="身份提供方，如 google"
    )
    provider_sub: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="提供方稳定用户标识(sub)"
    )
    email: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="提供方返回的邮箱（参考）"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        comment="创建时间",
    )

    def __repr__(self) -> str:
        return f"<OAuthAccountModel(provider='{self.provider}', user_id={self.user_id})>"
