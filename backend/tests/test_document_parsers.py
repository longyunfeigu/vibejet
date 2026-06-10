# input: parsing providers（markitdown 真实库 / textin httpx mock）
# output: 文档解析 provider 行为测试
# owner: wanhua.gu
# pos: 后端测试 - 解析 provider 成功/失败/错误映射验证；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Tests for document parsing providers."""

from __future__ import annotations

import httpx
import pytest

from application.ports.document_parser import DocumentParserError

# ── markitdown provider ─────────────────────────────────────────────

markitdown = pytest.importorskip("markitdown", reason="documents extra not installed")

from infrastructure.external.parsing.providers.markitdown import (  # noqa: E402
    MarkitdownParser,
)
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


async def test_markitdown_parse_timeout_is_mapped() -> None:
    """转换线程超时必须映射为 document.parse.timeout（线程本身不可取消，仅丢弃等待）。"""
    import time

    parser = MarkitdownParser(timeout=1)
    parser._convert_sync = lambda data, ct, fn: time.sleep(5) or ""  # type: ignore[method-assign]

    with pytest.raises(DocumentParserError) as exc_info:
        await parser.parse(b"slow", content_type="text/plain", filename="slow.txt")
    assert exc_info.value.code == "document.parse.timeout"
