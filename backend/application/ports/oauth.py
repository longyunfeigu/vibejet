# input: 无外部依赖（纯 Protocol/数据类定义）
# output: GoogleIdentityVerifier 端口, GoogleAuthCodeExchanger 端口, GoogleIdentity 数据类
# owner: wanhua.gu
# pos: 应用层端口 - Google 身份验证抽象（ID Token 验签 + 授权码交换），infrastructure/external/google 提供实现；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""OAuth ports: turning a Google credential / auth code into a trusted identity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass(frozen=True)
class GoogleIdentity:
    """Trusted identity extracted from a verified Google ID token."""

    sub: str  # Google 稳定唯一用户标识
    email: str
    email_verified: bool
    name: Optional[str] = None


class GoogleIdentityVerifier(Protocol):
    def verify(self, credential: str) -> GoogleIdentity:
        """Verify a Google ID token (credential) and return its identity.

        Implementations MUST validate signature, audience (== our client_id),
        issuer and expiry, and raise ``InvalidTokenException`` on any failure.
        """
        ...


class GoogleAuthCodeExchanger(Protocol):
    async def exchange(self, code: str) -> GoogleIdentity:
        """Exchange a Google authorization code for a verified identity.

        Implementations MUST POST the code to Google's token endpoint with the
        server-side client_secret, then validate the returned ID token (signature,
        audience, issuer, expiry) and return its identity. Any failure (token
        exchange error, missing/invalid ID token) MUST raise ``InvalidTokenException``.
        """
        ...
