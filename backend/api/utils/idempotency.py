# input: FastAPI Header/Request, application IdempotencyService, core.logging_config
# output: validate_idempotency_key, build_request_hash, pick_subject_from_request_headers, IdempotencyContext, idempotency_for
# owner: wanhua.gu
# pos: 表示层工具 - Idempotency-Key 解析、请求哈希、依赖注入上下文；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Idempotency helpers for API boundaries.

Routes consume `IdempotencyContext` via the `idempotency_for(scope)` dependency
factory. The context encapsulates key validation, scope/subject resolution,
request-hash building, cache lookup, and result persistence — so route handlers
contain only orchestration, not idempotency mechanics.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

from fastapi import Depends, Header, HTTPException, Request

from application.services.idempotency_service import IdempotencyService
from core.logging_config import get_logger
from domain.common.exceptions import BusinessException

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def validate_idempotency_key(key: str) -> str:
    """Validate Idempotency-Key header value.

    Keeps the rules intentionally simple for a kit:
    - 8..128 chars
    - visible ASCII only
    """
    k = (key or "").strip()
    if not k:
        raise ValueError("Idempotency-Key is empty")
    if len(k) < 8 or len(k) > 128:
        raise ValueError("Idempotency-Key length must be between 8 and 128")
    for ch in k:
        o = ord(ch)
        if o < 33 or o > 126:
            raise ValueError("Idempotency-Key must be visible ASCII characters")
    return k


def canonical_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def build_request_hash(*, scope: str, subject: str, body: Any) -> str:
    raw = canonical_json({"scope": scope, "subject": subject, "body": body})
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def pick_subject_from_request_headers(headers: dict[str, str]) -> str:
    """Pick a best-effort idempotency subject.

    Prefer authenticated identity when available; fall back to a stable anon bucket.
    """
    auth = (headers.get("authorization") or "").strip()
    if auth:
        return hashlib.sha256(auth.encode("utf-8")).hexdigest()
    return "anon"


# ---------------------------------------------------------------------------
# Per-request idempotency context (dependency-injected)
# ---------------------------------------------------------------------------


class IdempotencyContext:
    """Per-request idempotency state.

    All methods are safe to call unconditionally: when no Idempotency-Key was
    provided, ``request_hash``/``lookup``/``persist`` become no-ops, so route
    handlers don't need to branch on whether the request is idempotent.

    Failure policy mirrors the original inline code:
    - ``decide()`` raising a ``BusinessException`` propagates (e.g. duplicate-with-
      different-body → DomainValidationException → 4xx).
    - Any other ``decide()`` / ``persist_result()`` failure is logged at WARNING
      and the context disables itself for the rest of the request.
    """

    def __init__(
        self,
        *,
        service: IdempotencyService,
        scope: str,
        subject: str,
        idem_key: Optional[str],
    ) -> None:
        self._service = service
        self._scope = scope
        self._subject = subject
        self._idem_key = idem_key

    @property
    def active(self) -> bool:
        return self._idem_key is not None

    def request_hash(self, body: Any) -> Optional[str]:
        """Return the canonical request hash, or ``None`` when inactive."""
        if not self._idem_key:
            return None
        return build_request_hash(scope=self._scope, subject=self._subject, body=body)

    async def lookup(self, request_hash: Optional[str]) -> Optional[dict[str, Any]]:
        """Return cached payload on hit, ``None`` when the caller should execute."""
        if not request_hash or not self._idem_key:
            return None
        try:
            decision = await self._service.decide(
                scope=self._scope,
                key=self._idem_key,
                request_hash=request_hash,
            )
        except BusinessException:
            raise
        except Exception as exc:
            logger.warning(
                "idempotency_decide_failed",
                scope=self._scope,
                key=self._idem_key,
                error=str(exc),
            )
            self._idem_key = None
            return None
        if decision.execute:
            return None
        return decision.payload

    async def persist(self, request_hash: Optional[str], payload: dict[str, Any]) -> None:
        """Persist the result; no-op when inactive."""
        if not request_hash or not self._idem_key:
            return
        try:
            await self._service.persist_result(
                scope=self._scope,
                key=self._idem_key,
                request_hash=request_hash,
                payload=payload,
            )
        except Exception as exc:
            logger.warning(
                "idempotency_persist_failed",
                scope=self._scope,
                key=self._idem_key,
                error=str(exc),
            )


def idempotency_for(scope_label: str | None = None):
    """FastAPI dependency factory.

    Usage:
        @router.post("/foo")
        async def foo(
            payload: FooDTO,
            idem: IdempotencyContext = Depends(idempotency_for("foo:create")),
        ):
            ...

    When ``scope_label`` is omitted, the scope defaults to ``f"{method}:{path}"``.
    Validates ``Idempotency-Key`` (if present) and maps ``ValueError`` to 422.
    """
    # Local import to avoid circular import at module load.
    from api.dependencies import get_idempotency_service

    async def _dep(
        request: Request,
        idem_service: IdempotencyService = Depends(get_idempotency_service),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ) -> IdempotencyContext:
        scope = scope_label or f"{request.method}:{request.url.path}"
        subject = pick_subject_from_request_headers(dict(request.headers))

        idem_key: Optional[str] = None
        if idempotency_key:
            try:
                idem_key = validate_idempotency_key(idempotency_key)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc

        return IdempotencyContext(
            service=idem_service,
            scope=scope,
            subject=subject,
            idem_key=idem_key,
        )

    return _dep
