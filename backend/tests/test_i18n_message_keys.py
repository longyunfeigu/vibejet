"""The catalog check must pass, and a missing translation must never leak the raw
key as the user-facing message."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from core.exceptions import register_exception_handlers
from domain.common.exceptions import BusinessException
from shared.codes import BusinessCode

VALIDATE_PO = Path(__file__).resolve().parent.parent / "scripts" / "validate_po.py"


def _load_validate_po() -> ModuleType:
    spec = importlib.util.spec_from_file_location("validate_po", VALIDATE_PO)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_catalogs_pass_validate_po(capsys: pytest.CaptureFixture[str]) -> None:
    # 翻译表校验只有 scripts/validate_po.py 一份实现（pre-commit 也调它）；这里让 CI 的 pytest 也跑到它
    assert _load_validate_po().main() == 0, capsys.readouterr().err


class _UntranslatedError(BusinessException):
    def __init__(self) -> None:
        super().__init__(
            code=BusinessCode.NOT_FOUND,
            message="Thing not found",
            message_key="test.untranslated.key",
        )


def _make_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    async def boom() -> None:
        raise _UntranslatedError()

    return app


async def test_missing_translation_falls_back_to_default_message_not_the_key() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=_make_app()), base_url="http://test"
    ) as client:
        resp = await client.get("/boom")

    body = resp.json()
    assert body["message"] == "Thing not found"
    assert body["error"]["message_key"] == "test.untranslated.key"
