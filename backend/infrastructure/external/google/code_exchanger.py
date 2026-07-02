# input: httpx, Google token 端点(oauth2.googleapis.com/token), GOOGLE_CLIENT_ID/SECRET, GoogleIdentityVerifier
# output: GoogleAuthCodeExchanger —— 授权码换 id_token 并验签，返回可信 GoogleIdentity
# owner: wanhua.gu
# pos: 基础设施层 - Google OAuth 授权码交换实现（popup auth-code 流，client_secret 仅后端持有）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Exchange a Google authorization code for a verified identity (auth-code flow)."""

from __future__ import annotations

import httpx

from application.ports.oauth import GoogleIdentity, GoogleIdentityVerifier
from core.logging_config import get_logger
from domain.common.exceptions import InvalidTokenException

logger = get_logger(__name__)

# Google OAuth 2.0 token 端点（用授权码换 access_token / id_token）。
_GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
_EXCHANGE_TIMEOUT_SECONDS = 10.0


class GoogleAuthCodeExchanger:
    """Exchange an authorization code for tokens, then verify the returned ID token.

    popup 模式下 ``redirect_uri`` 固定为 ``"postmessage"``（@react-oauth/google 约定）。
    client_secret 仅在此后端持有，绝不下发前端。
    """

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        verifier: GoogleIdentityVerifier,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._verifier = verifier

    async def exchange(self, code: str) -> GoogleIdentity:
        payload = {
            "code": code,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "redirect_uri": self._redirect_uri,
            "grant_type": "authorization_code",
        }

        try:
            async with httpx.AsyncClient(timeout=_EXCHANGE_TIMEOUT_SECONDS) as client:
                resp = await client.post(_GOOGLE_TOKEN_ENDPOINT, data=payload)
        except httpx.HTTPError as exc:
            logger.warning("google_token_exchange_request_failed", error=str(exc))
            raise InvalidTokenException("google token exchange failed") from exc

        if resp.status_code != httpx.codes.OK:
            # Google 在错误时返回 {error, error_description}；不回显 code/secret。
            logger.warning(
                "google_token_exchange_rejected",
                status_code=resp.status_code,
                error=_safe_error(resp),
            )
            raise InvalidTokenException("google token exchange rejected")

        try:
            body = resp.json()
        except ValueError as exc:
            logger.warning("google_token_exchange_bad_body", error=str(exc))
            raise InvalidTokenException("google token response not json") from exc

        id_token = body.get("id_token") if isinstance(body, dict) else None
        if not id_token:
            logger.warning("google_token_exchange_missing_id_token")
            raise InvalidTokenException("google token response missing id_token")

        # 复用 ID Token 验签（签名/aud/iss/exp），失败时 verifier 抛 InvalidTokenException。
        return self._verifier.verify(id_token)


def _safe_error(resp: httpx.Response) -> str:
    try:
        body = resp.json()
        return str(body.get("error") or body.get("error_description") or "")
    except ValueError:
        return ""
