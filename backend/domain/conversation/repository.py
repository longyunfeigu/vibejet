"""Repository abstractions for conversation aggregate."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from .entity import AgentConfig, Conversation, Message, Run


class ConversationRepository(ABC):
    """Contract for persisting and querying conversations."""

    @abstractmethod
    async def create(self, conversation: Conversation) -> Conversation: ...

    @abstractmethod
    async def update(self, conversation: Conversation) -> Conversation: ...

    @abstractmethod
    async def touch_activity(self, conversation_id: int, *, at: datetime) -> None:
        """只刷新 ``updated_at``（且仅限未软删的行），不回写其他列。

        聊天活跃度刷新走这里而不是整行 ``update``：读-改-写整行会覆盖并发 PATCH 的
        title/model，或把刚被软删的会话"复活"。行不存在/已软删 → 抛
        ``ConversationNotFoundException``。
        """
        ...

    @abstractmethod
    async def get_by_id(
        self, conversation_id: int, *, include_deleted: bool = False
    ) -> Optional[Conversation]: ...

    @abstractmethod
    async def list(
        self,
        *,
        owner_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Conversation]: ...

    @abstractmethod
    async def count(
        self, *, owner_id: Optional[int] = None, status: Optional[str] = None
    ) -> int: ...


class MessageRepository(ABC):
    """Contract for persisting and querying messages."""

    @abstractmethod
    async def create(self, message: Message) -> Message: ...

    @abstractmethod
    async def list_by_conversation(
        self,
        conversation_id: int,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Message]: ...

    @abstractmethod
    async def list_recent_by_conversation(
        self,
        conversation_id: int,
        *,
        limit: int = 200,
    ) -> list[Message]:
        """返回最近 N 条消息，按时间正序（最旧→最新）排列。

        用于喂给 LLM 的上下文加载：长对话需要"最近 N 条"而不是"最早 N 条"。
        """
        ...

    @abstractmethod
    async def count_by_conversation(self, conversation_id: int) -> int: ...


class RunRepository(ABC):
    """Contract for persisting and querying runs."""

    @abstractmethod
    async def create(self, run: Run) -> Run: ...

    @abstractmethod
    async def update(self, run: Run) -> Run: ...

    @abstractmethod
    async def get_by_id(self, run_id: int) -> Optional[Run]: ...

    @abstractmethod
    async def list_by_conversation(
        self,
        conversation_id: int,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Run]: ...


class AgentConfigRepository(ABC):
    """Contract for persisting and querying agent configurations."""

    @abstractmethod
    async def create(self, config: AgentConfig) -> AgentConfig: ...

    @abstractmethod
    async def update(self, config: AgentConfig) -> AgentConfig: ...

    @abstractmethod
    async def delete(self, config_id: int) -> None: ...

    @abstractmethod
    async def get_by_id(self, config_id: int) -> Optional[AgentConfig]: ...

    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[AgentConfig]: ...

    @abstractmethod
    async def list(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> list[AgentConfig]: ...

    @abstractmethod
    async def count(self) -> int: ...
