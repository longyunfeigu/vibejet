# input: LarkAuthCodeExchanger + monkeypatch 的 httpx.AsyncClient（post=token, get=user_info）
# output: 飞书/Lark 授权码交换适配器行为测试（成功/无企业邮箱/token拒绝/缺token/user_info拒绝/缺data/缺sub/网络错误/非JSON）
# pos: 后端测试 - 飞书/Lark 授权码交换适配器验证；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Behavior tests for LarkAuthCodeExchanger (v2 token exchange + v1 user_info)."""

from __future__ import annotations

import httpx
import pytest

from domain.common.exceptions import InvalidTokenException
from infrastructure.external.lark import code_exchanger as ce


def _patch_client(
    monkeypatch,
    *,
    token_response: httpx.Response | None = None,
    token_error: Exception | None = None,
    userinfo_response: httpx.Response | None = None,
    userinfo_error: Exception | None = None,
):
    """Monkeypatch httpx.AsyncClient so post() => token endpoint, get() => user_info."""

    class _FakeClient:
        def __init__(self, *a, **k) -> None:
            pass

        async def __aenter__(self) -> "_FakeClient":
            return self

        async def __aexit__(self, *exc) -> bool:
            return False

        async def post(self, url: str, json=None) -> httpx.Response:
            if token_error is not None:
                raise token_error
            assert token_response is not None
            return token_response

        async def get(self, url: str, headers=None) -> httpx.Response:
            if userinfo_error is not None:
                raise userinfo_error
            assert userinfo_response is not None
            return userinfo_response

    monkeypatch.setattr(ce.httpx, "AsyncClient", _FakeClient)


def _exchanger() -> ce.LarkAuthCodeExchanger:
    return ce.LarkAuthCodeExchanger(
        host="https://open.feishu.cn",
        app_id="cli_app",
        app_secret="secret",
        redirect_uri="https://app.example.com/auth/callback",
    )


def _user_info(data: dict) -> httpx.Response:
    return httpx.Response(200, json={"code": 0, "msg": "success", "data": data})


async def test_exchange_success_with_enterprise_email(monkeypatch) -> None:
    _patch_client(
        monkeypatch,
        token_response=httpx.Response(200, json={"code": 0, "access_token": "u-token"}),
        userinfo_response=_user_info(
            {
                "union_id": "on_union_1",
                "open_id": "ou_open_1",
                "name": "张三",
                "enterprise_email": "zhangsan@corp.com",
                "email": "self@personal.com",
            }
        ),
    )

    identity = await _exchanger().exchange("auth-code")

    assert identity.sub == "on_union_1"  # 优先 union_id
    assert identity.email == "zhangsan@corp.com"  # 仅取可信的 enterprise_email
    assert identity.email_verified is True
    assert identity.name == "张三"


async def test_exchange_no_enterprise_email_yields_unverified_none(monkeypatch) -> None:
    _patch_client(
        monkeypatch,
        token_response=httpx.Response(200, json={"code": 0, "access_token": "u-token"}),
        userinfo_response=_user_info(
            {"union_id": "on_2", "name": "李四", "email": "self@personal.com"}
        ),
    )

    identity = await _exchanger().exchange("code")

    assert identity.sub == "on_2"
    assert identity.email is None  # 自填 email 不参与，不可信
    assert identity.email_verified is False


async def test_exchange_falls_back_to_open_id_when_union_missing(monkeypatch) -> None:
    _patch_client(
        monkeypatch,
        token_response=httpx.Response(200, json={"code": 0, "access_token": "u-token"}),
        userinfo_response=_user_info({"open_id": "ou_only", "name": "N"}),
    )

    identity = await _exchanger().exchange("code")

    assert identity.sub == "ou_only"


async def test_token_rejected_status_raises_and_skips_user_info(monkeypatch) -> None:
    _patch_client(
        monkeypatch,
        token_response=httpx.Response(400, json={"code": 20050, "error": "server_error"}),
        # user_info 不应被调用；若被调用会因 None 断言失败
    )

    with pytest.raises(InvalidTokenException):
        await _exchanger().exchange("bad-code")


async def test_token_business_code_nonzero_raises(monkeypatch) -> None:
    _patch_client(
        monkeypatch,
        token_response=httpx.Response(200, json={"code": 20001, "error": "invalid_grant"}),
    )

    with pytest.raises(InvalidTokenException):
        await _exchanger().exchange("bad-code")


async def test_token_missing_access_token_raises(monkeypatch) -> None:
    _patch_client(
        monkeypatch,
        token_response=httpx.Response(200, json={"code": 0}),
    )

    with pytest.raises(InvalidTokenException):
        await _exchanger().exchange("code")


async def test_user_info_rejected_raises(monkeypatch) -> None:
    _patch_client(
        monkeypatch,
        token_response=httpx.Response(200, json={"code": 0, "access_token": "t"}),
        userinfo_response=httpx.Response(200, json={"code": 99991663, "msg": "token invalid"}),
    )

    with pytest.raises(InvalidTokenException):
        await _exchanger().exchange("code")


async def test_user_info_missing_data_raises(monkeypatch) -> None:
    _patch_client(
        monkeypatch,
        token_response=httpx.Response(200, json={"code": 0, "access_token": "t"}),
        userinfo_response=httpx.Response(200, json={"code": 0, "msg": "ok"}),
    )

    with pytest.raises(InvalidTokenException):
        await _exchanger().exchange("code")


async def test_user_info_missing_sub_raises(monkeypatch) -> None:
    _patch_client(
        monkeypatch,
        token_response=httpx.Response(200, json={"code": 0, "access_token": "t"}),
        userinfo_response=_user_info({"name": "no ids"}),
    )

    with pytest.raises(InvalidTokenException):
        await _exchanger().exchange("code")


async def test_token_network_error_raises(monkeypatch) -> None:
    _patch_client(monkeypatch, token_error=httpx.ConnectError("boom"))

    with pytest.raises(InvalidTokenException):
        await _exchanger().exchange("code")


async def test_token_non_json_raises(monkeypatch) -> None:
    _patch_client(
        monkeypatch,
        token_response=httpx.Response(200, text="<html>oops</html>"),
    )

    with pytest.raises(InvalidTokenException):
        await _exchanger().exchange("code")
