# input: httpx
# output: LazyAsyncClient —— 懒创建、可关闭的共享 httpx.AsyncClient 持有器
# pos: 基础设施层 - 外部 HTTP 客户端共享持有器（google/lark/textin 复用，杜绝三处复制）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Shared lazy holder for a reusable ``httpx.AsyncClient``.

避免每次外呼新建连接池 + TLS 握手。持有器绑定首次使用时的事件循环：
在单事件循环的服务进程（uvicorn 单 loop 生命周期）中作为进程级单例是安全的；
若需跨事件循环复用（如测试驱动多个 loop），必须先 ``aclose()`` 再使用。
"""

from __future__ import annotations

from typing import Optional

import httpx


class LazyAsyncClient:
    """Create-on-first-use holder with idempotent async close."""

    def __init__(
        self,
        *,
        timeout: float,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        self._timeout = timeout
        self._transport = transport
        self._client: Optional[httpx.AsyncClient] = None

    def get(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout, transport=self._transport)
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
