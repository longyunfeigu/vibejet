"""Tests for the shared-secret guard on /health/ready and /metrics."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from api.utils.access_token import require_access_token


def _request(headers: dict[str, str]) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    return Request({"type": "http", "headers": raw})


@pytest.mark.parametrize(
    "headers",
    [
        {"Authorization": "Bearer s3cret"},
        {"Authorization": "bearer s3cret"},
        {"X-Access-Token": "s3cret"},
    ],
)
def test_matching_token_passes(headers: dict[str, str]) -> None:
    require_access_token(_request(headers), "s3cret")


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer wrong"},
        {"X-Access-Token": "s3cre"},
        {"Authorization": "s3cret!"},
    ],
)
def test_missing_or_wrong_token_is_forbidden(headers: dict[str, str]) -> None:
    with pytest.raises(HTTPException) as caught:
        require_access_token(_request(headers), "s3cret")
    assert caught.value.status_code == 403


def test_no_configured_token_allows_anonymous() -> None:
    require_access_token(_request({}), None)
