# input: ChatApplicationService + 内存 fake UoW/仓储/带计数的 fake LLM
# output: Epic-1 Story 1.2 chat 归属校验与零副作用验收测试
# pos: 后端测试 - 越权 chat 必须 404 且不落消息/不建 Run/不调 LLM；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Chat ownership tests (Epic 1, Story 1.2).

关键不变量 I3：非 owner 的 chat 请求（stream 与 sync）在任何写库副作用
（用户消息、Run）与 LLM 调用之前被 404 拦截；stream 形态下异常发生在
StreamingResponse 构造之前（await 阶段），不会 200 后断流。
"""

from __future__ import annotations

from typing import AsyncIterator, Optional

import pytest

from application.dto import ChatRequestDTO
from application.ports.llm import LLMChunk, LLMMessage
from application.services.chat_service import ChatApplicationService
from application.utils.time import utcnow
from domain.conversation.entity import Conversation, Message, Run
from domain.conversation.exceptions import ConversationNotFoundException


class _FakeConversationRepo:
    def __init__(self, conversation: Optional[Conversation]):
        self._conversation = conversation

    async def get_by_id(self, conversation_id: int) -> Optional[Conversation]:
        return self._conversation

    async def update(self, conversation: Conversation) -> Conversation:
        self._conversation = conversation
        return conversation


class _FakeMessageRepo:
    def __init__(self):
        self.created: list[Message] = []

    async def create(self, message: Message) -> Message:
        message.id = len(self.created) + 1
        self.created.append(message)
        return message

    async def list_recent_by_conversation(self, conversation_id: int, limit: int):
        return list(self.created)


class _FakeRunRepo:
    def __init__(self):
        self.created: list[Run] = []

    async def create(self, run: Run) -> Run:
        run.id = len(self.created) + 1
        self.created.append(run)
        return run

    async def get_by_id(self, run_id: int) -> Optional[Run]:
        return next((r for r in self.created if r.id == run_id), None)

    async def update(self, run: Run) -> Run:
        return run


class _FakeUoW:
    def __init__(self, conversation: Optional[Conversation]):
        self.conversation_repository = _FakeConversationRepo(conversation)
        self.message_repository = _FakeMessageRepo()
        self.run_repository = _FakeRunRepo()

    def __call__(self, **kwargs):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def commit(self):
        return None


class _CountingLLM:
    def __init__(self):
        self.calls = 0

    async def generate(self, messages: list[LLMMessage], **kwargs):
        self.calls += 1
        from application.ports.llm import LLMResponse

        return LLMResponse(content="hi", model="m")

    async def stream(self, messages: list[LLMMessage], **kwargs) -> AsyncIterator[LLMChunk]:
        self.calls += 1
        yield LLMChunk(content="hi")


def _setup(owner_id: Optional[int]):
    now = utcnow()
    conv = Conversation(
        id=1, title="t", status="active", owner_id=owner_id, created_at=now, updated_at=now
    )
    uow = _FakeUoW(conv)
    llm = _CountingLLM()
    service = ChatApplicationService(uow_factory=uow, llm=llm)
    return service, uow, llm


def _dto(stream: bool) -> ChatRequestDTO:
    return ChatRequestDTO(message="hello", stream=stream)


async def test_non_owner_stream_404_before_stream_and_no_side_effects() -> None:
    service, uow, llm = _setup(owner_id=1)

    # 关键断言：异常在 await 阶段抛出（StreamingResponse 之前），而非迭代时
    with pytest.raises(ConversationNotFoundException):
        await service.send_message_stream(1, _dto(stream=True), owner_id=2)

    assert uow.message_repository.created == []
    assert uow.run_repository.created == []
    assert llm.calls == 0


async def test_non_owner_sync_404_and_no_side_effects() -> None:
    service, uow, llm = _setup(owner_id=1)

    with pytest.raises(ConversationNotFoundException):
        await service.send_message_sync(1, _dto(stream=False), owner_id=2)

    assert uow.message_repository.created == []
    assert uow.run_repository.created == []
    assert llm.calls == 0


async def test_legacy_null_owner_conversation_unreachable() -> None:
    service, uow, llm = _setup(owner_id=None)

    with pytest.raises(ConversationNotFoundException):
        await service.send_message_sync(1, _dto(stream=False), owner_id=1)
    assert llm.calls == 0


async def test_owner_chat_still_works() -> None:
    service, uow, llm = _setup(owner_id=2)

    result = await service.send_message_sync(1, _dto(stream=False), owner_id=2)
    assert result["message"]["content"] == "hi"
    assert llm.calls == 1
    # 用户消息 + assistant 消息都已落库
    assert [m.role for m in uow.message_repository.created] == ["user", "assistant"]
