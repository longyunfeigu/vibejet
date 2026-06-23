# input: google-auth 库, GOOGLE_CLIENT_ID, Google 签发的 ID Token
# output: GoogleIdTokenVerifier —— 验 Google ID Token 并返回可信身份
# owner: wanhua.gu
# pos: 基础设施层 - Google ID Token 验签实现（验签名/aud/iss/exp）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Verify Google ID tokens via the official google-auth library."""

from __future__ import annotations

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from application.ports.oauth import GoogleIdentity
from core.logging_config import get_logger
from domain.common.exceptions import InvalidTokenException

logger = get_logger(__name__)


class GoogleIdTokenVerifier:
    """Validate a Google ID token's signature, audience, issuer and expiry."""

    def __init__(self, client_id: str) -> None:
        self._client_id = client_id
        self._request = google_requests.Request()

    def verify(self, credential: str) -> GoogleIdentity:
        try:
            # verify_oauth2_token 校验签名、exp，并断言 aud == client_id、iss 为 Google
            claims = google_id_token.verify_oauth2_token(credential, self._request, self._client_id)
        except ValueError as exc:
            logger.warning("google_id_token_invalid", error=str(exc))
            raise InvalidTokenException("invalid google credential") from exc

        sub = claims.get("sub")
        email = claims.get("email")
        if not sub or not email:
            raise InvalidTokenException("google credential missing sub/email")

        return GoogleIdentity(
            sub=str(sub),
            email=str(email),
            email_verified=bool(claims.get("email_verified", False)),
            name=claims.get("name"),
        )
