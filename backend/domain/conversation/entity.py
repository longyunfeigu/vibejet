# input: domain.common（BaseEntity、异常），纯业务逻辑
# output: Conversation, Message, Run, AgentConfig 领域实体
# owner: unknown
# pos: 领域层 - 对话聚合根及关联实体定义（继承 BaseEntity 公共原语）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Domain entities for the conversation aggregate."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from domain.common.entity import BaseEntity, ensure_utc, utcnow
from domain.common.exceptions import DomainValidationException

_CONVERSATION_STATUSES = {"active", "archived"}
_MESSAGE_ROLES = {"system", "user", "assistant"}
_RUN_STATUSES = {"running", "completed", "failed"}


@dataclass
class Conversation(BaseEntity[int]):
    """Aggregate root for a chat conversation."""

    title: str = ""
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    status: str = "active"
    metadata: dict[str, Any] = field(default_factory=dict)
    owner_id: Optional[int] = None

    def __post_init__(self) -> None:
        super().__post_init__()
        self.status = self.status or "active"
        if self.status not in _CONVERSATION_STATUSES:
            raise DomainValidationException(
                f"Invalid conversation status: {self.status}",
                field="status",
                details={"allowed": sorted(_CONVERSATION_STATUSES)},
            )
        if self.metadata is None:
            self.metadata = {}

    def update_title(self, title: str) -> None:
        self.title = title
        self._touch()

    def set_system_prompt(self, system_prompt: Optional[str]) -> None:
        self.system_prompt = system_prompt
        self._touch()

    def set_model(self, model: Optional[str]) -> None:
        self.model = model
        self._touch()

    def archive(self) -> None:
        self.status = "archived"
        self._touch()

    def record_activity(self) -> None:
        """会话内发生聊天等活动时刷新 updated_at，驱动列表"最近活跃"排序。"""
        self._touch()

    def soft_delete(self) -> None:
        self.status = "archived"
        self.mark_deleted()

    def is_active(self) -> bool:
        return self.status == "active" and self.deleted_at is None

    def belongs_to(self, user_id: int) -> bool:
        # NULL owner（遗留孤儿行）不属于任何用户
        return self.owner_id == user_id


@dataclass
class Message(BaseEntity[int]):
    """A single message within a conversation.

    Persists only ``created_at``; the inherited updated/deleted fields are unused.
    """

    conversation_id: int = 0
    role: str = "user"  # system | user | assistant
    content: str = ""
    run_id: Optional[int] = None
    token_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.role not in _MESSAGE_ROLES:
            raise DomainValidationException(
                f"Invalid message role: {self.role}",
                field="role",
                details={"allowed": sorted(_MESSAGE_ROLES)},
            )
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Run(BaseEntity[int]):
    """Tracks a single LLM invocation within a conversation.

    Phase 1 state machine: running → completed | failed
    """

    conversation_id: int = 0
    status: str = "running"
    model: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.status not in _RUN_STATUSES:
            raise DomainValidationException(
                f"Invalid run status: {self.status}",
                field="status",
                details={"allowed": sorted(_RUN_STATUSES)},
            )
        self.started_at = ensure_utc(self.started_at) or utcnow()
        self.completed_at = ensure_utc(self.completed_at)

    def mark_completed(
        self,
        *,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
    ) -> None:
        self.status = "completed"
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens
        self.completed_at = utcnow()

    def mark_failed(self, error: str) -> None:
        self.status = "failed"
        self.error_message = error
        self.completed_at = utcnow()


@dataclass
class AgentConfig(BaseEntity[int]):
    """Standalone aggregate for reusable agent configurations."""

    name: str = ""
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.name or not self.name.strip():
            raise DomainValidationException(
                "Agent config name is required",
                field="name",
            )
        if self.metadata is None:
            self.metadata = {}

    def rename(self, name: str) -> None:
        if not name or not name.strip():
            raise DomainValidationException(
                "Agent config name is required",
                field="name",
            )
        self.name = name
        self._touch()

    def set_system_prompt(self, system_prompt: Optional[str]) -> None:
        self.system_prompt = system_prompt
        self._touch()

    def set_model(self, model: Optional[str]) -> None:
        self.model = model
        self._touch()

    def set_temperature(self, temperature: Optional[float]) -> None:
        self.temperature = temperature
        self._touch()

    def set_max_tokens(self, max_tokens: Optional[int]) -> None:
        self.max_tokens = max_tokens
        self._touch()

    def set_metadata(self, metadata: dict[str, Any]) -> None:
        self.metadata = metadata
        self._touch()
