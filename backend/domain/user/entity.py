# input: domain.common（BaseEntity、异常），纯业务逻辑
# output: User 领域实体（认证主体聚合根）
# owner: wanhua.gu
# pos: 领域层 - 用户聚合根：激活/停用不变量、可认证性判定；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Domain entity for the user aggregate (authentication subject)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from domain.common.entity import BaseEntity
from domain.common.exceptions import (
    DomainValidationException,
    SuperuserDeactivationForbiddenException,
    UserAlreadyActiveException,
    UserAlreadyInactiveException,
)


@dataclass
class User(BaseEntity[int]):
    """Aggregate root representing an authenticatable user.

    The entity stores only the password *hash*; hashing itself is an
    application/infrastructure concern (see ``application.ports.security``).
    """

    username: str = ""
    email: str = ""
    hashed_password: str = ""
    full_name: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.username or not self.username.strip():
            raise DomainValidationException("Username is required", field="username")
        if not self.email or "@" not in self.email:
            raise DomainValidationException("Valid email is required", field="email")

    def activate(self) -> None:
        if self.is_active:
            raise UserAlreadyActiveException()
        self.is_active = True
        self._touch()

    def deactivate(self) -> None:
        # 业务不变量：超级用户不可被停用
        if self.is_superuser:
            raise SuperuserDeactivationForbiddenException()
        if not self.is_active:
            raise UserAlreadyInactiveException()
        self.is_active = False
        self._touch()

    def set_password_hash(self, hashed_password: str) -> None:
        if not hashed_password:
            raise DomainValidationException("Password hash is required", field="password")
        self.hashed_password = hashed_password
        self._touch()

    def can_authenticate(self) -> bool:
        return self.is_active and not self.is_deleted()
