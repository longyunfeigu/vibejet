from __future__ import annotations

import asyncio
import concurrent.futures
import contextlib
import functools
import queue
import threading
from typing import Any, Callable, Coroutine, Optional, Tuple

_Job = Tuple[Callable[[], Any], "concurrent.futures.Future[Any]"]


class HandlerThread:
    """One daemon thread that runs submitted calls in order; it starts on first use.

    Unlike ThreadPoolExecutor workers, which Python joins at interpreter exit, a call that
    never returns cannot keep the process alive. Submit only from one thread (the loop).
    """

    def __init__(self, name: str) -> None:
        self._jobs: queue.SimpleQueue[Optional[_Job]] = queue.SimpleQueue()
        self._thread = threading.Thread(target=self._work, name=name, daemon=True)

    @property
    def started(self) -> bool:
        return self._thread.ident is not None

    def is_current(self) -> bool:
        return threading.current_thread() is self._thread

    def submit(self, fn: Callable[..., Any], *args: Any) -> concurrent.futures.Future[Any]:
        future: concurrent.futures.Future[Any] = concurrent.futures.Future()
        self._jobs.put((functools.partial(fn, *args), future))
        if not self.started:
            self._thread.start()
        return future

    def shutdown(self) -> None:
        """Let the thread end once the calls already submitted have run."""
        if self.started:
            self._jobs.put(None)

    def _work(self) -> None:
        while True:
            job = self._jobs.get()
            if job is None:
                return
            call, future = job
            if future.set_running_or_notify_cancel():
                _run_into(call, future)


def _run_into(call: Callable[[], Any], future: concurrent.futures.Future[Any]) -> None:
    try:
        result = call()
    except BaseException as exc:  # noqa: B036 - handed to the awaiting future, as executors do
        future.set_exception(exc)
    else:
        future.set_result(result)


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
