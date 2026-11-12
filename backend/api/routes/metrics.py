"""Prometheus metrics endpoint."""

from __future__ import annotations

import contextlib

from fastapi import APIRouter, HTTPException, Request
from starlette.responses import Response

from api.utils.access_token import require_access_token
from core.config import settings
from core.observability import metrics
from infrastructure.database import engine

router = APIRouter(tags=["Metrics"])


@router.get("/metrics", include_in_schema=False)
async def metrics_endpoint(request: Request):
    if not settings.metrics.enabled or not metrics.HAS_PROMETHEUS:
        raise HTTPException(status_code=404, detail="Metrics disabled")
    require_access_token(request, settings.metrics.access_token)

    with contextlib.suppress(Exception):
        metrics.collect_db_pool_metrics(engine)

    if settings.redis.url:
        with contextlib.suppress(Exception):
            from infrastructure.external.cache import get_redis_client

            client = await get_redis_client()
            metrics.collect_redis_pool_metrics(client)

    data, content_type = metrics.get_metrics_response()
    return Response(content=data, media_type=content_type)
