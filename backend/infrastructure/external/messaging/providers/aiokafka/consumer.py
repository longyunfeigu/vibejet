from __future__ import annotations

import asyncio
import concurrent.futures
import contextlib
import contextvars
import logging
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ...base import ConsumeMiddleware, Consumer, Envelope, HandleResult, Serializer
from ...config import KafkaConfig, RetryConfig
from ...envelope import (
    H_ERROR_CLASS,
    H_ERROR_MSG,
    bump_attempts,
    ensure_original_topic,
    get_not_before_ms,
    now_ms,
    set_not_before_ms,
)
from ...exceptions import NonRetryableError, RequeueProducerFatalError, RetryableError
from ...middlewares.retry import RetryPolicy
from ._client_config import consumer_kwargs, requeue_producer_kwargs, security_kwargs
from ._loop import HandlerThread, LoopThread
from ._offsets import OffsetTracker, PartitionKey

_ERROR_MSG_MAX_BYTES = 2048
_RETRY_SEND_FAILED = "retry requeue failed, message will be redelivered"
_DLQ_SEND_FAILED = "dlq send failed, message will be redelivered"
_COMMIT_FAILED = "offset commit failed, uncommitted records may be redelivered"
_STOP_TIMED_OUT = "consumer did not stop in time; offsets may stay uncommitted"
_OLD_PRODUCER_STUCK = "replaced retry/DLQ producer did not stop within delivery_wait_s; abandoned"
_RESTART_REFUSED = "AiokafkaConsumer cannot be restarted; create a new one"
_PRODUCER_FATAL = "the retry/DLQ producer can no longer send ({error!r}), so the consumer stopped"
_TXN_ID_NOT_UNIQUE = (
    ". KAFKA__TRANSACTIONAL_ID={txn_id!r} must be unique per consumer instance: another live"
    " producer with the same transactional_id fences this one"
)
# Longest single poll. It bounds how late a paused partition is resumed and how long
# the loop runs before it checks the stop flag again.
_POLL_TIMEOUT_MS = 500
# How long stop() waits for the loop to flush offsets and close the clients
_STOP_TIMEOUT_S = 30.0


def _from_headers(raw: Optional[List[tuple[str, bytes]]]) -> Dict[str, bytes]:
    headers: Dict[str, bytes] = {}
    if not raw:
        return headers
    for k, v in raw:
        headers[k] = v
    return headers


def _to_headers(headers: Dict[str, bytes]) -> List[tuple[str, bytes]]:
    return [(k, v) for k, v in headers.items()]


def _keys(partitions: Iterable[Any]) -> List[PartitionKey]:
    return [(tp.topic, tp.partition) for tp in partitions]


def _set_error_headers(headers: Dict[str, bytes], error_class: bytes, message: str) -> None:
    headers[H_ERROR_CLASS] = error_class
    headers[H_ERROR_MSG] = message.encode("utf-8")[:_ERROR_MSG_MAX_BYTES]


def _record_handler_error(headers: Dict[str, bytes], err: Optional[BaseException]) -> None:
    if err is not None:
        _set_error_headers(headers, type(err).__name__.encode("utf-8"), str(err))


def _invoke(
    handler: Consumer.Handler, env: Envelope
) -> Tuple[HandleResult, Optional[BaseException]]:
    """Run the handler; map its exceptions to a result (unexpected errors are retried)."""
    try:
        return handler(env), None
    except RetryableError as e:
        return HandleResult.RETRY, e
    except NonRetryableError as e:
        return HandleResult.DROP, e
    except Exception as e:  # noqa: BLE001
        return HandleResult.RETRY, e


def _read_outcome(future: asyncio.Future[Any]) -> None:
    """Read a finished future's error so asyncio does not log it as never retrieved."""
    if not future.cancelled():
        future.exception()


def _requeue_backoff_ms(retry: RetryConfig) -> int:
    """How long a record whose retry/DLQ send failed waits before it is consumed again.

    Reuses the first retry layer's delay (KAFKA__RETRY_LAYERS), and never less than one
    poll (_POLL_TIMEOUT_MS), so a broker that rejects every send at once cannot turn the
    retry into a busy loop.
    """
    first_delay = retry.layers[0].delay_ms if retry.layers else 0
    return int(max(first_delay, _POLL_TIMEOUT_MS))


class _RebalanceCallbacks:
    """Forget stale offsets on assign; on revoke drop pause state and flush processed offsets."""

    def __init__(self, parent: AiokafkaConsumer) -> None:
        self._parent = parent

    def on_partitions_assigned(self, assigned: Any) -> None:
        self._parent._offsets.forget(_keys(assigned))

    async def on_partitions_revoked(self, revoked: Any) -> None:
        # aiokafka awaits this before the partitions move to another member
        await self._parent._release_partitions(revoked)


def _make_rebalance_listener(parent: AiokafkaConsumer) -> Any:
    """Bind the callbacks to aiokafka's ConsumerRebalanceListener.

    aiokafka's subscribe() rejects any listener that is not an instance of it; the
    base is imported here, like the clients, so aiokafka stays an optional extra.
    """
    from aiokafka import ConsumerRebalanceListener

    class _RebalanceListener(_RebalanceCallbacks, ConsumerRebalanceListener):
        pass

    return _RebalanceListener(parent)


class AiokafkaConsumer(Consumer):
    def __init__(
        self,
        cfg: KafkaConfig,
        retry: RetryConfig,
        serializer: Serializer,
        middlewares: Optional[List[ConsumeMiddleware]] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.cfg = cfg
        self.retry_cfg = retry
        self.serializer = serializer
        self.middlewares = middlewares or []
        self.log = logger or logging.getLogger("messaging.aiokafka.consumer")
        self._group_id: Optional[str] = None
        self._topics: Optional[List[str]] = None
        self._stopped = False
        self._retry_policy = RetryPolicy(retry)
        self._requeue_backoff_ms = _requeue_backoff_ms(retry)
        self._offsets = OffsetTracker(cfg.consumer.commit_every_n, cfg.consumer.commit_interval_ms)
        self._delivery_wait_s: float = self.cfg.producer.delivery_wait_s
        try:
            from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
        except Exception as e:  # noqa: BLE001
            raise ImportError(
                "aiokafka is required for AiokafkaConsumer. Install via `pip install aiokafka`."
            ) from e
        self._AIOKafkaConsumer = AIOKafkaConsumer
        self._AIOKafkaProducer = AIOKafkaProducer
        self._loop = LoopThread()
        # Sync handlers run on one daemon thread (started on first use): the event loop keeps
        # sending heartbeats while a handler works, and a stuck handler cannot block exit
        self._handlers = HandlerThread("kafka-consumer-handler")
        # Set while no record is in flight; a revoke waits for it
        self._idle = asyncio.Event()
        self._idle.set()
        self._run_future: Optional[concurrent.futures.Future[Any]] = None
        self._consumer: Any = None
        self._producer: Any = None
        self._producer_cls: Any = None
        self._producer_kwargs: Dict[str, Any] = {}
        # True after a failed requeue: the next requeue starts with a new producer
        self._producer_stale = False
        self._tp_cls: Any = None
        self._fenced_cls: Any = None
        # partition -> due time (ms) of its deferred head record
        self._paused: Dict[Any, int] = {}

    def subscribe(self, topics: List[str], group_id: str) -> None:
        self._topics = topics
        self._group_id = group_id

    def start(self, handler: Consumer.Handler) -> None:
        if not self._topics or not self._group_id:
            raise RuntimeError("Call subscribe(topics, group_id) before start().")
        if self._run_future is not None:
            raise RuntimeError(_RESTART_REFUSED)

        self._loop.start()
        self._run_future = self._loop.submit(self._run(handler))
        try:
            self._run_future.result()
        finally:
            # nothing else runs on the loop or the handler thread once the consume loop is over
            self._loop.stop()
            self._handlers.shutdown()

    def stop(self) -> None:
        """Stop consuming: flush processed offsets, close the clients, end start().

        From another thread this blocks until that is done (at most _STOP_TIMEOUT_S);
        the loop notices the flag within one poll (_POLL_TIMEOUT_MS). From inside a
        handler it only sets the flag; the loop ends after that record. stop() never
        halts the event loop itself: start() does that once the consume coroutine has
        finished, so a slow shutdown still completes instead of freezing half-way.
        """
        self._stopped = True
        run = self._run_future
        if run is None or self._on_consumer_thread():
            return
        done, _ = concurrent.futures.wait([run], timeout=_STOP_TIMEOUT_S)
        if not done:
            self.log.warning(_STOP_TIMED_OUT)

    def _on_consumer_thread(self) -> bool:
        """The loop or the handler thread: waiting there for start() to end would deadlock."""
        return bool(self._loop.in_loop_thread() or self._handlers.is_current())

    async def _run(self, handler: Consumer.Handler) -> None:
        # Lazy imports to avoid hard dependency unless this path is used
        from aiokafka import AIOKafkaConsumer, AIOKafkaProducer, TopicPartition
        from aiokafka.errors import ProducerFenced

        self._tp_cls = TopicPartition
        self._fenced_cls = ProducerFenced
        try:
            await self._start_clients(AIOKafkaConsumer, AIOKafkaProducer)
            self._consumer.subscribe(self._topics, listener=_make_rebalance_listener(self))
            while not self._stopped:
                await self._poll_once(handler)
        finally:
            # Also runs when startup or the loop fails: flush offsets, close what was opened
            await self._shutdown()

    async def _shutdown(self) -> None:
        if self._consumer is not None:
            await self._commit_offsets()
        await self._stop_clients()

    async def _poll_once(self, handler: Consumer.Handler) -> None:
        self._resume_due_partitions()
        batch = await self._consumer.getmany(timeout_ms=self._poll_timeout_ms(), max_records=1)
        for records in batch.values():
            for msg in records:
                await self._process(msg, handler)
        if self._offsets.commit_due():
            await self._commit_offsets()

    def _poll_timeout_ms(self) -> int:
        """Wake up by the time the earliest paused partition is due, at most _POLL_TIMEOUT_MS."""
        if not self._paused:
            return _POLL_TIMEOUT_MS
        until_due: int = min(self._paused.values()) - now_ms()
        return max(0, min(_POLL_TIMEOUT_MS, until_due))

    def _resume_due_partitions(self) -> None:
        now = now_ms()
        for tp, due in list(self._paused.items()):
            if due <= now:
                del self._paused[tp]
                self._consumer.resume(tp)

    async def _commit_offsets(self, keys: Optional[Iterable[PartitionKey]] = None) -> None:
        """Commit processed offsets (all partitions, or only `keys`); failures stay pending."""
        if keys is None:
            # a full flush starts the next batch whether or not it succeeds
            self._offsets.attempted()
        offsets = self._owned(self._offsets.uncommitted(keys))
        if not offsets:
            return
        try:
            await self._consumer.commit(
                offsets={self._tp_cls(t, p): offset for (t, p), offset in offsets.items()}
            )
        except Exception as exc:
            # 位点留在待提交里，下一批再试；进程若此时退出，这些记录会重投（at-least-once）
            self.log.warning(_COMMIT_FAILED, extra={"partitions": len(offsets), "error": str(exc)})
            return
        self._offsets.mark_committed(offsets)

    def _owned(self, offsets: Dict[PartitionKey, int]) -> Dict[PartitionKey, int]:
        """Keep only partitions still assigned here; forget the rest.

        aiokafka rejects a whole commit that names an unassigned partition, so one stale
        entry would fail every later batch. A partition can go away without a successful
        revoke flush, for example when the member is evicted and that flush fails.
        """
        if not offsets:
            return offsets
        assigned = set(_keys(self._consumer.assignment()))
        self._offsets.forget([key for key in offsets if key not in assigned])
        return {key: offset for key, offset in offsets.items() if key in assigned}

    async def _release_partitions(self, partitions: Any) -> None:
        """On revoke: let the record in flight finish, flush the partitions' processed
        offsets, then drop their local state.

        The handler runs off the loop, so a rebalance can start mid-record. Waiting for it
        commits that record here instead of handing it to the new owner a second time. The
        group waits for this member up to rebalance_timeout_ms, which consumer_kwargs sets
        to max_poll_interval_ms; a handler slower than that loses the partition anyway.
        """
        await self._idle.wait()
        keys = _keys(partitions)
        for tp in partitions:
            self._paused.pop(tp, None)
        await self._commit_offsets(keys)
        self._offsets.forget(keys)

    async def _start_clients(self, consumer_cls: Any, producer_cls: Any) -> None:
        # One TLS/SASL setup (one SSL context) shared by the consumer and its requeue producer
        security = security_kwargs(self.cfg)
        self._consumer = consumer_cls(
            bootstrap_servers=self.cfg.bootstrap_servers,
            client_id=self.cfg.client_id,
            **consumer_kwargs(self.cfg, self._group_id),
            **security,
        )
        await self._consumer.start()
        self._producer_cls = producer_cls
        self._producer_kwargs = {
            "bootstrap_servers": self.cfg.bootstrap_servers,
            "client_id": self.cfg.client_id + ".consumer-producer",
            **requeue_producer_kwargs(self.cfg),
            **security,
        }
        self._producer = producer_cls(**self._producer_kwargs)
        await self._producer.start()

    async def _stop_clients(self) -> None:
        # Stop whichever clients were constructed; stop errors are swallowed
        for client in (self._consumer, self._producer):
            if client is not None:
                with contextlib.suppress(Exception):
                    await client.stop()

    async def _replace_producer(self) -> None:
        """Swap the retry/DLQ producer for a new one before retrying a failed requeue.

        aiokafka (0.13) never resets a partition's sequence number after the broker
        rejects a batch, so every later send to that partition fails with
        OutOfOrderSequenceNumber. A new producer gets a fresh producer id or epoch and
        starts its sequences at zero. Never used after fencing: that stops the consumer.
        """
        old = self._producer
        with contextlib.suppress(Exception):
            try:
                await asyncio.wait_for(old.stop(), timeout=self._delivery_wait_s)
            except asyncio.TimeoutError:
                self.log.warning(
                    _OLD_PRODUCER_STUCK,
                    extra={"producer": repr(old), "client_id": self._producer_kwargs["client_id"]},
                )
        self._producer = self._producer_cls(**self._producer_kwargs)
        self._producer_stale = False
        await self._producer.start()

    async def _process(self, msg: Any, handler: Consumer.Handler) -> None:
        # a revoke waits for this record, so its offset is flushed before the partition moves
        self._idle.clear()
        try:
            await self._handle_record(msg, handler)
        finally:
            self._idle.set()

    async def _handle_record(self, msg: Any, handler: Consumer.Handler) -> None:
        headers = _from_headers(msg.headers)
        if self._defer_if_not_due(msg, headers):
            return
        value = msg.value
        try:
            payload = self.serializer.loads(value) if value is not None else None
        except Exception as e:  # noqa: BLE001
            _set_error_headers(headers, b"SerializationError", str(e))
            await self._forward(msg, self._dlq_topic(msg.topic), headers, _DLQ_SEND_FAILED)
            return
        await self._dispatch(msg, headers, payload, handler)

    def _defer_if_not_due(self, msg: Any, headers: Dict[str, bytes]) -> bool:
        """Pause the record's partition until x-retry-not-before; True when it was deferred.

        Only that partition waits: the loop keeps polling the others, so a long delay
        never counts against max_poll_interval_ms.
        """
        due = get_not_before_ms(headers)
        if due is None or due <= now_ms():
            return False
        self._pause_at(msg, due)
        return True

    def _pause_at(self, msg: Any, due_ms: int) -> None:
        """Pause the record's partition and rewind to it; it is fetched again once due."""
        tp = self._tp_cls(msg.topic, msg.partition)
        self._consumer.pause(tp)
        self._consumer.seek(tp, msg.offset)
        self._paused[tp] = due_ms

    def _retry_later(self, msg: Any) -> None:
        """After a failed retry/DLQ send: consume the record again after the backoff.

        The offset is not advanced, so later records of that partition wait behind it and
        no commit can pass it; other partitions keep flowing.
        """
        if self._tp_cls(msg.topic, msg.partition) not in self._consumer.assignment():
            # revoked during the send: the new owner re-consumes it from the committed offset
            return
        self._pause_at(msg, now_ms() + self._requeue_backoff_ms)

    async def _dispatch(
        self, msg: Any, headers: Dict[str, bytes], payload: Any, handler: Consumer.Handler
    ) -> None:
        topic, partition, offset = msg.topic, msg.partition, msg.offset
        env = Envelope(payload=payload, key=msg.key, headers=headers)
        for m in self.middlewares:
            env = m.before_handle(topic, partition, offset, env)

        result, err = await self._call_handler(handler, env)
        try:
            await self._settle(msg, headers, result, err)
        finally:
            for m in self.middlewares:
                m.after_handle(topic, partition, offset, env, result, err)

    async def _call_handler(
        self, handler: Consumer.Handler, env: Envelope
    ) -> Tuple[HandleResult, Optional[BaseException]]:
        """Run the sync handler on the handler thread so the event loop keeps heartbeating.

        Middlewares stay on the loop, so before_handle and after_handle share one context
        (the metrics middleware keeps its start time in a ContextVar). The handler runs in
        a copy of that context: it sees what before_handle set, but what it sets itself
        stays in the copy.
        """
        context = contextvars.copy_context()
        future = self._handlers.submit(context.run, _invoke, handler, env)
        outcome: Tuple[HandleResult, Optional[BaseException]] = await asyncio.wrap_future(future)
        return outcome

    async def _settle(
        self,
        msg: Any,
        headers: Dict[str, bytes],
        result: HandleResult,
        err: Optional[BaseException],
    ) -> None:
        if result == HandleResult.ACK:
            # committed with the next batch (or on revoke / stop)
            self._offsets.processed(msg.topic, msg.partition, msg.offset)
        elif result == HandleResult.RETRY:
            await self._requeue_for_retry(msg, headers, err)
        elif result == HandleResult.DROP:
            _record_handler_error(headers, err)
            await self._forward(msg, self._dlq_topic(msg.topic), headers, _DLQ_SEND_FAILED)

    async def _requeue_for_retry(
        self, msg: Any, headers: Dict[str, bytes], err: Optional[BaseException]
    ) -> None:
        decision = self._retry_policy.next_for_retry(msg.topic)
        ensure_original_topic(headers, msg.topic)
        bump_attempts(headers)
        if not decision.is_dlq:
            set_not_before_ms(headers, now_ms() + decision.delay_ms)
        _record_handler_error(headers, err)
        await self._forward(msg, decision.next_topic, headers, _RETRY_SEND_FAILED)

    async def _forward(
        self, msg: Any, topic: str, headers: Dict[str, bytes], failure_message: str
    ) -> None:
        """Produce the original record to a retry/DLQ topic and commit its offset.

        When that fails nothing is committed and the record is consumed again after the
        requeue backoff (see _retry_later), so it is never skipped. A fenced producer, or
        one in aiokafka's fatal state, can never send again: that stops the consumer.
        """
        try:
            await self._requeue(msg, topic, headers)
        except Exception as send_exc:
            if self._producer_is_fatal(send_exc):
                raise RequeueProducerFatalError(self._fatal_message(send_exc)) from send_exc
            await self._abort_open_transaction()
            self._producer_stale = True
            self._retry_later(msg)
            # 位点没前进：这条退避后重新消费（分区若已被撤销，由新的属主从已提交位点重投）
            self.log.warning(
                failure_message,
                extra={
                    "topic": msg.topic,
                    "partition": msg.partition,
                    "offset": msg.offset,
                    "error": str(send_exc),
                },
            )

    def _producer_is_fatal(self, exc: BaseException) -> bool:
        """Fenced, or aiokafka's transaction manager is in its fatal state."""
        if isinstance(exc, self._fenced_cls):
            return True
        # aiokafka has no public accessor for the producer's transaction manager
        txn_manager = getattr(self._producer, "_txn_manager", None)
        return txn_manager is not None and bool(txn_manager.is_fatal_error())

    def _fatal_message(self, exc: BaseException) -> str:
        message = _PRODUCER_FATAL.format(error=exc)
        if self.cfg.transactional_id:
            message += _TXN_ID_NOT_UNIQUE.format(txn_id=self.cfg.transactional_id)
        return message

    async def _requeue(self, msg: Any, topic: str, headers: Dict[str, bytes]) -> None:
        """Send the record to `topic` within delivery_wait_s, then mark it processed.

        A send that times out may still land; the retry then writes it a second time to
        the retry/DLQ topic (at-least-once).
        """
        if self._producer_stale:
            await self._replace_producer()
        if self.cfg.transactional_id:
            await asyncio.wait_for(
                self._requeue_in_transaction(msg, topic, headers), timeout=self._delivery_wait_s
            )
            return
        await asyncio.wait_for(
            self._producer.send_and_wait(
                topic, value=msg.value, key=msg.key, headers=_to_headers(headers)
            ),
            timeout=self._delivery_wait_s,
        )
        self._offsets.processed(msg.topic, msg.partition, msg.offset)
        # commit right away so a crash does not requeue the same record twice
        await self._commit_offsets()

    async def _requeue_in_transaction(
        self, msg: Any, topic: str, headers: Dict[str, bytes]
    ) -> None:
        """Produce to the retry/DLQ topic and commit the source offset atomically."""
        source = self._tp_cls(msg.topic, msg.partition)
        async with self._producer.transaction():
            delivery = await self._producer.send(
                topic, value=msg.value, key=msg.key, headers=_to_headers(headers)
            )
            # if the offsets step fails first (e.g. fenced), nobody awaits the delivery
            delivery.add_done_callback(_read_outcome)
            await self._producer.send_offsets_to_transaction(
                {source: msg.offset + 1}, self._group_id
            )
            # aiokafka commits a transaction even when one of its records was rejected;
            # waiting for the delivery makes a rejection abort it (else the record is lost)
            await delivery
        self._offsets.processed(msg.topic, msg.partition, msg.offset)
        self._offsets.mark_committed({(msg.topic, msg.partition): msg.offset + 1})

    async def _abort_open_transaction(self) -> None:
        """After a failed transactional requeue, leave the producer ready for the next one."""
        if not self.cfg.transactional_id:
            return
        # The transaction context already aborts when its body fails; this covers a
        # failed commit. Aborting with no open transaction raises, which is fine here.
        with contextlib.suppress(Exception):
            await self._producer.abort_transaction()

    def _dlq_topic(self, topic: str) -> str:
        return f"{topic}.{self.retry_cfg.dlq_suffix}"
