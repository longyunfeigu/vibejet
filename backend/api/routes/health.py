"""Health check endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette import status as http_status

from api.utils.access_token import require_access_token
from core.config import settings
from core.observability.health import full_health_check

router = APIRouter(tags=["Health"])


@router.get("/health/live")
async def health_live():
    return {"status": "alive"}


@router.get("/health/ready")
async def health_ready(request: Request):
    require_access_token(request, settings.health.access_token)
    report = await full_health_check()
    payload = (
        report.to_dict() if settings.health.include_details else {"status": report.status.value}
    )
    status_code = (
        http_status.HTTP_200_OK if report.is_ready else http_status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return JSONResponse(status_code=status_code, content=payload)


@router.get("/health")
async def health_legacy():
    return {"status": "alive"}
