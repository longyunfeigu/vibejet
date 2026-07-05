# input: core.config.settings.document（DOCUMENT__PARSER 二选一）
# output: create_parser/get_parser 工厂（DocumentParserPort 进程级单例）+ init_parser/shutdown_parser 生命周期
# pos: 基础设施层 - 文档解析 provider 工厂（按配置实例化 markitdown 或 textin，懒加载）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Document parsing provider factory.

Mirrors the storage provider pattern: providers are lazily imported so that
optional dependencies (markitdown) are only required when actually selected.
The two providers are mutually exclusive — chosen once via ``DOCUMENT__PARSER``.
"""

from __future__ import annotations

from typing import Optional

from application.ports.document_parser import DocumentParserPort
from core.config import settings

_parser: Optional[DocumentParserPort] = None


def create_parser() -> DocumentParserPort:
    """Instantiate the configured parser provider (no caching)."""
    doc = settings.document
    if doc.parser == "textin":
        from .providers.textin import TextInParser

        return TextInParser(
            app_id=doc.textin_app_id or "",
            secret_code=doc.textin_secret_code or "",
            base_url=doc.textin_base_url,
            timeout=doc.textin_timeout,
        )
    # settings 校验保证 parser ∈ {markitdown, textin}
    from .providers.markitdown import MarkitdownParser

    return MarkitdownParser(timeout=doc.markitdown_timeout)


def get_parser() -> DocumentParserPort:
    """Process-level lazy singleton (parsers are stateless and reusable)."""
    global _parser
    if _parser is None:
        _parser = create_parser()
    return _parser


async def init_parser() -> None:
    """Lifespan 探测：构造一次解析器，把缺依赖/缺凭证暴露在启动期而不是首个请求。"""
    get_parser()


async def shutdown_parser() -> None:
    """关闭解析器持有的资源（如 TextIn 共享 HTTP 客户端），与 init 对称。"""
    global _parser
    if _parser is None:
        return
    aclose = getattr(_parser, "aclose", None)
    if callable(aclose):
        await aclose()
    _parser = None


__all__ = ["create_parser", "get_parser", "init_parser", "shutdown_parser"]
