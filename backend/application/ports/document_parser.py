"""Application-owned document parser port (hexagonal architecture).

All parser providers normalize input files to canonical Markdown so that
downstream consumers (chunking, indexing, prompting) only ever see one format.
Providers are mutually exclusive — selected once via ``DOCUMENT__PARSER``,
no silent fallback between them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable


@dataclass
class ParsedDocument:
    """Canonical parse result."""

    markdown: str
    metadata: dict[str, Any] = field(default_factory=dict)


class DocumentParserError(Exception):
    """Raised by parser providers on parse failure.

    ``code`` is a stable, dot-separated identifier persisted to
    ``Document.error_code`` (e.g. ``document.parse.empty_content``,
    ``document.parse.textin_error``).
    """

    def __init__(self, code: str, message: str, *, details: Optional[dict[str, Any]] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


@runtime_checkable
class DocumentParserPort(Protocol):
    """Port for converting a file's bytes into canonical Markdown."""

    # Provider identifier persisted to Document.parser (markitdown / textin)
    name: str

    async def parse(
        self,
        data: bytes,
        *,
        content_type: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> ParsedDocument: ...
