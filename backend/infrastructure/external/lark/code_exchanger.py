# input: httpx, 飞书/Lark 开放平台 (open.feishu.cn / open.larksuite.com), FEISHU_/LARK_ APP_ID/SECRET
# output: LarkAuthCodeExchanger —— 授权码换 access_token 再调 user_info，返回可信 OAuthIdentity；LARK_OPEN_HOSTS 映射
# owner: wanhua.gu
# pos: 基础设施层 - 飞书/Lark OAuth 授权码交换实现（v2 token + v1 user_info，app_secret 仅后端持有）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Exchange a Feishu/Lark authorization code for a trusted identity (auth-code flow)."""

from __future__ import annotations

from typing import Any

import httpx

from application.ports.oauth import OAuthIdentity
from core.logging_config import get_logger
from domain.common.exceptions import InvalidTokenException

logger = get_logger(__name__)

# 飞书 / Lark 开放平台 host（v2 OIDC token 与 v1 user_info 同 host，仅域名不同）。
LARK_OPEN_HOSTS = {
    "feishu": "https://open.feishu.cn",
    "lark": "https://open.larksuite.com",
}

# 授权码换 user_access_token（v2 OIDC，client_id+client_secret+code，无需先取 app_access_token）。
_TOKEN_PATH = "/open-apis/authen/v2/oauth/token"
# 用 user_access_token 拿用户身份。
_USER_INFO_PATH = "/open-apis/authen/v1/user_info"
_REQUEST_TIMEOUT_SECONDS = 10.0


class LarkAuthCodeExchanger:
    """Exchange an authorization code for a user access_token, then call user_info.

    飞书/Lark 不返回可本地验签的 id_token：先用 v2 OIDC token 端点换 ``access_token``，
    再调 ``user_info`` 拿身份。``sub`` 取 ``union_id``（同开发者跨应用稳定），缺失回退 ``open_id``；
    ``email`` 仅取可信的 ``enterprise_email``（管理员分配），用户自填 ``email`` 不参与链接。
    ``app_secret`` 仅在此后端持有，绝不下发前端。
    """

    def __init__(
        self,
        *,
        host: str,
        app_id: str,
        app_secret: str,
        redirect_uri: str,
    ) -> None:
        self._host = host.rstrip("/")
        self._app_id = app_id
        self._app_secret = app_secret
        self._redirect_uri = redirect_uri

    async def exchange(self, code: str) -> OAuthIdentity:
        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_SECONDS) as client:
            access_token = await self._exchange_code(client, code)
            data = await self._fetch_user_info(client, access_token)
        return _to_identity(data)

    async def _exchange_code(self, client: httpx.AsyncClient, code: str) -> str:
        payload = {
            "grant_type": "authorization_code",
            "client_id": self._app_id,
            "client_secret": self._app_secret,
            "code": code,
            "redirect_uri": self._redirect_uri,
        }
        try:
            resp = await client.post(self._host + _TOKEN_PATH, json=payload)
        except httpx.HTTPError as exc:
            logger.warning("lark_token_exchange_request_failed", error=str(exc))
            raise InvalidTokenException("lark token exchange failed") from exc

        body = _json_or_raise(resp, "lark token")
        # 错误时不回显 code/secret；飞书业务码 0 表示成功（部分场景可能不带 code，宽松放过）。
        if resp.status_code != httpx.codes.OK or body.get("code") not in (0, None):
            logger.warning(
                "lark_token_exchange_rejected",
                status_code=resp.status_code,
                error=_safe_error(body),
            )
            raise InvalidTokenException("lark token exchange rejected")

        access_token = body.get("access_token")
        if not access_token:
            logger.warning("lark_token_exchange_missing_access_token")
            raise InvalidTokenException("lark token response missing access_token")
        return str(access_token)

    async def _fetch_user_info(self, client: httpx.AsyncClient, access_token: str) -> dict:
        try:
            resp = await client.get(
                self._host + _USER_INFO_PATH,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        except httpx.HTTPError as exc:
            logger.warning("lark_user_info_request_failed", error=str(exc))
            raise InvalidTokenException("lark user_info request failed") from exc

        body = _json_or_raise(resp, "lark user_info")
        if resp.status_code != httpx.codes.OK or body.get("code") not in (0, None):
            logger.warning(
                "lark_user_info_rejected",
                status_code=resp.status_code,
                error=_safe_error(body),
            )
            raise InvalidTokenException("lark user_info rejected")

        data = body.get("data")
        if not isinstance(data, dict):
            logger.warning("lark_user_info_missing_data")
            raise InvalidTokenException("lark user_info missing data")
        return data


def _to_identity(data: dict) -> OAuthIdentity:
    # union_id 跨该开发者所有应用稳定；自建应用偶发缺失时回退 open_id。
    sub = data.get("union_id") or data.get("open_id")
    if not sub:
        logger.warning("lark_user_info_missing_sub")
        raise InvalidTokenException("lark user_info missing union_id/open_id")
    enterprise_email = data.get("enterprise_email")
    return OAuthIdentity(
        sub=str(sub),
        email=str(enterprise_email) if enterprise_email else None,
        email_verified=bool(enterprise_email),
        name=data.get("name"),
    )


def _json_or_raise(resp: httpx.Response, what: str) -> dict:
    try:
        body: Any = resp.json()
    except ValueError as exc:
        logger.warning("lark_response_not_json", what=what)
        raise InvalidTokenException(f"{what} response not json") from exc
    if not isinstance(body, dict):
        raise InvalidTokenException(f"{what} response not an object")
    return body


def _safe_error(body: dict) -> str:
    return str(body.get("error") or body.get("error_description") or body.get("msg") or "")
