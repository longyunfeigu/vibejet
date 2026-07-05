# input: SQLAlchemy AsyncSession, FileAssetModel ORM
# output: SQLAlchemyFileAssetRepository 仓储实现
# owner: wanhua.gu
# pos: 基础设施层 - 文件资源仓储 SQLAlchemy 实现；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""SQLAlchemy-backed repository for file assets."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from domain.file_asset import FileAsset, FileAssetRepository
from domain.common.exceptions import FileAssetKeyConflictException, FileAssetNotFoundException
from infrastructure.models.file_asset import FileAssetModel
from infrastructure.repositories.base_repository import execute_targeted_update
from infrastructure.repositories.mixins import SoftDeleteFilterMixin


class SQLAlchemyFileAssetRepository(SoftDeleteFilterMixin, FileAssetRepository):
    """Persist file asset aggregates using SQLAlchemy ORM."""

    model_class = FileAssetModel

    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, model: FileAssetModel) -> FileAsset:
        return FileAsset(
            id=model.id,
            owner_id=model.owner_id,
            storage_type=model.storage_type,
            bucket=model.bucket,
            region=model.region,
            key=model.key,
            size=model.size,
            etag=model.etag,
            content_type=model.content_type,
            original_filename=model.original_filename,
            kind=model.kind,
            is_public=model.is_public,
            metadata=dict(model.extra_metadata or {}),
            url=model.url,
            status=model.status,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )

    def _apply_filters(
        self,
        query,
        *,
        owner_id: Optional[int] = None,
        kind: Optional[str] = None,
        status: Optional[str] = None,
    ):
        query = super()._apply_filters(query)  # mixin: excludes soft-deleted
        if owner_id is not None:
            query = query.where(FileAssetModel.owner_id == owner_id)
        if kind:
            query = query.where(FileAssetModel.kind == kind)
        if status:
            query = query.where(FileAssetModel.status == status)
        return query

    async def create(self, asset: FileAsset) -> FileAsset:
        model = FileAssetModel(
            owner_id=asset.owner_id,
            storage_type=asset.storage_type,
            bucket=asset.bucket,
            region=asset.region,
            key=asset.key,
            size=asset.size,
            etag=asset.etag,
            content_type=asset.content_type,
            original_filename=asset.original_filename,
            kind=asset.kind,
            is_public=asset.is_public,
            extra_metadata=asset.metadata or {},
            url=asset.url,
            status=asset.status,
            created_at=asset.created_at,
            updated_at=asset.updated_at,
            deleted_at=asset.deleted_at,
        )
        self.session.add(model)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            # 应用层 get_by_key 预检在并发下存在 check-then-act 窗口；
            # uq_file_assets_key 兜底后映射回域异常，而不是裸 500
            raise FileAssetKeyConflictException(asset.key) from exc
        await self.session.refresh(model)
        return self._to_entity(model)

    async def update(self, asset: FileAsset) -> FileAsset:
        await execute_targeted_update(
            self.session,
            FileAssetModel,
            asset.id,
            {
                "owner_id": asset.owner_id,
                "storage_type": asset.storage_type,
                "bucket": asset.bucket,
                "region": asset.region,
                "key": asset.key,
                "size": asset.size,
                "etag": asset.etag,
                "content_type": asset.content_type,
                "original_filename": asset.original_filename,
                "kind": asset.kind,
                "is_public": asset.is_public,
                "extra_metadata": asset.metadata or {},
                "url": asset.url,
                "status": asset.status,
                "updated_at": asset.updated_at,
                "deleted_at": asset.deleted_at,
            },
            not_found=lambda: FileAssetNotFoundException(asset.id),
        )
        return asset

    async def get_by_id(
        self, asset_id: int, *, include_deleted: bool = False
    ) -> Optional[FileAsset]:
        query = select(FileAssetModel).where(FileAssetModel.id == asset_id)
        if not include_deleted:
            query = self._filter_active(query)
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_key(self, key: str, *, include_deleted: bool = False) -> Optional[FileAsset]:
        query = select(FileAssetModel).where(FileAssetModel.key == key)
        if not include_deleted:
            query = self._filter_active(query)
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list(
        self,
        *,
        owner_id: Optional[int] = None,
        kind: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[FileAsset]:
        query = select(FileAssetModel)
        query = self._apply_filters(
            query,
            owner_id=owner_id,
            kind=kind,
            status=status,
        )
        query = query.order_by(
            FileAssetModel.created_at.desc(),
            FileAssetModel.id.desc(),
        )
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models]

    async def count(
        self,
        *,
        owner_id: Optional[int] = None,
        kind: Optional[str] = None,
        status: Optional[str] = None,
    ) -> int:
        query = select(func.count()).select_from(FileAssetModel)
        query = self._apply_filters(
            query,
            owner_id=owner_id,
            kind=kind,
            status=status,
        )
        result = await self.session.execute(query)
        return int(result.scalar() or 0)
