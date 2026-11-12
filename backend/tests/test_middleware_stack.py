"""Regression tests for the HTTP middleware stack wiring in main.py."""

from __future__ import annotations

import pytest

from api.middleware.locale import _normalize


def test_request_id_middleware_wraps_logging() -> None:
    from main import app

    # user_middleware is outermost-first; RequestID must run before Logging so that
    # request_started log lines already carry the request_id.
    names = [m.cls.__name__ for m in app.user_middleware]
    assert names.index("RequestIDMiddleware") < names.index("LoggingMiddleware")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("zh-CN", "zh_Hans"),
        ("zh_Hans", "zh_Hans"),
        ("en-US", "en"),
        ("fr", "en"),
        ("xx-attacker-controlled", "en"),
        ("", "en"),
    ],
)
def test_locale_normalize_only_returns_supported_locales(raw: str, expected: str) -> None:
    assert _normalize(raw) == expected
