# input: register_exception_handlers + 最小 FastAPI app
# output: 422 校验错误响应脱敏测试（details 不回显原始入参）
# pos: 后端测试 - 全局校验异常处理器行为验证；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""RequestValidationError handler must not echo raw input back in details.

pydantic v2 的 errors() 自带 input/ctx 字段，会把原始入参（如注册失败时的
密码明文）回显进响应体；前端错误追踪采集响应后即成泄露面。
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from pydantic import BaseModel, Field

from core.exceptions import register_exception_handlers


class _RegisterBody(BaseModel):
    username: str = Field(min_length=3)
    password: str = Field(min_length=8)


def _make_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.post("/register")
    async def register(body: _RegisterBody):  # pragma: no cover - 不会走到
        return {"ok": True}

    return app


@pytest.mark.asyncio
async def test_422_details_do_not_echo_raw_input() -> None:
    app = _make_app()
    secret_value = "short7!"  # 8 位以下，触发 password 校验失败

    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post(
            "/register", json={"username": "alice", "password": secret_value}
        )

    assert resp.status_code == 422
    body = resp.json()
    errors = body["error"]["details"]["errors"]
    assert errors, "应包含结构化校验错误"
    # 白名单字段：loc/msg/type；绝不回显 input/ctx
    assert set(errors[0].keys()) == {"loc", "msg", "type"}
    assert secret_value not in resp.text
