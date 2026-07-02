# input: domain.common（BaseEntity、异常），纯业务逻辑
# output: OAuthAccount 领域实体（联合登录身份，挂在 User 聚合下）
# owner: wanhua.gu
# pos: 领域层 - 联合身份实体：记录某 provider 的稳定标识与所属用户；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Domain entity for a federated identity linked to a user (e.g. Google)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from domain.common.entity import BaseEntity
from domain.common.exceptions import DomainValidationException


@dataclass
class OAuthAccount(BaseEntity[int]):
    """A federated login identity belonging to a user.

    ``provider`` + ``provider_sub`` together uniquely identify an external
    identity (e.g. provider="google", provider_sub=Google 的稳定 user id)。
    """

    user_id: int = 0
    provider: str = ""
    provider_sub: str = ""
    email: Optional[str] = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.provider or not self.provider.strip():
            raise DomainValidationException("provider is required", field="provider")
        if not self.provider_sub or not self.provider_sub.strip():
            raise DomainValidationException("provider_sub is required", field="provider_sub")
