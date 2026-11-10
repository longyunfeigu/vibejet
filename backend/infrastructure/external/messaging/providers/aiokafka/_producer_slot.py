# input: 异步工厂（新建并启动一个 producer）, 标准库 asyncio
# output: ProducerSlot（发布者当前在用的 producer：lease() 借用；replace(failed) 对同一个失效 producer 只换一次；旧 producer 等最后一次借用结束后才在后台关闭；close() 关掉全部）
# owner: unknown
# pos: 基础设施层 - aiokafka 发布者的可替换 producer（绕开 aiokafka 0.13 被拒后分区序号再也对不上的问题）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
from __future__ import annotations

import asyncio
import contextlib
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, Set


class ProducerSlot:
    """The publisher's current producer, replaceable while other sends are in flight.

    Every send borrows the current producer through lease(). replace(failed) swaps in a
    new producer only while `failed` is still the current one, so concurrent callers that
    hit the same failure share one rebuild. The old producer is stopped in the background
    once its last lease ends, so no send ever runs on a closed producer.
    All methods run on the publisher's event-loop thread.
    """

    def __init__(self, factory: Callable[[], Awaitable[Any]]) -> None:
        self._factory = factory
        self._current: Any = None
        self._leases: Dict[Any, int] = {}
        self._drained: Dict[Any, asyncio.Event] = {}
        self._lock = asyncio.Lock()
        self._retiring: Set["asyncio.Task[None]"] = set()

    @property
    def current(self) -> Any:
        return self._current

    async def open(self) -> None:
        self._current = await self._factory()

    @contextlib.asynccontextmanager
    async def lease(self) -> AsyncIterator[Any]:
        producer = self._current
        self._leases[producer] = self._leases.get(producer, 0) + 1
        try:
            yield producer
        finally:
            self._release(producer)

    def _release(self, producer: Any) -> None:
        self._leases[producer] -= 1
        if self._leases[producer]:
            return
        del self._leases[producer]
        drained = self._drained.pop(producer, None)
        if drained is not None:
            drained.set()

    async def replace(self, failed: Any) -> bool:
        """Swap in a new producer unless `failed` was already replaced; True when this call did.

        A factory error propagates and leaves `failed` in place for the next attempt.
        """
        async with self._lock:
            if self._current is not failed:
                return False
            self._current = await self._factory()
        task = asyncio.get_running_loop().create_task(self._retire(failed))
        self._retiring.add(task)
        task.add_done_callback(self._retiring.discard)
        return True

    async def _retire(self, old: Any) -> None:
        if old in self._leases:
            await self._drained.setdefault(old, asyncio.Event()).wait()
        with contextlib.suppress(Exception):
            await old.stop()

    async def close(self) -> None:
        """Wait for replaced producers to stop, then stop the current one."""
        if self._retiring:
            await asyncio.gather(*self._retiring, return_exceptions=True)
        if self._current is not None:
            await self._current.stop()
