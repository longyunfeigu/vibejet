# input: markitdown 库（optional extra "documents"），文件二进制
# output: MarkitdownParser（本地解析 Office/HTML/txt/数字原生 PDF → Markdown）
# pos: 基础设施层 - 文档解析 provider（markitdown，默认；扫描件显式拒绝）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Local document parsing via Microsoft markitdown.

Sync CPU-bound conversion is offloaded to a worker thread. PDFs whose text
layer yields (near-)empty Markdown are rejected explicitly — scanned PDFs are
NOT supported by this provider; switch ``DOCUMENT__PARSER=textin`` instead.
"""

from __future__ import annotations

import io
from os.path import splitext
from typing import Optional

import anyio

from application.ports.document_parser import DocumentParserError, ParsedDocument
from core.logging_config import get_logger

logger = get_logger(__name__)

# 低于该字符数视为"未提取到有效文本"（典型场景：扫描件 PDF 没有文本层）
_MIN_MEANINGFUL_CHARS = 20


class MarkitdownParser:
    """DocumentParserPort implementation backed by the markitdown library."""

    name = "markitdown"

    def __init__(self, *, timeout: int = 600) -> None:
        try:
            from markitdown import MarkItDown
        except ImportError as exc:  # pragma: no cover - exercised only without extra
            raise RuntimeError(
                "markitdown 未安装。请安装 documents extra：uv sync --extra documents"
            ) from exc
        # enable_plugins=False：只用内置转换器，不加载第三方插件入口
        self._md = MarkItDown(enable_plugins=False)
        # 病态文件可能让转换跑到 parsing_stale_seconds 之外，触发僵尸任务；必须有界
        self._timeout = timeout

    async def parse(
        self,
        data: bytes,
        *,
        content_type: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> ParsedDocument:
        try:
            with anyio.fail_after(self._timeout):
                markdown = await anyio.to_thread.run_sync(
                    self._convert_sync, data, content_type, filename
                )
        except TimeoutError as exc:
            # 注意：超时只取消等待，工作线程无法被杀死，会继续跑完后被丢弃
            raise DocumentParserError(
                code="document.parse.timeout",
                message=f"markitdown 解析超时（>{self._timeout}s）",
                details={"filename": filename, "content_type": content_type},
            ) from exc
        if len(markdown.strip()) < _MIN_MEANINGFUL_CHARS:
            raise DocumentParserError(
                code="document.parse.empty_content",
                message=(
                    "未能从文件中提取到有效文本（扫描件 PDF 不被 markitdown 支持，"
                    "可切换 DOCUMENT__PARSER=textin）"
                ),
                details={"filename": filename, "content_type": content_type},
            )
        return ParsedDocument(markdown=markdown, metadata={"chars": len(markdown)})

    def _convert_sync(
        self, data: bytes, content_type: Optional[str], filename: Optional[str]
    ) -> str:
        from markitdown import MarkItDownException, StreamInfo

        ext = splitext(filename or "")[1] or None
        stream_info = StreamInfo(
            extension=ext,
            mimetype=content_type,
            filename=filename,
        )
        try:
            result = self._md.convert_stream(io.BytesIO(data), stream_info=stream_info)
        except MarkItDownException as exc:
            raise DocumentParserError(
                code="document.parse.unsupported_format",
                message=str(exc),
                details={"filename": filename, "content_type": content_type},
            ) from exc
        return result.text_content or ""
