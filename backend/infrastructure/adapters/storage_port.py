# input: infrastructure.external.storage 的 StorageProvider 实现
# output: StorageProviderPortAdapter（实现 application StoragePort；流式上传中断自动 abort multipart）
# pos: 基础设施层 - 存储端口适配器，应用层与具体 provider 的转换边界；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Infrastructure adapter that implements the application StoragePort
by delegating to the concrete StorageProvider and translating models.
"""

from __future__ import annotations

from typing import AsyncIterator, Optional

from application.ports.storage import StoragePort
from application.ports.storage import (
    PresignedURL,
    ObjectMetadata,
    StorageInfo,
    UploadOutcome,
)
from core.logging_config import get_logger
from infrastructure.external.storage import StorageProvider
from infrastructure.external.storage.base import AdvancedStorageProvider

logger = get_logger(__name__)

_PART_SIZE = 5 * 1024 * 1024


class _MultipartState:
    """Mutable pump state shared across upload_stream helpers (also visible to the abort path)."""

    __slots__ = ("buffer", "total", "upload_id", "parts")

    def __init__(self) -> None:
        self.buffer = bytearray()
        self.total = 0
        self.upload_id: Optional[str] = None
        self.parts: list[dict[str, int | str]] = []


async def _abort_multipart_quietly(provider: StorageProvider, upload_id: str, key: str) -> None:
    """Best-effort abort：失败仅告警，绝不掩盖调用方正在传播的原始异常。"""
    try:
        await provider.multipart_upload_abort(upload_id, key)  # type: ignore[attr-defined]
    except Exception as abort_exc:
        logger.warning(
            "multipart_upload_abort_failed",
            key=key,
            upload_id=upload_id,
            error=str(abort_exc),
        )


class StorageProviderPortAdapter(StoragePort):
    def __init__(self, provider: StorageProvider):
        self.provider = provider

    def info(self) -> StorageInfo:
        cfg = getattr(self.provider, "config", None)
        stype = getattr(cfg, "type", None)
        bucket = getattr(cfg, "bucket", None)
        region = getattr(cfg, "region", None)
        if hasattr(stype, "value"):
            stype_value = str(getattr(stype, "value"))
        else:
            stype_value = str(stype) if stype is not None else ""
        return StorageInfo(type=stype_value, bucket=bucket, region=region)

    async def delete(self, key: str) -> bool:
        return await self.provider.delete(key)

    async def download(self, key: str) -> bytes:
        return await self.provider.download(key)

    async def get_metadata(self, key: str) -> ObjectMetadata:
        meta = await self.provider.get_metadata(key)
        return ObjectMetadata(
            etag=getattr(meta, "etag", None),
            content_type=getattr(meta, "content_type", None),
            size=int(getattr(meta, "size", 0) or 0),
            custom_metadata=dict(getattr(meta, "custom_metadata", {}) or {}),
        )

    async def generate_presigned_url(
        self,
        key: str,
        expires_in: int = 3600,
        method: str = "GET",
        content_type: Optional[str] = None,
        response_content_disposition: Optional[str] = None,
        response_content_type: Optional[str] = None,
    ) -> PresignedURL:
        presigned = await self.provider.generate_presigned_url(
            key,
            expires_in,
            method,
            content_type,
            response_content_disposition=response_content_disposition,
            response_content_type=response_content_type,
        )
        return PresignedURL(
            url=getattr(presigned, "url", ""),
            method=getattr(presigned, "method", method),
            expires_in=int(getattr(presigned, "expires_in", expires_in) or expires_in),
            headers=dict(getattr(presigned, "headers", {}) or {}),
            fields=dict(getattr(presigned, "fields", {}) or {}),
        )

    def public_url(self, key: str) -> Optional[str]:
        return self.provider.public_url(key)

    async def upload_stream(
        self,
        stream: AsyncIterator[bytes],
        key: str,
        metadata: Optional[dict] = None,
        content_type: Optional[str] = None,
    ) -> UploadOutcome:
        state = _MultipartState()
        try:
            await self._pump_stream(stream, key, content_type, state)

            if state.upload_id is None:
                # Small file: do a normal upload to preserve metadata when possible.
                result = await self.provider.upload(
                    bytes(state.buffer), key, metadata=metadata, content_type=content_type
                )
                return UploadOutcome(
                    key=getattr(result, "key", key),
                    etag=getattr(result, "etag", None),
                    size=int(getattr(result, "size", state.total) or state.total),
                    content_type=getattr(result, "content_type", content_type),
                    url=getattr(result, "url", None),
                )

            if state.buffer:
                await self._flush_part(key, state, bytes(state.buffer))

            result = await self.provider.multipart_upload_complete(  # type: ignore[attr-defined]
                state.upload_id, key, state.parts
            )
        except BaseException:
            # 源流中断（如超限截断/客户端断连取消）或分片失败：已开启的 multipart 会话
            # 不 abort 就会在对象存储侧长期挂着占空间。best-effort abort，失败仅告警。
            if state.upload_id is not None:
                await _abort_multipart_quietly(self.provider, state.upload_id, key)
            raise

        return UploadOutcome(
            key=getattr(result, "key", key),
            etag=getattr(result, "etag", None),
            size=state.total,
            content_type=content_type,
            url=getattr(result, "url", None),
        )

    async def _pump_stream(
        self,
        stream: AsyncIterator[bytes],
        key: str,
        content_type: Optional[str],
        state: "_MultipartState",
    ) -> None:
        """Read the stream into ``state``; escalate to multipart past the part-size threshold."""
        async for chunk in stream:
            if not chunk:
                continue
            state.total += len(chunk)
            state.buffer.extend(chunk)

            if state.upload_id is None:
                if len(state.buffer) < _PART_SIZE:
                    continue
                if not isinstance(self.provider, AdvancedStorageProvider):
                    raise RuntimeError("Provider does not support multipart upload")
                state.upload_id = await self.provider.multipart_upload_start(
                    key, content_type=content_type
                )

            while len(state.buffer) >= _PART_SIZE:
                part = bytes(state.buffer[:_PART_SIZE])
                del state.buffer[:_PART_SIZE]
                await self._flush_part(key, state, part)

    async def _flush_part(self, key: str, state: "_MultipartState", data: bytes) -> None:
        part_number = len(state.parts) + 1
        etag = await self.provider.multipart_upload_part(  # type: ignore[attr-defined]
            key, state.upload_id, part_number, data
        )
        state.parts.append({"PartNumber": part_number, "ETag": etag})
