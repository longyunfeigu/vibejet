# input: pwdlib（argon2）
# output: PwdlibPasswordHasher 密码哈希实现
# owner: wanhua.gu
# pos: 基础设施层 - PasswordHasher 端口的 pwdlib/argon2 实现；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Password hashing via pwdlib (argon2, modern maintained successor to passlib)."""

from __future__ import annotations

from pwdlib import PasswordHash


class PwdlibPasswordHasher:
    """PasswordHasher port implementation backed by pwdlib's recommended setup."""

    def __init__(self) -> None:
        self._hasher = PasswordHash.recommended()

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password: str, hashed: str) -> bool:
        if not hashed:
            return False
        try:
            return self._hasher.verify(password, hashed)
        except Exception:
            # Malformed/legacy hash formats must fail closed, not raise 500
            return False
