# input: backend 源码里的 message_key / t() 字面量, locales/*/LC_MESSAGES/messages.po, register_exception_handlers
# output: 翻译覆盖测试（代码用到的 key 必须在每份翻译表里）+ 业务异常 message 兜底测试（缺翻译时返回默认文案而非 key）
# pos: 后端测试 - i18n 翻译表漂移与异常提示文案守护；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Every message key used in backend code must exist in every translation catalog,
and a missing translation must never leak the raw key as the user-facing message."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from core.exceptions import register_exception_handlers
from domain.common.exceptions import BusinessException
from shared.codes import BusinessCode

BACKEND = Path(__file__).resolve().parent.parent
CATALOGS = sorted((BACKEND / "locales").glob("*/LC_MESSAGES/messages.po"))
SKIP_DIRS = {".venv", "tests", "alembic", "__pycache__"}
KEY_RE = re.compile(r'(?:message_key\s*=\s*|\bt\()"([a-z][\w.]*)"')
MSGID_RE = re.compile(r'^msgid "([^"]+)"', re.M)


def _keys_used_in_code() -> dict[str, str]:
    keys: dict[str, str] = {}
    for path in BACKEND.rglob("*.py"):
        if SKIP_DIRS.intersection(path.relative_to(BACKEND).parts):
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for key in KEY_RE.findall(line):
                keys.setdefault(key, f"{path.relative_to(BACKEND)}:{lineno}")
    return keys


def test_catalogs_cover_both_locales() -> None:
    assert {p.parts[-3] for p in CATALOGS} >= {"en", "zh_Hans"}
    assert _keys_used_in_code(), "the scan must find the keys used in code"


@pytest.mark.parametrize("catalog", CATALOGS, ids=lambda p: p.parts[-3])
def test_every_message_key_in_code_has_a_translation(catalog: Path) -> None:
    translated = set(MSGID_RE.findall(catalog.read_text(encoding="utf-8")))
    missing = {k: where for k, where in _keys_used_in_code().items() if k not in translated}
    assert not missing, f"{catalog.parts[-3]} catalog is missing: {missing}"


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


@pytest.mark.asyncio
async def test_missing_translation_falls_back_to_default_message_not_the_key() -> None:
    async with AsyncClient(app=_make_app(), base_url="http://test") as client:
        resp = await client.get("/boom")

    body = resp.json()
    assert body["message"] == "Thing not found"
    assert body["error"]["message_key"] == "test.untranslated.key"
