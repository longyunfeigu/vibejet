# input: TextIn xParse HTTP API（x-ti-app-id / x-ti-secret-code 长期凭证），httpx
# output: TextInParser（公有云解析 PDF/扫描件/Office → Markdown）
# owner: wanhua.gu
# pos: 基础设施层 - 文档解析 provider（TextIn 通用文档解析，按页计费）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Document parsing via TextIn (合合信息) general document parsing API.

Endpoint: POST {base_url}/ai/service/v1/pdf_to_markdown with the raw file
bytes as request body. Errors are surfaced as ``DocumentParserError`` with the
TextIn business code preserved — never silently degraded to another parser.
"""

from __future__ import annotations

from typing import Any, Optional

import httpx

from application.ports.document_parser import DocumentParserError, ParsedDocument
from core.logging_config import get_logger

logger = get_logger(__name__)

_PARSE_PATH = "/ai/service/v1/pdf_to_markdown"


class TextInParser:
    """DocumentParserPort implementation backed by the TextIn cloud API."""

    name = "textin"

    def __init__(
        self,
        *,
        app_id: str,
        secret_code: str,
        base_url: str = "https://api.textin.com",
        timeout: int = 120,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        if not app_id or not secret_code:
            raise RuntimeError(
                "TextIn 凭证缺失：需要 DOCUMENT__TEXTIN_APP_ID 和 DOCUMENT__TEXTIN_SECRET_CODE"
            )
        self._app_id = app_id
        self._secret_code = secret_code
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        # 测试注入点（httpx.MockTransport）；生产走默认 transport
        self._transport = transport

    async def parse(
        self,
        data: bytes,
        *,
        content_type: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> ParsedDocument:
        headers = {
            "x-ti-app-id": self._app_id,
            "x-ti-secret-code": self._secret_code,
            "Content-Type": "application/octet-stream",
        }
        # markdown_details=0：只要 markdown 正文，省掉元素明细，缩小响应体
        params = {"markdown_details": 0, "apply_document_tree": 1}

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, transport=self._transport
            ) as client:
                resp = await client.post(
                    f"{self._base_url}{_PARSE_PATH}",
                    params=params,
                    headers=headers,
                    content=data,
                )
        except httpx.TimeoutException as exc:
            raise DocumentParserError(
                code="document.parse.textin_timeout",
                message=f"TextIn 解析超时（>{self._timeout}s）",
                details={"filename": filename},
            ) from exc
        except httpx.HTTPError as exc:
            raise DocumentParserError(
                code="document.parse.textin_network_error",
                message=f"TextIn 请求失败: {exc}",
                details={"filename": filename},
            ) from exc

        if resp.status_code != 200:
            raise DocumentParserError(
                code="document.parse.textin_http_error",
                message=f"TextIn HTTP {resp.status_code}",
                details={"status_code": resp.status_code, "filename": filename},
            )

        payload: dict[str, Any] = resp.json()
        code = payload.get("code")
        if code != 200:
            # 保留 TextIn 业务码（如 40101 凭证错误），便于排障
            raise DocumentParserError(
                code="document.parse.textin_error",
                message=str(payload.get("message") or f"TextIn error code {code}"),
                details={"textin_code": code, "filename": filename},
            )

        result = payload.get("result") or {}
        markdown = result.get("markdown") or ""
        if not markdown.strip():
            raise DocumentParserError(
                code="document.parse.empty_content",
                message="TextIn 返回了空的解析结果",
                details={"filename": filename},
            )

        metadata: dict[str, Any] = {"chars": len(markdown)}
        if result.get("total_page_number") is not None:
            metadata["pages"] = result["total_page_number"]
        if payload.get("x_request_id"):
            metadata["textin_request_id"] = payload["x_request_id"]
        return ParsedDocument(markdown=markdown, metadata=metadata)
