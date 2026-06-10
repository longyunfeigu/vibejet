# input: ChatUnitOfWork, LLMPort, Conversation/Message/Run 领域实体
# output: ChatApplicationService 聊天用例编排（流式 + 非流式）
# owner: unknown
# pos: 应用层服务 - 核心聊天流程编排，发消息→创建Run→调LLM→流式返回；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Application service for the chat workflow (send message → LLM → stream response).

Transaction shape (deliberate): three short UoWs instead of one long one so the
DB transaction is never held open across the LLM call —
phase 1 persist user message + create run / phase 2 call LLM (no tx) /
phase 3 persist assistant message + finalize run.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import AsyncIterator, Callable, Optional, Protocol

from application.dto import ChatRequestDTO, MessageDTO_Agent, RunDTO
from application.ports.llm import LLMMessage, LLMPort, LLMResponse
from application.utils.time import utcnow
from core.logging_config import get_logger
from domain.conversation.entity import Message, Run
from domain.conversation.exceptions import (
    ConversationArchivedException,
    ConversationNotFoundException,
    LLMProviderException,
)
from domain.conversation.repository import ConversationRepository, MessageRepository, RunRepository

logger = get_logger(__name__)


class ChatUnitOfWork(Protocol):
    conversation_repository: ConversationRepository
    message_repository: MessageRepository
    run_repository: RunRepository

    async def __aenter__(self) -> "ChatUnitOfWork": ...

    async def __aexit__(self, exc_type, exc, tb) -> None: ...

    async def commit(self) -> None: ...


@dataclass
class _StartedRun:
    """Phase-1 result: everything later phases need, detached from the UoW."""

    run_id: int
    user_message_id: int
    model: Optional[str]
    llm_messages: list[LLMMessage]


class ChatApplicationService:
    """Orchestrates sending a message to LLM and streaming the response."""

    def __init__(
        self,
        uow_factory: Callable[..., ChatUnitOfWork],
        llm: LLMPort,
    ) -> None:
        self._uow_factory = uow_factory
        self._llm = llm

    # ------------------------------------------------------------------
    # Shared phases
    # ------------------------------------------------------------------
    async def _load_history(self, uow: ChatUnitOfWork, conversation_id: int) -> list[LLMMessage]:
        """Load conversation messages as LLMMessage list (newest N, ordered chronologically)."""
        # 长对话上下文窗口：拿最近 N 条而不是最早 N 条
        messages = await uow.message_repository.list_recent_by_conversation(
            conversation_id, limit=200
        )
        return [LLMMessage(role=m.role, content=m.content) for m in messages]

    async def _start_run(self, conversation_id: int, dto: ChatRequestDTO) -> _StartedRun:
        """Phase 1: validate conversation, persist user message, create run, build LLM context."""
        async with self._uow_factory() as uow:
            conv = await uow.conversation_repository.get_by_id(conversation_id)
            if conv is None:
                raise ConversationNotFoundException(conversation_id)
            if not conv.is_active():
                raise ConversationArchivedException(conversation_id)

            model = dto.model or conv.model
            now = utcnow()

            user_msg = Message(
                id=None,
                conversation_id=conversation_id,
                role="user",
                content=dto.message,
                created_at=now,
            )
            user_msg = await uow.message_repository.create(user_msg)

            run = Run(
                id=None,
                conversation_id=conversation_id,
                status="running",
                model=model,
                started_at=now,
                created_at=now,
            )
            run = await uow.run_repository.create(run)

            history = await self._load_history(uow, conversation_id)
            await uow.commit()

        llm_messages: list[LLMMessage] = []
        if conv.system_prompt:
            llm_messages.append(LLMMessage(role="system", content=conv.system_prompt))
        llm_messages.extend(history)

        assert run.id is not None and user_msg.id is not None
        return _StartedRun(
            run_id=run.id,
            user_message_id=user_msg.id,
            model=model,
            llm_messages=llm_messages,
        )

    async def _finalize_run(
        self,
        started: _StartedRun,
        conversation_id: int,
        *,
        content: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
    ) -> tuple[Message, Optional[Run]]:
        """Phase 3: persist assistant message and mark run completed."""
        async with self._uow_factory() as uow:
            assistant_msg = Message(
                id=None,
                conversation_id=conversation_id,
                role="assistant",
                content=content,
                run_id=started.run_id,
                token_count=completion_tokens,
                created_at=utcnow(),
            )
            assistant_msg = await uow.message_repository.create(assistant_msg)

            run_entity = await uow.run_repository.get_by_id(started.run_id)
            if run_entity:
                run_entity.mark_completed(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                )
                await uow.run_repository.update(run_entity)

            await uow.commit()
        return assistant_msg, run_entity

    async def _fail_run(self, run_id: int, error: str) -> None:
        """Mark a run as failed (best effort, used on LLM errors and stream aborts)."""
        async with self._uow_factory() as uow:
            run_entity = await uow.run_repository.get_by_id(run_id)
            if run_entity and run_entity.status == "running":
                run_entity.mark_failed(error)
                await uow.run_repository.update(run_entity)
            await uow.commit()

    # ------------------------------------------------------------------
    # Use cases
    # ------------------------------------------------------------------
    async def send_message_stream(
        self,
        conversation_id: int,
        dto: ChatRequestDTO,
    ) -> AsyncIterator[str]:
        """Send a user message and stream the assistant response as SSE events.

        Yields SSE-formatted strings: `data: {...}\\n\\n`
        """
        started = await self._start_run(conversation_id, dto)

        yield _sse_event(
            "message_created",
            {
                "message_id": started.user_message_id,
                "role": "user",
            },
        )

        # Phase 2: stream LLM response
        full_content = ""
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0

        try:
            async for chunk in self._llm.stream(
                started.llm_messages,
                model=started.model,
                temperature=dto.temperature,
                max_tokens=dto.max_tokens,
            ):
                if chunk.content:
                    full_content += chunk.content
                    yield _sse_event(
                        "message_delta",
                        {
                            "content": chunk.content,
                        },
                    )
                # Capture usage from final chunk
                if chunk.total_tokens > 0:
                    prompt_tokens = chunk.prompt_tokens
                    completion_tokens = chunk.completion_tokens
                    total_tokens = chunk.total_tokens

        except (asyncio.CancelledError, GeneratorExit):
            # 客户端断连：CancelledError/GeneratorExit 是 BaseException，
            # 不收尾的话 Run 会永远停留在 running。shield 保证收尾写库不被二次取消打断。
            logger.warning("llm_stream_cancelled", run_id=started.run_id)
            try:
                await asyncio.shield(self._fail_run(started.run_id, "stream cancelled by client"))
            except Exception as cleanup_exc:  # pragma: no cover - best effort
                logger.error(
                    "llm_stream_cancel_cleanup_failed",
                    run_id=started.run_id,
                    error=str(cleanup_exc),
                )
            raise
        except Exception as exc:
            logger.error("llm_stream_failed", error=str(exc), run_id=started.run_id)
            await self._fail_run(started.run_id, str(exc))
            yield _sse_event(
                "error", {"message": "An error occurred while generating the response."}
            )
            yield _sse_event("done", {})
            return

        # Phase 3: persist assistant message and complete run
        assistant_msg, _ = await self._finalize_run(
            started,
            conversation_id,
            content=full_content,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

        yield _sse_event(
            "message_complete",
            {
                "message_id": assistant_msg.id,
                "role": "assistant",
                "content": full_content,
            },
        )
        yield _sse_event(
            "run_complete",
            {
                "run_id": started.run_id,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            },
        )
        yield _sse_event("done", {})

    async def send_message_sync(
        self,
        conversation_id: int,
        dto: ChatRequestDTO,
    ) -> dict:
        """Send a user message and return the full assistant response (non-streaming)."""
        started = await self._start_run(conversation_id, dto)

        # Phase 2: call LLM
        try:
            response: LLMResponse = await self._llm.generate(
                started.llm_messages,
                model=started.model,
                temperature=dto.temperature,
                max_tokens=dto.max_tokens,
            )
        except Exception as exc:
            logger.error("llm_generate_failed", error=str(exc), run_id=started.run_id)
            await self._fail_run(started.run_id, str(exc))
            raise LLMProviderException(str(exc))

        # Phase 3: persist assistant message and complete run
        assistant_msg, run_entity = await self._finalize_run(
            started,
            conversation_id,
            content=response.content,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            total_tokens=response.total_tokens,
        )

        return {
            "message": MessageDTO_Agent.model_validate(assistant_msg).model_dump(),
            "run": RunDTO.model_validate(run_entity).model_dump() if run_entity else None,
        }


def _sse_event(event: str, data: dict) -> str:
    """Format an SSE event string."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
