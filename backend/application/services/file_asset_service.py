"""Application layer orchestration for file asset lifecycle (application/services)."""

from __future__ import annotations

from os.path import splitext
from typing import Any, AsyncIterator, Callable, Optional, Protocol, Tuple

from application.dto import FileAssetDTO, FileAssetSummaryDTO, StorageUploadResponseDTO
from application.ports.storage import (
    ObjectMetadata,
    PresignedURL,
    StorageInfo,
    StorageObjectNotFoundError,
    StoragePort,
)
from application.utils.storage import build_storage_key, guess_content_type
from application.utils.time import utcnow
from core.config import settings
from core.logging_config import get_logger
from domain.common.exceptions import (
    BusinessException,
    DomainValidationException,
    FileAssetAlreadyDeletedException,
    FileAssetNotFoundException,
    FileNotUploadedException,
    FileTooLargeException,
    FileUploadClosedException,
    InvalidFileNameException,
    UnsupportedMimeTypeException,
)
from domain.file_asset import FileAsset
from domain.file_asset.repository import FileAssetRepository

logger = get_logger(__name__)


class FileAssetUnitOfWork(Protocol):
    @property
    def file_asset_repository(self) -> FileAssetRepository: ...

    async def __aenter__(self) -> "FileAssetUnitOfWork": ...

    async def __aexit__(self, exc_type, exc, tb) -> None: ...

    async def commit(self) -> None: ...


def _sanitize_filename_for_header(filename: Optional[str], *, fallback: str) -> str:
    if not filename:
        return fallback
    cleaned = filename.replace("\r", " ").replace("\n", " ").strip()
    cleaned = cleaned.replace('"', "")
    return cleaned or fallback


def _build_content_disposition(mode: str, filename: Optional[str], *, fallback: str) -> str:
    safe = _sanitize_filename_for_header(filename, fallback=fallback)
    return f'{mode}; filename="{safe}"'


def _user_id_for_key(user_id: Optional[int]) -> Optional[str]:
    return str(user_id) if user_id is not None else None


def _declared_size(size: Any) -> Optional[int]:
    """客户端声明的大小；0/缺失/非整数视为未声明（与 presign 校验口径一致）。"""
    if isinstance(size, int) and not isinstance(size, bool) and size > 0:
        return size
    return None


def _media_type(content_type: Optional[str]) -> Optional[str]:
    """``text/plain; charset=utf-8`` → ``text/plain``：存储回报的类型可能带参数。"""
    if not content_type:
        return None
    return content_type.split(";", 1)[0].strip().lower() or None


def _direct_upload_violation(
    meta: ObjectMetadata, *, expected_size: Any, fallback_content_type: Optional[str]
) -> Optional[BusinessException]:
    """按 presign 同一套策略校验存储里的真实对象；合规返回 None。

    presign 只校验客户端声明的 size/type，真实上传内容由客户端决定，必须在确认时
    用存储 HEAD 回来的真实值复核，否则声明与实际不符的对象会被直接激活。
    """
    actual_size = meta.size
    presign_max = settings.storage.presign_max_size
    if presign_max and actual_size > presign_max:
        return FileTooLargeException(size=actual_size, max_size=presign_max)

    # expected_size=0 与 presign 一致视为"未声明"（presign 对 0 也不做上限校验）
    declared = _declared_size(expected_size)
    if declared is not None:
        if actual_size > declared:
            return FileTooLargeException(size=actual_size, max_size=declared)
        if actual_size < declared:
            return DomainValidationException(
                "Uploaded size does not match declared size",
                field="size_bytes",
                details={"expected_size": declared, "actual_size": actual_size},
                message_key="validation.failed",
                format_params={"reason": "uploaded size does not match size_bytes"},
            )

    allowed_types = settings.storage.presign_content_types
    actual_type = meta.content_type or fallback_content_type
    if allowed_types and actual_type:
        allowed = {_media_type(t) for t in allowed_types}
        if _media_type(actual_type) not in allowed:
            return UnsupportedMimeTypeException(actual_type)
    return None


def _limit_stream(
    stream: AsyncIterator[bytes],
    *,
    max_bytes: int,
) -> AsyncIterator[bytes]:
    async def _gen() -> AsyncIterator[bytes]:
        seen = 0
        async for chunk in stream:
            if not chunk:
                continue
            seen += len(chunk)
            if max_bytes and seen > max_bytes:
                raise FileTooLargeException(size=seen, max_size=max_bytes)
            yield chunk

    return _gen()


class FileAssetApplicationService:
    """High-level file asset workflows bridging API and domain layers."""

    def __init__(
        self, uow_factory: Callable[..., FileAssetUnitOfWork], storage: StoragePort | None = None
    ):
        self._uow_factory = uow_factory
        self._storage = storage

    # ------------------------------------------------------------------
    # DTO helpers
    # ------------------------------------------------------------------
    def _to_dto(self, asset: FileAsset) -> FileAssetDTO:
        return FileAssetDTO.model_validate(asset)

    def _to_summary(self, asset: FileAsset) -> FileAssetSummaryDTO:
        assert asset.id is not None  # 只对已持久化实体做摘要
        return FileAssetSummaryDTO(
            id=asset.id,
            key=asset.key,
            status=asset.status,
            original_filename=asset.original_filename,
            content_type=asset.content_type,
            etag=asset.etag,
            size=asset.size,
            url=asset.url,
        )

    # ------------------------------------------------------------------
    # Workflow operations
    # ------------------------------------------------------------------
    async def create_pending_asset(
        self,
        *,
        owner_id: Optional[int],
        storage_type: str,
        bucket: Optional[str],
        region: Optional[str],
        key: str,
        original_filename: Optional[str],
        content_type: Optional[str],
        kind: Optional[str],
        metadata: Optional[dict[str, Any]] = None,
    ) -> FileAssetSummaryDTO:
        now = utcnow()
        asset = FileAsset(
            id=None,
            owner_id=owner_id,
            storage_type=storage_type,
            bucket=bucket,
            region=region,
            key=key,
            size=0,
            etag=None,
            content_type=content_type,
            original_filename=original_filename,
            kind=kind,
            is_public=False,
            metadata=metadata or {},
            url=None,
            status="pending",
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )
        async with self._uow_factory() as uow:
            created = await uow.file_asset_repository.create(asset)
            return self._to_summary(created)

    # ---------------------- Orchestration with Storage ----------------------
    async def confirm_direct_upload(
        self,
        *,
        asset_id: Optional[int] = None,
        key: Optional[str] = None,
        owner_id: int,
    ) -> FileAssetDTO:
        """Confirm client direct upload by reconciling metadata from storage."""
        if self._storage is None:
            raise RuntimeError("Storage port not configured for FileAssetApplicationService")

        # 三段式（同 chat/document 的既有纪律）：数据库事务不得跨存储网络调用，
        # 否则连接被钉住整个存储往返，并发确认下有池耗尽风险。
        # tx-1：短只读事务完成加载 + 归属校验
        asset = await self._load_owned_for_confirm(asset_id=asset_id, key=key, owner_id=owner_id)

        # 无事务：存储元数据 HEAD（网络往返）
        try:
            meta = await self._storage.get_metadata(asset.key)
        except StorageObjectNotFoundError as exc:
            # 客户端在对象落盘前就调了 complete：可重试的状态冲突（409），而非 500
            raise FileNotUploadedException(asset_id, key=key) from exc

        violation = _direct_upload_violation(
            meta,
            expected_size=(asset.metadata or {}).get("expected_size"),
            fallback_content_type=asset.content_type,
        )
        if violation is not None:
            await self._reject_direct_upload(asset, owner_id=owner_id)
            raise violation

        public_url = self._storage.public_url(asset.key)

        # tx-2：重新加载并应用元数据（确认幂等；期间被删/易主则同 404）
        return await self._activate_direct_upload(
            asset, meta, public_url, asset_id=asset_id, key=key, owner_id=owner_id
        )

    async def _load_owned_for_confirm(
        self, *, asset_id: Optional[int], key: Optional[str], owner_id: int
    ) -> FileAsset:
        async with self._uow_factory(readonly=True) as uow:
            repo = uow.file_asset_repository
            asset: Optional[FileAsset] = None
            if asset_id is not None:
                asset = await repo.get_by_id(asset_id)
            if asset is None and key:
                asset = await repo.get_by_key(key)
            if asset is None:
                raise FileAssetNotFoundException(asset_id, key=key)
            self._ensure_owned(
                asset, owner_id, not_found=FileAssetNotFoundException(asset_id, key=key)
            )
            return asset

    async def _activate_direct_upload(
        self,
        asset: FileAsset,
        meta: ObjectMetadata,
        public_url: Optional[str],
        *,
        asset_id: Optional[int],
        key: Optional[str],
        owner_id: int,
    ) -> FileAssetDTO:
        async with self._uow_factory() as uow:
            repo = uow.file_asset_repository
            current = await repo.get_by_id(asset.id) if asset.id is not None else None
            if current is None:
                raise FileAssetNotFoundException(asset_id, key=key)
            self._ensure_owned(
                current, owner_id, not_found=FileAssetNotFoundException(asset_id, key=key)
            )

            current.update_object_metadata(
                size=meta.size,
                etag=meta.etag,
                content_type=meta.content_type or current.content_type,
                url=public_url,
                metadata=meta.custom_metadata or current.metadata,
            )
            current.mark_active()
            # 激活会清 deleted_at：守卫写，重载与写入之间被并发软删则 404，而不是复活
            try:
                updated = await repo.update_if_not_deleted(current)
            except FileAssetNotFoundException:
                # 与本方法其他 404 分支同标识构造（D1：不泄露 asset_id）
                raise FileAssetNotFoundException(asset_id, key=key) from None
            return self._to_dto(updated)

    async def _reject_direct_upload(self, asset: FileAsset, *, owner_id: int) -> None:
        """不合规直传：best-effort 删存储对象，并把资产软删（不留可被再次确认的 pending）。"""
        assert self._storage is not None
        try:
            await self._storage.delete(asset.key)
        except Exception as exc:
            logger.warning("direct_upload_reject_delete_failed", key=asset.key, error=str(exc))

        async with self._uow_factory() as uow:
            repo = uow.file_asset_repository
            current = await repo.get_by_id(asset.id) if asset.id is not None else None
            if current is None or not current.belongs_to(owner_id):
                return
            current.mark_deleted()
            await repo.update(current)

    async def generate_access_url_by_info(
        self,
        *,
        key: str,
        content_type: Optional[str],
        filename: Optional[str],
        expires_in: int,
        disposition_mode: str = "inline",
    ) -> dict[str, int | str]:
        """Generate signed access URL for given file info (no DB lookup)."""
        if self._storage is None:
            raise RuntimeError("Storage port not configured for FileAssetApplicationService")

        if filename:
            disposition = _build_content_disposition(disposition_mode, filename, fallback="file")
        else:
            disposition = disposition_mode

        presigned = await self._storage.generate_presigned_url(
            key=key,
            expires_in=expires_in,
            method="GET",
            content_type=content_type,
            response_content_disposition=disposition,
            # response_content_type intentionally omitted for OSS
        )
        return {"url": presigned.url, "expires_in": presigned.expires_in}

    async def generate_access_url_for_asset(
        self,
        *,
        asset: FileAsset,
        expires_in: int,
        filename: Optional[str],
        disposition_mode: str,
    ) -> dict[str, int | str]:
        """Generate public or signed URL for a specific asset."""
        if self._storage is None:
            raise RuntimeError("Storage port not configured for FileAssetApplicationService")

        # If object is public and we can derive a stable URL, return it directly
        if asset.is_public:
            public_url = self._storage.public_url(asset.key)
            if public_url:
                return {"url": public_url, "expires_in": expires_in}

        # Build content type and disposition for signed access
        fname = filename or asset.original_filename or f"file-{asset.id}"
        content_type = asset.content_type or guess_content_type(fname)
        disposition = _build_content_disposition(
            disposition_mode,
            fname,
            fallback=f"file-{asset.id or 0}",
        )

        presigned = await self._storage.generate_presigned_url(
            key=asset.key,
            expires_in=expires_in,
            method="GET",
            content_type=content_type,
            response_content_disposition=disposition,
        )
        return {"url": presigned.url, "expires_in": presigned.expires_in}

    async def presign_upload(
        self,
        *,
        user_id: Optional[int],
        filename: str,
        mime_type: Optional[str],
        size_bytes: int,
        kind: str,
        method: str = "PUT",
        expires_in: int = 600,
    ):
        """Prepare client direct-upload: generate presigned request and persist pending asset."""
        if self._storage is None:
            raise RuntimeError("Storage port not configured for FileAssetApplicationService")

        method = method or "PUT"
        if method not in {"PUT", "POST"}:
            raise DomainValidationException(
                "Invalid upload method",
                field="method",
                details={"method": method},
                message_key="storage.method.invalid",
            )

        # Basic validations
        fname = filename or "upload.bin"
        if len(fname) > 255:
            raise InvalidFileNameException(fname, max_len=255)

        _, ext = splitext(fname)
        content_type = mime_type or guess_content_type(fname)

        # Check allowed MIME types (presign context)
        allowed_types = settings.storage.presign_content_types
        if allowed_types and content_type and content_type not in allowed_types:
            raise UnsupportedMimeTypeException(content_type)

        # Check presign size limit
        presign_max = settings.storage.presign_max_size
        if presign_max and size_bytes and size_bytes > presign_max:
            raise FileTooLargeException(size=size_bytes, max_size=presign_max)
        key = build_storage_key(kind=kind, user_id=_user_id_for_key(user_id), ext=ext)

        try:
            presigned: PresignedURL = await self._storage.generate_presigned_url(
                key=key,
                expires_in=expires_in,
                method=method,
                content_type=content_type,
                content_length=_declared_size(size_bytes),
            )
        except ValueError as exc:
            # Normalize to domain-level validation error for i18n handling
            raise DomainValidationException(
                "Validation failed",
                details={"reason": str(exc)},
                message_key="validation.failed",
                format_params={"reason": str(exc)},
            ) from exc

        info: StorageInfo = self._storage.info()
        file_summary = await self.create_pending_asset(
            owner_id=user_id,
            storage_type=info.type,
            bucket=info.bucket,
            region=info.region,
            key=key,
            original_filename=filename,
            content_type=content_type,
            kind=kind,
            metadata={
                "expected_size": size_bytes,
                "upload_method": method,
            },
        )

        return file_summary, presigned

    async def generate_upload_presign(
        self,
        *,
        asset_id: int,
        owner_id: int,
        method: str,
        expires_in: int,
    ) -> PresignedURL:
        """为仍处于 pending 的已有资产重新签发上传链接（幂等重放用）。

        key / content_type / 声明大小一律取库里的资产，而不是客户端缓存的摘要；
        资产一旦确认（active）或删除就不再签发写链接，否则重放即可覆盖已通过
        确认期复核的对象。
        """
        if self._storage is None:
            raise RuntimeError("Storage port not configured for FileAssetApplicationService")
        method = method or "PUT"
        if method not in {"PUT", "POST"}:
            raise DomainValidationException(
                "Invalid upload method",
                field="method",
                details={"method": method},
                message_key="storage.method.invalid",
            )

        async with self._uow_factory(readonly=True) as uow:
            # 含已软删：已删资产要给 409（上传已关闭），而不是 404
            asset = await uow.file_asset_repository.get_by_id(asset_id, include_deleted=True)
            if asset is None:
                raise FileAssetNotFoundException(asset_id)
            self._ensure_owned(asset, owner_id, not_found=FileAssetNotFoundException(asset_id))
            if asset.status != "pending":
                raise FileUploadClosedException(asset_id)

        return await self._storage.generate_presigned_url(
            key=asset.key,
            expires_in=expires_in,
            method=method,
            content_type=asset.content_type,
            content_length=_declared_size((asset.metadata or {}).get("expected_size")),
        )

    async def relay_upload_stream(
        self,
        *,
        user_id: Optional[int],
        file_stream: AsyncIterator[bytes],
        filename: str,
        kind: str,
        content_type: Optional[str] = None,
        size_hint: Optional[int] = None,
    ) -> StorageUploadResponseDTO:
        """Server-side relay upload with streaming body to reduce peak memory usage."""
        if self._storage is None:
            raise RuntimeError("Storage port not configured for FileAssetApplicationService")

        # 与 presign 同一套长度约束（对齐 file_assets 列宽），否则超长值在落库时才炸成 500
        if filename and len(filename) > 255:
            raise InvalidFileNameException(filename, max_len=255)

        _, ext = splitext(filename or "")
        ctype = content_type or guess_content_type(filename or "")
        if ctype and len(ctype) > 100:
            raise UnsupportedMimeTypeException(ctype)

        max_size = settings.storage.max_file_size
        if settings.storage.validation_enabled:
            if max_size and size_hint and size_hint > max_size:
                raise FileTooLargeException(size=size_hint, max_size=max_size)
            allowed = settings.storage.allowed_types
            if allowed and ctype and ctype not in allowed:
                raise UnsupportedMimeTypeException(ctype)

        key = build_storage_key(kind=kind, user_id=_user_id_for_key(user_id), ext=ext)

        stream: AsyncIterator[bytes] = file_stream
        if settings.storage.validation_enabled and max_size:
            stream = _limit_stream(stream, max_bytes=max_size)

        meta = {"filename": filename or ""}
        outcome = await self._storage.upload_stream(stream, key, metadata=meta, content_type=ctype)

        info = self._storage.info()
        db_url = self._storage.public_url(outcome.key)

        asset_dto = await self._persist_relay_upload(
            owner_id=user_id,
            storage_type=info.type,
            bucket=info.bucket,
            region=info.region,
            key=outcome.key,
            original_filename=filename or None,
            content_type=outcome.content_type or ctype,
            kind=kind,
            size=outcome.size,
            etag=outcome.etag,
            url=db_url,
            metadata={"upload_source": "relay", "filename": filename or ""},
        )

        return StorageUploadResponseDTO(
            key=outcome.key,
            etag=outcome.etag,
            size=outcome.size,
            content_type=outcome.content_type or ctype,
            url=outcome.url,
            file_id=asset_dto.id,
            file_status=asset_dto.status,
        )

    async def _persist_relay_upload(self, **asset_kwargs: Any) -> FileAssetDTO:
        """Upsert DB record for an object already written to storage.

        DB 写入失败时对象会变孤儿（UoW 只回滚 DB）：best-effort 删掉已上传对象，
        删除失败仅记 warning，不掩盖原始异常。
        """
        try:
            return await self.upsert_active_asset(**asset_kwargs)
        except BaseException:
            # BaseException：客户端断连的 CancelledError 是 relay 中断的常见形态，同样要清孤儿
            key = asset_kwargs.get("key")
            try:
                if key and self._storage is not None:
                    await self._storage.delete(key)
                    logger.warning("relay_upload_db_failed_object_cleaned", key=key)
            except Exception as cleanup_exc:
                logger.warning(
                    "relay_upload_orphan_object",
                    key=key,
                    cleanup_error=str(cleanup_exc),
                )
            raise

    async def upsert_active_asset(
        self,
        *,
        owner_id: Optional[int],
        storage_type: str,
        bucket: Optional[str],
        region: Optional[str],
        key: str,
        original_filename: Optional[str],
        content_type: Optional[str],
        kind: Optional[str],
        size: int,
        etag: Optional[str],
        url: Optional[str],
        metadata: Optional[dict[str, Any]] = None,
    ) -> FileAssetDTO:
        async with self._uow_factory() as uow:
            repo = uow.file_asset_repository
            # 需要含已软删的记录：key 唯一约束下，重传同 key 必须命中老记录复活，否则会 IntegrityError
            asset = await repo.get_by_key(key, include_deleted=True)
            if asset is None:
                now = utcnow()
                asset = FileAsset(
                    id=None,
                    owner_id=owner_id,
                    storage_type=storage_type,
                    bucket=bucket,
                    region=region,
                    key=key,
                    size=size,
                    etag=etag,
                    content_type=content_type,
                    original_filename=original_filename,
                    kind=kind,
                    is_public=False,
                    metadata=metadata or {},
                    url=url,
                    status="active",
                    created_at=now,
                    updated_at=now,
                    deleted_at=None,
                )
                created = await repo.create(asset)
                return self._to_dto(created)

            asset.owner_id = owner_id
            asset.storage_type = storage_type
            asset.bucket = bucket
            asset.region = region
            asset.original_filename = original_filename or asset.original_filename
            asset.kind = kind or asset.kind
            asset.update_object_metadata(
                size=size,
                etag=etag,
                content_type=content_type,
                url=url,
                metadata=metadata if metadata is not None else asset.metadata,
            )
            asset.mark_active()
            updated = await repo.update(asset)
            return self._to_dto(updated)

    @staticmethod
    def _ensure_owned(
        asset: FileAsset, owner_id: int, *, not_found: FileAssetNotFoundException
    ) -> None:
        """越权与不存在同 404（Epic-1 D1）。not_found 必须与调用方的"不存在"分支
        用相同标识（asset_id vs key）构造，否则两种 404 的 details 不同，泄露资产
        存在性与内部 asset_id。"""
        if not asset.belongs_to(owner_id):
            raise not_found

    async def get_asset_raw(self, asset_id: int, *, owner_id: int) -> FileAsset:
        async with self._uow_factory(readonly=True) as uow:
            asset = await uow.file_asset_repository.get_by_id(asset_id)
            if asset is None:
                raise FileAssetNotFoundException(asset_id)
            self._ensure_owned(asset, owner_id, not_found=FileAssetNotFoundException(asset_id))
            return asset

    async def get_asset_by_key_raw(self, key: str, *, owner_id: int) -> FileAsset:
        async with self._uow_factory(readonly=True) as uow:
            asset = await uow.file_asset_repository.get_by_key(key)
            if asset is None:
                raise FileAssetNotFoundException(key=key)
            self._ensure_owned(asset, owner_id, not_found=FileAssetNotFoundException(key=key))
            return asset

    async def list_assets(
        self,
        *,
        owner_id: int,
        kind: Optional[str],
        status: Optional[str],
        skip: int,
        limit: int,
    ) -> Tuple[list[FileAssetDTO], int]:
        async with self._uow_factory(readonly=True) as uow:
            repo = uow.file_asset_repository
            items = await repo.list(
                owner_id=owner_id,
                kind=kind,
                status=status,
                skip=skip,
                limit=limit,
            )
            total = await repo.count(
                owner_id=owner_id,
                kind=kind,
                status=status,
            )
            return [self._to_dto(item) for item in items], total

    async def soft_delete(self, asset_id: int, *, owner_id: int) -> FileAssetDTO:
        async with self._uow_factory() as uow:
            # 需要看到已软删的记录，才能给出 AlreadyDeleted 而不是 NotFound
            asset = await uow.file_asset_repository.get_by_id(asset_id, include_deleted=True)
            if asset is None:
                raise FileAssetNotFoundException(asset_id)
            # 归属断言先于 AlreadyDeleted：不向非 owner 泄露删除状态
            self._ensure_owned(asset, owner_id, not_found=FileAssetNotFoundException(asset_id))
            if asset.is_deleted():
                raise FileAssetAlreadyDeletedException(asset_id)
            asset.mark_deleted()
            updated = await uow.file_asset_repository.update(asset)
            return self._to_dto(updated)
