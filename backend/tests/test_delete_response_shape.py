"""所有 DELETE 端点统一返回标准信封，``data = {"id": <id>, "deleted": true}``。"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.dependencies import (
    get_conversation_service,
    get_current_user,
    get_document_service,
    get_file_asset_service,
)
from api.routes.conversations import router as conversations_router
from api.routes.documents import router as documents_router
from api.routes.files import router as files_router
from application.dto import UserDTO


class _FakeDeleteService:
    """只实现各 DELETE 路由调用的方法；返回值刻意不是删除 payload，断言路由不透传它。"""

    def __init__(self) -> None:
        self.calls: list[tuple[str, int, int | None]] = []

    async def delete_conversation(self, conversation_id: int, *, owner_id: int):
        self.calls.append(("conversation", conversation_id, owner_id))
        return object()

    async def delete_agent_config(self, config_id: int):
        self.calls.append(("agent_config", config_id, None))

    async def soft_delete(self, resource_id: int, *, owner_id: int):
        self.calls.append(("soft_delete", resource_id, owner_id))
        return object()


@pytest.fixture
def fake_service() -> _FakeDeleteService:
    return _FakeDeleteService()


@pytest.fixture
def app(fake_service: _FakeDeleteService) -> FastAPI:
    app = FastAPI()
    app.include_router(conversations_router, prefix="/api/v1")
    app.include_router(files_router, prefix="/api/v1")
    app.include_router(documents_router, prefix="/api/v1")
    for dep in (get_conversation_service, get_file_asset_service, get_document_service):
        app.dependency_overrides[dep] = lambda: fake_service
    app.dependency_overrides[get_current_user] = lambda: UserDTO(
        id=7, username="u7", email="u7@example.com"
    )
    return app


@pytest.mark.parametrize(
    "path, resource_id",
    [
        ("/api/v1/conversations/11", 11),
        ("/api/v1/agent-configs/12", 12),
        ("/api/v1/files/13", 13),
        ("/api/v1/documents/14", 14),
    ],
)
async def test_delete_returns_uniform_payload(
    app: FastAPI, fake_service: _FakeDeleteService, path: str, resource_id: int
) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete(path)

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"] == {"id": resource_id, "deleted": True}
    assert len(fake_service.calls) == 1
    assert fake_service.calls[0][1] == resource_id
