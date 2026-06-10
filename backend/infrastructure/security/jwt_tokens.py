# input: pyjwt, SECRET_KEY + AuthSettings（algorithm/TTL）
# output: JwtTokenProvider 令牌签发与校验实现
# owner: wanhua.gu
# pos: 基础设施层 - TokenProvider 端口的 JWT(HS256) 实现，type claim 区分 access/refresh；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""JWT implementation of the TokenProvider port (pyjwt, HS256)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt

from application.ports.security import TokenPair, TokenType
from domain.common.exceptions import InvalidTokenException


class JwtTokenProvider:
    """Issues and verifies HS256-signed access/refresh token pairs.

    Claims: ``sub`` (user id), ``type`` (access|refresh), ``iat``, ``exp``.
    A refresh token can never pass verification where an access token is
    expected (and vice versa) — the ``type`` claim is always checked.
    """

    def __init__(
        self,
        *,
        secret_key: str,
        algorithm: str = "HS256",
        access_ttl_seconds: int = 30 * 60,
        refresh_ttl_seconds: int = 7 * 24 * 60 * 60,
    ) -> None:
        if not secret_key:
            raise ValueError("JwtTokenProvider requires a non-empty secret key")
        self._secret = secret_key
        self._algorithm = algorithm
        self._access_ttl = access_ttl_seconds
        self._refresh_ttl = refresh_ttl_seconds

    def issue_pair(self, *, subject: str) -> TokenPair:
        return TokenPair(
            access_token=self._encode(subject, "access", self._access_ttl),
            refresh_token=self._encode(subject, "refresh", self._refresh_ttl),
            token_type="bearer",
            expires_in=self._access_ttl,
        )

    def verify(self, token: str, *, expected_type: TokenType) -> str:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except jwt.ExpiredSignatureError:
            raise InvalidTokenException("expired")
        except jwt.InvalidTokenError:
            raise InvalidTokenException("invalid")
        if payload.get("type") != expected_type:
            raise InvalidTokenException("wrong token type")
        subject = payload.get("sub")
        if not subject:
            raise InvalidTokenException("missing subject")
        return str(subject)

    def _encode(self, subject: str, token_type: TokenType, ttl_seconds: int) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": subject,
            "type": token_type,
            "iat": now,
            "exp": now + timedelta(seconds=ttl_seconds),
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)
