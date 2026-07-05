# input: DocumentApplicationService（依赖注入）, FastAPI BackgroundTasks
# output: /api/v1/documents 路由（建档/列表/详情/内容/重解析/软删）
# pos: 表示层 - 文档解析 HTTP 端点（异步解析调度 + 状态轮询）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""文档解析相关路由。

创建/重解析返回即刻响应，解析在 BackgroundTasks 中执行；
客户端通过 GET /documents/{id} 轮询状态，ready 后从 /content 取 Markdown。
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query

from api.dependencies import get_current_user, get_document_service
from application.dto import (
    CreateDocumentDTO,
    DocumentContentDTO,
    DocumentDTO,
    UserDTO,
)
from application.services.document_service import DocumentApplicationService
from core.config import settings
from core.i18n import t
from core.response import (
    PaginatedData,
    Response as ApiResponse,
    paginated_response,
    success_response,
)

# 认证闸门 + 归属校验：文档端点要求登录，且只作用于当前用户的文档（越权 404）
router = APIRouter(
    prefix="/documents",
    tags=["文档解析"],
    dependencies=[Depends(get_current_user)],
)


@router.post(
    "",
    summary="创建文档并触发解析",
    response_model=ApiResponse[DocumentDTO],
)
async def create_document(
    payload: CreateDocumentDTO,
    background_tasks: BackgroundTasks,
    user: UserDTO = Depends(get_current_user),
    service: DocumentApplicationService = Depends(get_document_service),
):
    dto = await service.create_document(payload, owner_id=user.id)
    background_tasks.add_task(service.process_document, dto.id)
    return success_response(dto, message=t("document.create.success"))


@router.get(
    "",
    summary="文档列表",
    response_model=ApiResponse[PaginatedData[DocumentDTO]],
)
async def list_documents(
    page: int = Query(1, ge=1),
    size: int = Query(default=settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE),
    status: Optional[str] = Query(default=None, description="pending/parsing/ready/failed"),
    file_asset_id: Optional[int] = Query(default=None),
    user: UserDTO = Depends(get_current_user),
    service: DocumentApplicationService = Depends(get_document_service),
):
    skip = (page - 1) * size
    items, total = await service.list_documents(
        owner_id=user.id,
        file_asset_id=file_asset_id,
        status=status,
        skip=skip,
        limit=size,
    )
    return paginated_response(items=items, total=total, page=page, size=size)


@router.get(
    "/{document_id}",
    summary="文档详情（状态轮询）",
    response_model=ApiResponse[DocumentDTO],
)
async def get_document(
    document_id: int,
    user: UserDTO = Depends(get_current_user),
    service: DocumentApplicationService = Depends(get_document_service),
):
    dto = await service.get_document(document_id, owner_id=user.id)
    return success_response(dto, message=t("ok"))


@router.get(
    "/{document_id}/content",
    summary="获取解析产物（Markdown）",
    response_model=ApiResponse[DocumentContentDTO],
)
async def get_document_content(
    document_id: int,
    user: UserDTO = Depends(get_current_user),
    service: DocumentApplicationService = Depends(get_document_service),
):
    dto = await service.get_document_content(document_id, owner_id=user.id)
    return success_response(dto, message=t("ok"))


@router.post(
    "/{document_id}/reparse",
    summary="重新解析",
    response_model=ApiResponse[DocumentDTO],
)
async def reparse_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    user: UserDTO = Depends(get_current_user),
    service: DocumentApplicationService = Depends(get_document_service),
):
    dto = await service.reset_for_reparse(document_id, owner_id=user.id)
    background_tasks.add_task(service.process_document, document_id)
    return success_response(dto, message=t("document.reparse.success"))


@router.delete(
    "/{document_id}",
    summary="删除文档（软删除）",
    response_model=ApiResponse[dict],
)
async def delete_document(
    document_id: int,
    user: UserDTO = Depends(get_current_user),
    service: DocumentApplicationService = Depends(get_document_service),
):
    updated = await service.soft_delete(document_id, owner_id=user.id)
    return success_response(
        {"deleted": True, "status": updated.status},
        message=t("document.delete.soft.success"),
    )
