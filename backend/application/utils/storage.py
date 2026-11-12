"""Application-level storage helpers to avoid infra coupling."""

from __future__ import annotations

import mimetypes
import uuid
from datetime import datetime, timezone
from typing import Optional


def build_storage_key(
    kind: str, user_id: Optional[str] = None, ext: Optional[str] = None, prefix_date: bool = True
) -> str:
    parts: list[str] = []
    if prefix_date:
        now = datetime.now(timezone.utc)
        parts.extend([str(now.year), f"{now.month:02d}", f"{now.day:02d}"])
    parts.append(kind)
    if user_id:
        parts.append(str(user_id))
    filename = str(uuid.uuid4())
    if ext:
        if not ext.startswith("."):
            ext = f".{ext}"
        filename += ext
    parts.append(filename)
    return "/".join(parts)


def guess_content_type(filename: str) -> str:
    ctype, _ = mimetypes.guess_type(filename)
    return ctype or "application/octet-stream"
