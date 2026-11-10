# input: 无（标准库 asyncio / threading）
# output: LoopThread（后台线程里的独立事件循环：start / submit / run_coro / in_loop_thread / stop；事件循环在 start() 时才创建、线程退出时关闭，不可重启）
# owner: unknown
# pos: 基础设施层 - aiokafka 同步外观用的事件循环线程（发布者与消费者共用）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
from __future__ import annotations

import asyncio
import concurrent.futures
import contextlib
import threading
from typing import Any, Coroutine, Optional


class LoopThread:
    def __init__(self) -> None:
        # created by start(): a LoopThread that is never started holds no event loop
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._started = threading.Event()

    def _run(self) -> None:
        loop = self._require_loop()
        asyncio.set_event_loop(loop)
        self._started.set()
        try:
            loop.run_forever()
        finally:
            # free the loop's selector and self-pipe once nothing runs on it any more
            loop.close()

    def start(self) -> None:
        if self._loop is not None:
            raise RuntimeError("LoopThread cannot be restarted; create a new one")
        self._loop = asyncio.new_event_loop()
        self._thread.start()
        self._started.wait(5)

    def stop(self) -> None:
        if not self._thread.is_alive():
            return
        loop = self._require_loop()
        # another caller may have stopped (and so closed) the loop a moment ago
        with contextlib.suppress(RuntimeError):
            loop.call_soon_threadsafe(loop.stop)
        # The loop thread cannot join itself; it exits once the current callback returns
        if not self.in_loop_thread():
            self._thread.join(timeout=5)

    def in_loop_thread(self) -> bool:
        return threading.current_thread() is self._thread

    def submit(self, coro: Coroutine[Any, Any, Any]) -> concurrent.futures.Future[Any]:
        return asyncio.run_coroutine_threadsafe(coro, self._require_loop())

    def run_coro(self, coro: Coroutine[Any, Any, Any]) -> Any:
        return self.submit(coro).result()

    def _require_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None:
            raise RuntimeError("LoopThread is not started")
        return self._loop
