# input: 无外部依赖（纯 Protocol/数据类定义）
# output: GoogleIdentityVerifier/GoogleAuthCodeExchanger/LarkAuthCodeExchanger 端口, GoogleIdentity/OAuthIdentity 数据类
# owner: wanhua.gu
# pos: 应用层端口 - 联合登录身份抽象（Google ID Token 验签/授权码交换 + 飞书/Lark 授权码交换），infrastructure/external/{google,lark} 提供实现；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""OAuth ports: turning a Google / Feishu / Lark credential or auth code into a trusted identity."""

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


@dataclass(frozen=True)
class OAuthIdentity:
    """Provider-neutral federated identity used by the find/link/create flow.

    ``email`` 可空（如飞书/Lark 用户无企业邮箱）；``email_verified`` 仅在可信邮箱
    （Google `email_verified=true` / 飞书 `enterprise_email`）时为真，决定是否按邮箱自动链接已有账号。
    """

    sub: str  # provider 稳定唯一标识（飞书/Lark 为 union_id）
    email: Optional[str]
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


class LarkAuthCodeExchanger(Protocol):
    async def exchange(self, code: str) -> OAuthIdentity:
        """Exchange a Feishu/Lark authorization code for a trusted identity.

        Implementations MUST POST the code to the v2 OIDC token endpoint with the
        server-side app_secret to obtain a user access_token, then call the user_info
        endpoint to resolve the identity. Any failure (token exchange error, user_info
        error, missing stable id) MUST raise ``InvalidTokenException``.
        """
        ...
