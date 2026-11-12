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
