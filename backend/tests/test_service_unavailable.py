"""未配置的外部能力（LLM / OAuth provider）必须渲染 503 SERVICE_UNAVAILABLE，而不是 500。"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import api.dependencies as deps
from api.dependencies import get_current_user
from api.routes.chat import router as chat_router
from application.dto import UserDTO
from core.exceptions import register_exception_handlers
from shared.codes import BusinessCode


async def test_chat_without_llm_configured_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(deps, "get_llm_client", lambda: None)
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(chat_router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: UserDTO(
        id=1, username="u1", email="u1@example.com"
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/conversations/1/chat", json={"message": "hi", "stream": False}
        )

    assert resp.status_code == 503
    body = resp.json()
    assert body["code"] == BusinessCode.SERVICE_UNAVAILABLE
    # 不泄露配置项名
    assert "LLM__API_KEY" not in resp.text
