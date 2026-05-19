# input: PresignUploadRequestDTO/CompleteUploadRequestDTO/UploadFile, FileAssetApplicationService, IdempotencyContext
# output: /storage 路由（presign-upload, complete, upload）
# owner: wanhua.gu
# pos: 表示层路由 - 文件存储/直传相关 HTTP 接口；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""存储/文件上传相关路由。"""

from __future__ import annotations

from typing import AsyncIterator

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
)

from api.dependencies import get_file_asset_service
from api.utils.idempotency import IdempotencyContext, idempotency_for
from application.dto import (
    PresignUploadRequestDTO,
    CompleteUploadRequestDTO,
    StorageUploadResponseDTO,
    PresignUploadResponseDTO,
    PresignUploadDetailDTO,
    FileAssetSummaryDTO,
)
from application.services.file_asset_service import FileAssetApplicationService
from core.response import (
    Response as ApiResponse,
    success_response,
)
from core.i18n import t


router = APIRouter(
    prefix="/storage",
    tags=["文件存储"],
)


async def _build_presign_response(
    service: FileAssetApplicationService,
    payload: PresignUploadRequestDTO,
    file_summary: FileAssetSummaryDTO,
    *,
    presigned=None,
) -> ApiResponse[PresignUploadResponseDTO]:
    """Assemble the presign response. Mints a fresh URL on cache hit (presigned=None)."""
    if presigned is None:
        presigned = await service.generate_upload_presign(
            key=file_summary.key,
            method=payload.method,
            content_type=file_summary.content_type,
            expires_in=payload.expires_in,
        )
    response_data = PresignUploadResponseDTO(
        file=file_summary,
        upload=PresignUploadDetailDTO(
            url=presigned.url,
            method=presigned.method,
            headers=presigned.headers,
            fields=presigned.fields,
            expires_in=presigned.expires_in,
        ),
    )
    return success_response(data=response_data, message=t("storage.presign.success"))


@router.post(
    "/presign-upload",
    summary="生成直传预签名",
    response_model=ApiResponse[PresignUploadResponseDTO],
)
async def presign_upload(
    payload: PresignUploadRequestDTO,
    service: FileAssetApplicationService = Depends(get_file_asset_service),
    idem: IdempotencyContext = Depends(idempotency_for("storage:presign-upload")),
):
    request_hash = idem.request_hash(payload.model_dump(by_alias=True, exclude_none=True))

    cached = await idem.lookup(request_hash)
    if cached is not None:
        return await _build_presign_response(
            service, payload, FileAssetSummaryDTO.model_validate(cached)
        )

    try:
        file_summary, presigned = await service.presign_upload(
            user_id=None,
            filename=payload.filename,
            mime_type=payload.mime_type,
            size_bytes=payload.size_bytes,
            kind=payload.kind,
            method=payload.method or "PUT",
            expires_in=payload.expires_in,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await idem.persist(request_hash, file_summary.model_dump(mode="json"))
    return await _build_presign_response(service, payload, file_summary, presigned=presigned)


@router.post(
    "/complete",
    summary="直传完成确认",
    response_model=ApiResponse[dict],
)
async def confirm_presigned_upload(
    payload: CompleteUploadRequestDTO,
    service: FileAssetApplicationService = Depends(get_file_asset_service),
):
    try:
        payload.ensure_identifier()
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=400, detail=t("file.identifier.missing")) from exc

    if payload.id is not None:
        asset = await service.get_asset_raw(payload.id)
    elif payload.key:
        asset = await service.get_asset_by_key_raw(payload.key)
    else:  # pragma: no cover - already guarded
        raise HTTPException(status_code=400, detail=t("file.identifier.missing"))

    # No permission check

    await service.confirm_direct_upload(asset_id=asset.id)

    return success_response(data={"ok": True}, message=t("file.activate.success"))


@router.post(
    "/upload",
    summary="中转上传单个文件",
    response_model=ApiResponse[StorageUploadResponseDTO],
)
async def upload_file(
    file: UploadFile = File(..., description="要上传的文件"),
    kind: str = Query("uploads", description="业务分类（如 avatar、document 等）"),
    service: FileAssetApplicationService = Depends(get_file_asset_service),
):
    """由应用服务器中转上传文件到对象存储（编排已下沉到 Application Service）。"""

    async def _iter_chunks(
        upload: UploadFile, *, chunk_size: int = 1024 * 1024
    ) -> AsyncIterator[bytes]:
        while True:
            chunk = await upload.read(chunk_size)
            if not chunk:
                break
            yield chunk

    resp = await service.relay_upload_stream(
        user_id=None,  # No user tracking
        file_stream=_iter_chunks(file),
        filename=file.filename or "upload.bin",
        kind=kind,
        content_type=file.content_type,
    )
    return success_response(data=resp, message=t("file.upload.success"))
