# input: SQLAlchemy AsyncSession, ConversationModel ORM
# output: SQLAlchemyConversationRepository 仓储实现
# owner: unknown
# pos: 基础设施层 - 对话仓储 SQLAlchemy 实现；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""SQLAlchemy-backed repository for conversations."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.conversation.entity import Conversation
from domain.conversation.exceptions import ConversationNotFoundException
from domain.conversation.repository import ConversationRepository
from infrastructure.models.conversation import ConversationModel
from infrastructure.repositories.base_repository import execute_targeted_update
from infrastructure.repositories.mixins import SoftDeleteFilterMixin


class SQLAlchemyConversationRepository(SoftDeleteFilterMixin, ConversationRepository):
    """Persist conversation aggregates using SQLAlchemy ORM."""

    model_class = ConversationModel

    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, model: ConversationModel) -> Conversation:
        return Conversation(
            id=model.id,
            title=model.title,
            system_prompt=model.system_prompt,
            model=model.model,
            status=model.status,
            metadata=dict(model.extra_metadata or {}),
            owner_id=model.owner_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )

    def _apply_filters(
        self, query, *, owner_id: Optional[int] = None, status: Optional[str] = None
    ):
        query = super()._apply_filters(query)  # mixin: excludes soft-deleted
        if owner_id is not None:
            query = query.where(ConversationModel.owner_id == owner_id)
        if status:
            query = query.where(ConversationModel.status == status)
        return query

    async def create(self, conversation: Conversation) -> Conversation:
        model = ConversationModel(
            title=conversation.title,
            system_prompt=conversation.system_prompt,
            model=conversation.model,
            status=conversation.status,
            extra_metadata=conversation.metadata or {},
            owner_id=conversation.owner_id,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            deleted_at=conversation.deleted_at,
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def update(self, conversation: Conversation) -> Conversation:
        # owner_id 不随更新改写
        await execute_targeted_update(
            self.session,
            ConversationModel,
            conversation.id,
            {
                "title": conversation.title,
                "system_prompt": conversation.system_prompt,
                "model": conversation.model,
                "status": conversation.status,
                "extra_metadata": conversation.metadata or {},
                "updated_at": conversation.updated_at,
                "deleted_at": conversation.deleted_at,
            },
            not_found=lambda: ConversationNotFoundException(conversation.id),
        )
        return conversation

    async def get_by_id(
        self, conversation_id: int, *, include_deleted: bool = False
    ) -> Optional[Conversation]:
        query = select(ConversationModel).where(ConversationModel.id == conversation_id)
        if not include_deleted:
            query = self._filter_active(query)
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list(
        self,
        *,
        owner_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Conversation]:
        query = select(ConversationModel)
        query = self._apply_filters(query, owner_id=owner_id, status=status)
        query = query.order_by(
            ConversationModel.updated_at.desc(),
            ConversationModel.id.desc(),
        )
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count(
        self, *, owner_id: Optional[int] = None, status: Optional[str] = None
    ) -> int:
        query = select(func.count()).select_from(ConversationModel)
        query = self._apply_filters(query, owner_id=owner_id, status=status)
        result = await self.session.execute(query)
        return int(result.scalar() or 0)
