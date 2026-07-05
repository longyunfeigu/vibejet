# input: pwdlib（argon2）, asyncio.to_thread
# output: PwdlibPasswordHasher 密码哈希实现（异步端口，计算卸载线程池）
# owner: wanhua.gu
# pos: 基础设施层 - PasswordHasher 端口的 pwdlib/argon2 实现；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Password hashing via pwdlib (argon2, modern maintained successor to passlib)."""

from __future__ import annotations

import asyncio

from pwdlib import PasswordHash


class PwdlibPasswordHasher:
    """PasswordHasher port implementation backed by pwdlib's recommended setup.

    argon2 单次哈希/校验耗时数十~上百毫秒（算法设计使然），必须经
    ``asyncio.to_thread`` 卸载，避免阻塞事件循环。
    """

    def __init__(self) -> None:
        self._hasher = PasswordHash.recommended()

    async def hash(self, password: str) -> str:
        return await asyncio.to_thread(self._hasher.hash, password)

    async def verify(self, password: str, hashed: str) -> bool:
        if not hashed:
            return False
        try:
            return await asyncio.to_thread(self._hasher.verify, password, hashed)
        except Exception:
            # Malformed/legacy hash formats must fail closed, not raise 500
            return False
