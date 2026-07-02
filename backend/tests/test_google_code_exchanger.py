# input: GoogleAuthCodeExchanger + monkeypatch 的 httpx.AsyncClient + fake verifier
# output: 授权码换 token 适配器行为测试（成功/Google拒绝/缺id_token/网络错误）
# pos: 后端测试 - Google 授权码交换适配器验证；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Behavior tests for GoogleAuthCodeExchanger (token exchange + id_token verify)."""

from __future__ import annotations

import httpx
import pytest

from application.ports.oauth import GoogleIdentity
from domain.common.exceptions import InvalidTokenException
from infrastructure.external.google import code_exchanger as ce


class FakeVerifier:
    def __init__(self, identity: GoogleIdentity) -> None:
        self._identity = identity
        self.seen: list[str] = []

    def verify(self, credential: str) -> GoogleIdentity:
        self.seen.append(credential)
        return self._identity


def _patch_client(
    monkeypatch, *, response: httpx.Response | None = None, error: Exception | None = None
):
    """Monkeypatch httpx.AsyncClient so the adapter's POST returns/raises a canned result."""

    class _FakeClient:
        def __init__(self, *a, **k) -> None:
            self.posted: dict | None = None

        async def __aenter__(self) -> "_FakeClient":
            return self

        async def __aexit__(self, *exc) -> bool:
            return False

        async def post(self, url: str, data=None) -> httpx.Response:
            if error is not None:
                raise error
            assert response is not None
            return response

    monkeypatch.setattr(ce.httpx, "AsyncClient", _FakeClient)


def _exchanger(verifier: FakeVerifier) -> ce.GoogleAuthCodeExchanger:
    return ce.GoogleAuthCodeExchanger(
        client_id="cid",
        client_secret="secret",
        redirect_uri="postmessage",
        verifier=verifier,
    )


async def test_exchange_success_returns_verified_identity(monkeypatch) -> None:
    identity = GoogleIdentity(sub="s1", email="a@x.com", email_verified=True, name="A")
    verifier = FakeVerifier(identity)
    _patch_client(monkeypatch, response=httpx.Response(200, json={"id_token": "the-id-token"}))

    result = await _exchanger(verifier).exchange("auth-code")

    assert result is identity
    assert verifier.seen == ["the-id-token"]  # 用换回的 id_token 验签


async def test_exchange_rejected_status_raises(monkeypatch) -> None:
    verifier = FakeVerifier(GoogleIdentity(sub="s", email="a@x.com", email_verified=True))
    _patch_client(monkeypatch, response=httpx.Response(400, json={"error": "invalid_grant"}))

    with pytest.raises(InvalidTokenException):
        await _exchanger(verifier).exchange("bad-code")
    assert verifier.seen == []  # 未到验签步骤


async def test_exchange_missing_id_token_raises(monkeypatch) -> None:
    verifier = FakeVerifier(GoogleIdentity(sub="s", email="a@x.com", email_verified=True))
    _patch_client(monkeypatch, response=httpx.Response(200, json={"access_token": "only-access"}))

    with pytest.raises(InvalidTokenException):
        await _exchanger(verifier).exchange("code")
    assert verifier.seen == []


async def test_exchange_network_error_raises(monkeypatch) -> None:
    verifier = FakeVerifier(GoogleIdentity(sub="s", email="a@x.com", email_verified=True))
    _patch_client(monkeypatch, error=httpx.ConnectError("boom"))

    with pytest.raises(InvalidTokenException):
        await _exchanger(verifier).exchange("code")


async def test_exchange_non_json_200_raises(monkeypatch) -> None:
    verifier = FakeVerifier(GoogleIdentity(sub="s", email="a@x.com", email_verified=True))
    _patch_client(monkeypatch, response=httpx.Response(200, text="<html>oops</html>"))

    with pytest.raises(InvalidTokenException):
        await _exchanger(verifier).exchange("code")
    assert verifier.seen == []
