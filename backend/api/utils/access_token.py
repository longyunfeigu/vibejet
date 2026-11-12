"""Shared-secret guard for operational endpoints (/health/ready, /metrics)."""

from __future__ import annotations

import hmac
from typing import Optional

from fastapi import HTTPException, Request


def require_access_token(request: Request, token: Optional[str]) -> None:
    """Reject with 403 unless the request carries ``token``; no-op when ``token`` is unset.

    Accepts ``Authorization: Bearer <token>`` or ``X-Access-Token: <token>`` and compares in
    constant time.
    """
    if not token:
        return
    header = request.headers.get("Authorization") or request.headers.get("X-Access-Token") or ""
    if header.lower().startswith("bearer "):
        header = header[7:]
    if not hmac.compare_digest(header.encode(), token.encode()):
        raise HTTPException(status_code=403, detail="Forbidden")
