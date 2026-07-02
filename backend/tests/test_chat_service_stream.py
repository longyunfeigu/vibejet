# input: ChatApplicationService + 内存 fake UoW/仓储/LLM
# output: SSE 流式聊天的预校验时机（4xx 先于流）与完整事件序列测试
# pos: 后端测试 - 聊天应用服务流式路径验证；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Tests for ChatApplicationService.send_message_stream validation timing.

审计 P1-1：会话不存在/已归档的域异常必须在返回 SSE 生成器之前抛出
（即 await send_message_stream 时），否则 StreamingResponse 已发 200，
客户端拿到的是中断流而不是 4xx。
"""

from __future__ import annotations

from typing import AsyncIterator, Optional

import pytest

from application.ports.llm import LLMChunk, LLMMessage
from application.ports.unit_of_work import AbstractUnitOfWork
from application.services.chat_service import ChatApplicationService
from application.utils.time import utcnow
from domain.conversation.entity import Conversation, Message, Run
from domain.conversation.exceptions import (
    ConversationArchivedException,
    ConversationNotFoundException,
)


class _FakeConversationRepo:
    def __init__(self, conversation: Optional[Conversation]):
        self._conversation = conversation

    async def get_by_id(self, conversation_id: int) -> Optional[Conversation]:
        return self._conversation


class _FakeMessageRepo:
    def __init__(self):
        self._next_id = 1
        self.created: list[Message] = []

    async def create(self, message: Message) -> Message:
        message.id = self._next_id
        self._next_id += 1
        self.created.append(message)
        return message

    async def list_recent_by_conversation(self, conversation_id: int, limit: int) -> list[Message]:
        return list(self.created)


class _FakeRunRepo:
    def __init__(self):
        self._runs: dict[int, Run] = {}
        self._next_id = 1

    async def create(self, run: Run) -> Run:
        run.id = self._next_id
        self._next_id += 1
        self._runs[run.id] = run
        return run

    async def get_by_id(self, run_id: int) -> Optional[Run]:
        return self._runs.get(run_id)

    async def update(self, run: Run) -> Run:
        self._runs[run.id] = run
        return run


class _FakeUoW(AbstractUnitOfWork):
    """继承端口基类以复用真实退出语义（干净退出即提交，异常回滚）。"""

    def __init__(self, conversation: Optional[Conversation]):
        super().__init__()
        self.conversation_repository = _FakeConversationRepo(conversation)
        self.message_repository = _FakeMessageRepo()
        self.run_repository = _FakeRunRepo()
        self.committed = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        return None


class _FakeLLM:
    async def generate(self, messages: list[LLMMessage], **kwargs):  # pragma: no cover
        raise NotImplementedError

    async def stream(self, messages: list[LLMMessage], **kwargs) -> AsyncIterator[LLMChunk]:
        yield LLMChunk(content="Hello")
        yield LLMChunk(content=" world")
        yield LLMChunk(prompt_tokens=3, completion_tokens=2, total_tokens=5)


def _service(conversation: Optional[Conversation]) -> tuple[ChatApplicationService, _FakeUoW]:
    uow = _FakeUoW(conversation)
    service = ChatApplicationService(uow_factory=lambda: uow, llm=_FakeLLM())
    return service, uow


def _chat_dto():
    from application.dto import ChatRequestDTO

    return ChatRequestDTO(message="hi", stream=True)


async def test_stream_raises_not_found_before_returning_generator() -> None:
    service, _ = _service(conversation=None)

    # 关键断言：异常在 await 阶段抛出，而不是首次迭代生成器时
    with pytest.raises(ConversationNotFoundException):
        await service.send_message_stream(1, _chat_dto())


async def test_stream_raises_archived_before_returning_generator() -> None:
    now = utcnow()
    conv = Conversation(id=1, title="t", status="archived", created_at=now, updated_at=now)
    service, _ = _service(conversation=conv)

    with pytest.raises(ConversationArchivedException):
        await service.send_message_stream(1, _chat_dto())


async def test_stream_happy_path_emits_full_event_sequence() -> None:
    now = utcnow()
    conv = Conversation(id=1, title="t", status="active", created_at=now, updated_at=now)
    service, uow = _service(conversation=conv)

    stream = await service.send_message_stream(1, _chat_dto())
    events = [chunk async for chunk in stream]

    joined = "".join(events)
    for expected in (
        "event: message_created",
        "event: message_delta",
        "event: message_complete",
        "event: run_complete",
        "event: done",
    ):
        assert expected in joined
    assert "Hello world" in joined
    # run 已完结
    run = await uow.run_repository.get_by_id(1)
    assert run is not None and run.status == "completed"
