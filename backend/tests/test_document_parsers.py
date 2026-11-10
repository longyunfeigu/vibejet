# input: parsing providers（markitdown 真实库 / textin httpx mock）
# output: 文档解析 provider 行为测试
# pos: 后端测试 - 解析 provider 成功/失败/错误映射验证；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Tests for document parsing providers."""

from __future__ import annotations

import httpx
import pytest

from application.ports.document_parser import DocumentParserError

# ── markitdown provider ─────────────────────────────────────────────

markitdown = pytest.importorskip("markitdown", reason="documents extra not installed")

from infrastructure.external.parsing.providers.markitdown import MarkitdownParser  # noqa: E402
from infrastructure.external.parsing.providers.textin import TextInParser  # noqa: E402


async def test_markitdown_parses_html_to_markdown() -> None:
    parser = MarkitdownParser()
    html = b"<html><body><h1>Title</h1><p>Some meaningful paragraph content.</p></body></html>"
    result = await parser.parse(html, content_type="text/html", filename="page.html")
    assert "# Title" in result.markdown
    assert result.metadata["chars"] > 0


async def test_markitdown_rejects_empty_extraction() -> None:
    parser = MarkitdownParser()
    with pytest.raises(DocumentParserError) as exc_info:
        await parser.parse(b"", content_type="text/plain", filename="empty.txt")
    assert exc_info.value.code == "document.parse.empty_content"


# ── textin provider (httpx MockTransport, no real network) ─────────


def _textin_parser_with(handler) -> tuple[TextInParser, list[httpx.Request]]:
    """Build a TextInParser backed by httpx.MockTransport (no real network)."""
    requests: list[httpx.Request] = []

    def _record(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return handler(request)

    parser = TextInParser(
        app_id="app",
        secret_code="secret",
        transport=httpx.MockTransport(_record),
    )
    return parser, requests


async def test_textin_success_returns_markdown_and_sends_credentials() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": 200,
                "message": "success",
                "result": {"markdown": "# Parsed", "total_page_number": 2},
            },
        )

    parser, requests = _textin_parser_with(handler)
    result = await parser.parse(b"%PDF-fake", content_type="application/pdf", filename="a.pdf")

    assert result.markdown == "# Parsed"
    assert result.metadata["pages"] == 2
    req = requests[0]
    assert req.headers["x-ti-app-id"] == "app"
    assert req.headers["x-ti-secret-code"] == "secret"
    assert req.url.params["markdown_details"] == "0"


async def test_textin_business_error_is_mapped_with_code() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 40101, "message": "x-ti-app-id header error"})

    parser, _ = _textin_parser_with(handler)
    with pytest.raises(DocumentParserError) as exc_info:
        await parser.parse(b"%PDF-fake", filename="a.pdf")
    assert exc_info.value.code == "document.parse.textin_error"
    assert exc_info.value.details["textin_code"] == 40101


async def test_textin_http_error_is_mapped() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="service unavailable")

    parser, _ = _textin_parser_with(handler)
    with pytest.raises(DocumentParserError) as exc_info:
        await parser.parse(b"%PDF-fake", filename="a.pdf")
    assert exc_info.value.code == "document.parse.textin_http_error"


async def test_textin_empty_markdown_rejected() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 200, "result": {"markdown": "  "}})

    parser, _ = _textin_parser_with(handler)
    with pytest.raises(DocumentParserError) as exc_info:
        await parser.parse(b"%PDF-fake", filename="a.pdf")
    assert exc_info.value.code == "document.parse.empty_content"


def test_textin_requires_credentials() -> None:
    with pytest.raises(RuntimeError):
        TextInParser(app_id="", secret_code="")


async def test_textin_non_json_response_is_mapped() -> None:
    """出口代理劫持为 200 + HTML 时，必须映射为带归因的 ParserError 而非裸异常。"""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>Gateway error</html>")

    parser, _ = _textin_parser_with(handler)
    with pytest.raises(DocumentParserError) as exc_info:
        await parser.parse(b"%PDF-fake", filename="a.pdf")
    assert exc_info.value.code == "document.parse.textin_invalid_response"
    assert "Gateway" in exc_info.value.details["body_prefix"]


async def test_textin_non_dict_json_is_mapped() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=["not", "a", "dict"])

    parser, _ = _textin_parser_with(handler)
    with pytest.raises(DocumentParserError) as exc_info:
        await parser.parse(b"%PDF-fake", filename="a.pdf")
    assert exc_info.value.code == "document.parse.textin_invalid_response"


async def test_markitdown_parse_timeout_is_mapped(monkeypatch: pytest.MonkeyPatch) -> None:
    """转换线程超时必须映射为 document.parse.timeout（线程本身不可取消，仅丢弃等待）。"""
    import time

    parser = MarkitdownParser(timeout=1)

    def slow_convert(data: bytes, ct: str | None, fn: str | None) -> str:
        time.sleep(5)
        return ""

    monkeypatch.setattr(parser, "_convert_sync", slow_convert)

    with pytest.raises(DocumentParserError) as exc_info:
        await parser.parse(b"slow", content_type="text/plain", filename="slow.txt")
    assert exc_info.value.code == "document.parse.timeout"


async def test_markitdown_abandoned_conversions_are_capped(monkeypatch: pytest.MonkeyPatch) -> None:
    """超时被放弃的转换线程继续占名额：名额满了直接报 busy，线程跑完名额才回来。"""
    import threading

    import anyio

    from infrastructure.external.parsing.providers import markitdown as markitdown_module

    slots = threading.BoundedSemaphore(1)
    monkeypatch.setattr(markitdown_module, "_conversion_slots", slots)
    release = threading.Event()

    def slow_convert(data: bytes, ct: str | None, fn: str | None) -> str:
        release.wait(5)
        return "converted text long enough to count as content"

    parser = MarkitdownParser(timeout=1)
    monkeypatch.setattr(parser, "_convert_sync", slow_convert)

    with pytest.raises(DocumentParserError) as first:
        await parser.parse(b"slow", content_type="text/plain", filename="a.txt")
    assert first.value.code == "document.parse.timeout"

    with pytest.raises(DocumentParserError) as second:
        await parser.parse(b"slow", content_type="text/plain", filename="b.txt")
    assert second.value.code == "document.parse.busy"

    release.set()
    with anyio.fail_after(5):
        while not slots.acquire(blocking=False):
            await anyio.sleep(0.01)
    slots.release()

    parsed = await parser.parse(b"ok", content_type="text/plain", filename="c.txt")
    assert "converted text" in parsed.markdown
