# input: 一个伪 credential（原始 JSON 或未验签 JWT 的 payload 段）
# output: DevGoogleVerifier —— 仅非生产用，不验签直接解码取身份
# owner: wanhua.gu
# pos: 基础设施层 - Google 验签的开发降级实现（mock-first 联调，禁用于生产）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""DEV-ONLY Google verifier: decodes a credential WITHOUT signature verification.

Used for mock-first integration before a real GOOGLE_CLIENT_ID exists. The
composition root only wires this when GOOGLE_CLIENT_ID is unset and the
environment is non-production. Never use this in production.
"""

from __future__ import annotations

import base64
import binascii
import json

from application.ports.oauth import GoogleIdentity
from core.logging_config import get_logger
from domain.common.exceptions import InvalidTokenException

logger = get_logger(__name__)


class DevGoogleVerifier:
    """Decode (not verify) a credential for local development only."""

    def verify(self, credential: str) -> GoogleIdentity:
        payload = self._decode(credential)
        sub = payload.get("sub")
        email = payload.get("email")
        if not sub or not email:
            raise InvalidTokenException("dev credential missing sub/email")
        # 显眼告警：该实现绝不能出现在生产
        logger.warning("google_dev_verifier_used", sub=str(sub))
        return GoogleIdentity(
            sub=str(sub),
            email=str(email),
            email_verified=bool(payload.get("email_verified", True)),
            name=payload.get("name"),
        )

    @staticmethod
    def _decode(credential: str) -> dict:
        # 1) 原始 JSON
        try:
            data = json.loads(credential)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, ValueError):
            pass
        # 2) 形如 JWT：取 payload 段做 base64url 解码
        parts = credential.split(".")
        if len(parts) >= 2:
            seg = parts[1]
            seg += "=" * (-len(seg) % 4)
            try:
                data = json.loads(base64.urlsafe_b64decode(seg))
                if isinstance(data, dict):
                    return data
            except (binascii.Error, json.JSONDecodeError, ValueError):
                pass
        raise InvalidTokenException("dev credential not decodable")
