# input: AiokafkaConsumer + monkeypatch 进 aiokafka 模块的 fake AIOKafkaConsumer/AIOKafkaProducer（无真实 broker）
# output: AiokafkaConsumer.start 特征测试：启停与退出（含跨线程 stop()）、建连参数与 TLS、反序列化失败转 DLQ、中间件、重试分层/DLQ、批量提交位点（按条数/按间隔、失败后随下一批重试、只提交仍分配的分区）、延迟重投、再均衡监听（撤销时冲刷位点）、事务性重投、告警日志；rebalance_timeout_ms 跟随 max_poll_interval_ms；handler 跑在守护线程上（卡死也不拦进程退出）；被换下的重投 producer 关不掉时点名告警；把捕获到的构造参数、listener、pause/resume 参数回放给真实 aiokafka 校验契约
# pos: 后端测试 - Kafka 消费主循环行为锁定；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Characterization tests for ``AiokafkaConsumer.start``.

这些测试锁定的是当前行为；改行为时要同步改对应断言。
handler 在独立的 handler 线程上跑（事件循环照常心跳），所以 handler 里调用的 fake 方法
（revoke_soon 等）都必须线程安全；中间件仍在事件循环上。
与真实 aiokafka 的契约（构造参数、listener 类型、pause/resume 参数形状）通过把 fake
捕获到的调用回放给真实客户端来校验，不需要 broker；端到端行为见 test_kafka_integration.py。

start() 在 LoopThread 的事件循环里跑消费协程，并在协程内部延迟导入
AIOKafkaConsumer / AIOKafkaProducer / TopicPartition，所以 fake 通过 monkeypatch
注入 aiokafka 模块本身；TopicPartition 保留真实 namedtuple，便于按值断言。
fake getmany 在脚本耗尽时抛 _StopLoop，用它结束消费循环（idle_when_drained 时改为
像空闲的真实 consumer 一样按超时返回空，用来测跨线程 stop()）。
位点按批提交、循环退出时再冲刷一次，所以多数用例看到的提交发生在退出时。
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import contextvars
import gc
import logging
import os
import ssl
import subprocess  # nosec B404 - runs the test's own interpreter
import sys
import threading
import time
import warnings
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Iterator, Optional

import pytest

from infrastructure.external.messaging.base import Envelope, HandleResult
from infrastructure.external.messaging.config import (
    ConsumerTuning,
    KafkaConfig,
    ProducerTuning,
    RetryConfig,
    RetryLayer,
    SASLConfig,
    TLSConfig,
)
from infrastructure.external.messaging.envelope import now_ms
from infrastructure.external.messaging.exceptions import (
    NonRetryableError,
    RequeueProducerFatalError,
    RetryableError,
)
from infrastructure.external.messaging.providers.aiokafka import consumer as consumer_module
from infrastructure.external.messaging.providers.aiokafka.consumer import AiokafkaConsumer
from infrastructure.external.messaging.serializers.json import JsonSerializer

aiokafka = pytest.importorskip("aiokafka")
TopicPartition = aiokafka.TopicPartition
ConsumerRebalanceListener = aiokafka.ConsumerRebalanceListener
IllegalStateError = pytest.importorskip("aiokafka.errors").IllegalStateError
ProducerFenced = pytest.importorskip("aiokafka.errors").ProducerFenced
REAL_AIOKAFKA_CONSUMER = aiokafka.AIOKafkaConsumer
REAL_AIOKAFKA_PRODUCER = aiokafka.AIOKafkaProducer

LOGGER_NAME = "messaging.aiokafka.consumer"
COMMIT_FAILED = "offset commit failed, uncommitted records may be redelivered"
RETRY_SEND_FAILED = "retry requeue failed, message will be redelivered"
DLQ_SEND_FAILED = "dlq send failed, message will be redelivered"
OLD_PRODUCER_STUCK = "replaced retry/DLQ producer did not stop within delivery_wait_s; abandoned"
BACKEND_DIR = Path(__file__).resolve().parents[1]
# 第一层重试 50ms：重投发送失败后的退避取它，但不低于一个轮询周期（500ms）
FAST_RETRY = RetryConfig(layers=[RetryLayer(suffix="retry.fast", delay_ms=50)])
TEST_SASL_CRED = "unit-test-cred"
BAD_CA = "/missing/ca.pem"


class _StopLoop(Exception):
    """fake getmany 在脚本耗尽时抛出，用来结束 start() 的消费循环。"""


@dataclass
class FakeRecord:
    topic: str
    partition: int
    offset: int
    value: Optional[bytes]
    key: Optional[bytes] = None
    headers: Optional[list[tuple[str, bytes]]] = None


@dataclass
class SentMessage:
    topic: str
    value: Optional[bytes]
    key: Optional[bytes]
    headers: list[tuple[str, bytes]]

    @property
    def header_map(self) -> dict[str, bytes]:
        return dict(self.headers)


@dataclass
class FakeBroker:
    """记录 fake 客户端上的全部调用；故障字段由测试按需注入。"""

    records: deque[FakeRecord] = field(default_factory=deque)
    events: list[tuple[Any, ...]] = field(default_factory=list)
    sent: list[SentMessage] = field(default_factory=list)
    consumer: Optional["FakeConsumer"] = None
    producer: Optional["FakeProducer"] = None
    consumer_start_error: Optional[Exception] = None
    producer_start_error: Optional[Exception] = None
    consumer_stop_error: Optional[Exception] = None
    producer_stop_error: Optional[Exception] = None
    # 依次加到 producer.stop() 上的耗时（秒）
    producer_stop_delays: deque[float] = field(default_factory=deque)
    subscribe_error: Optional[Exception] = None
    txn_commit_error: Optional[Exception] = None
    # 发送故障：send_error 每次都抛；send_errors 按顺序各抛一次
    send_error: Optional[Exception] = None
    send_errors: deque[Exception] = field(default_factory=deque)
    send_delay_s: float = 0.0
    # 打开后 producer 的事务管理器报告致命状态（真实 aiokafka 被隔离后就是这样）
    producer_fatal: bool = False
    producers: list["FakeProducer"] = field(default_factory=list)
    # commit 故障：commit_error 每次都抛；commit_errors 按顺序各抛一次
    commit_error: Optional[Exception] = None
    commit_errors: deque[Exception] = field(default_factory=deque)
    # 脚本耗尽后像空闲的真实 consumer 一样按超时返回空，而不是抛 _StopLoop
    idle_when_drained: bool = False
    idle_polled: threading.Event = field(default_factory=threading.Event)
    paused: set[Any] = field(default_factory=set)
    # 分配给消费者的分区：投喂的记录所在分区自动算已分配，撤销完成后移除
    assigned: set[Any] = field(default_factory=set)
    # 撤销回调任务：真实 aiokafka 由协调器在自己的任务里调用 listener
    rebalance_tasks: list["concurrent.futures.Future[None]"] = field(default_factory=list)
    poll_timeouts: list[int] = field(default_factory=list)
    last_delivered: dict[tuple[str, int], FakeRecord] = field(default_factory=dict)

    def feed(self, *records: FakeRecord) -> None:
        self.records.extend(records)
        self.assigned.update(TopicPartition(r.topic, r.partition) for r in records)

    def next_deliverable(self) -> Optional[FakeRecord]:
        """按投喂顺序取第一条不在暂停分区上的记录（暂停分区的记录留在队列里）。"""
        for rec in self.records:
            if TopicPartition(rec.topic, rec.partition) not in self.paused:
                self.records.remove(rec)
                return rec
        return None

    def event_names(self) -> list[str]:
        return [event[0] for event in self.events]

    def commits(self) -> list[Any]:
        return [event[1] for event in self.events if event[0] == "commit"]


class FakeConsumer:
    def __init__(self, broker: FakeBroker, **kwargs: Any) -> None:
        self.broker = broker
        self.kwargs = kwargs
        self.listener: Any = None
        # 在消费协程里构造：记下事件循环，handler 线程里的 revoke_soon 要往这里投递
        self.loop = asyncio.get_running_loop()
        broker.consumer = self

    async def start(self) -> None:
        self.broker.events.append(("consumer.start",))
        if self.broker.consumer_start_error is not None:
            raise self.broker.consumer_start_error

    def subscribe(self, topics: list[str], listener: Any = None) -> None:
        self.broker.events.append(("subscribe", list(topics)))
        self.listener = listener
        if self.broker.subscribe_error is not None:
            raise self.broker.subscribe_error

    async def getmany(
        self, *partitions: Any, timeout_ms: int = 0, max_records: Optional[int] = None
    ) -> dict[Any, list[FakeRecord]]:
        # 再均衡在 getmany 期间完成：先跑完排进来的撤销回调
        while self.broker.rebalance_tasks:
            await asyncio.wrap_future(self.broker.rebalance_tasks.pop(0))
        self.broker.poll_timeouts.append(timeout_ms)
        rec = self.broker.next_deliverable()
        if rec is None:
            if not self.broker.records:
                if not self.broker.idle_when_drained:
                    raise _StopLoop()
                self.broker.idle_polled.set()
            # 没有可投递的记录：像真实 getmany 一样等到超时后返回空
            await asyncio.sleep(timeout_ms / 1000)
            return {}
        self.broker.events.append(("poll", rec.topic, rec.partition, rec.offset))
        self.broker.last_delivered[(rec.topic, rec.partition)] = rec
        return {TopicPartition(rec.topic, rec.partition): [rec]}

    def pause(self, *partitions: Any) -> None:
        self.broker.events.append(("pause", partitions, time.monotonic()))
        self.broker.paused.update(partitions)

    def seek(self, partition: Any, offset: int) -> None:
        self.broker.events.append(("seek", partition, offset))
        # 真实 seek 会让该分区从 offset 重新拉取：把刚投递的那条放回队首
        last = self.broker.last_delivered.get((partition.topic, partition.partition))
        if last is not None and last.offset == offset:
            self.broker.records.appendleft(last)

    def resume(self, *partitions: Any) -> None:
        self.broker.events.append(("resume", partitions, time.monotonic()))
        self.broker.paused.difference_update(partitions)

    def assignment(self) -> set[Any]:
        return set(self.broker.assigned)

    def revoke_soon(self, *partitions: Any) -> None:
        """像 aiokafka 协调器一样，在独立任务里调用撤销回调；在 handler 线程里调用也安全。

        回调在事件循环空闲时开始，所以可能和 handler 同时跑；回调结束后分区才离开 assignment。
        """

        async def _revoke() -> None:
            await self.listener.on_partitions_revoked(set(partitions))
            self.broker.assigned.difference_update(partitions)

        future = asyncio.run_coroutine_threadsafe(_revoke(), self.loop)
        self.broker.rebalance_tasks.append(future)

    async def commit(self, offsets: Any = None) -> None:
        self.broker.events.append(("commit", offsets))
        if self.broker.commit_errors:
            raise self.broker.commit_errors.popleft()
        if self.broker.commit_error is not None:
            raise self.broker.commit_error
        # 与真实 aiokafka 一致：提交未分配给自己的分区直接报错
        unassigned = set(offsets or {}) - self.broker.assigned
        if unassigned:
            raise IllegalStateError(f"Partition {sorted(unassigned)[0]} is not assigned")

    async def stop(self) -> None:
        self.broker.events.append(("consumer.stop",))
        if self.broker.consumer_stop_error is not None:
            raise self.broker.consumer_stop_error


class FakeProducer:
    def __init__(self, broker: FakeBroker, **kwargs: Any) -> None:
        self.broker = broker
        self.kwargs = kwargs
        # 对应 aiokafka 的 producer._txn_manager（只用到 is_fatal_error）
        self._txn_manager = SimpleNamespace(is_fatal_error=lambda: broker.producer_fatal)
        broker.producer = self
        broker.producers.append(self)

    async def start(self) -> None:
        self.broker.events.append(("producer.start",))
        if self.broker.producer_start_error is not None:
            raise self.broker.producer_start_error

    async def send(
        self,
        topic: str,
        value: Optional[bytes] = None,
        key: Optional[bytes] = None,
        headers: Optional[list[tuple[str, bytes]]] = None,
    ) -> "asyncio.Future[None]":
        """像 aiokafka：交给 producer 就返回；送达结果（包括发送故障）落在返回的 future 上。"""
        self.broker.events.append(("send", topic))
        self.broker.sent.append(SentMessage(topic, value, key, list(headers or [])))
        error: Optional[Exception] = self.broker.send_error
        if self.broker.send_errors:
            error = self.broker.send_errors.popleft()
        delivery: asyncio.Future[None] = asyncio.get_running_loop().create_future()

        def _settle() -> None:
            if delivery.done():  # 等送达的一方超时放弃时会取消它
                return
            if error is not None:
                delivery.set_exception(error)
            else:
                delivery.set_result(None)

        asyncio.get_running_loop().call_later(self.broker.send_delay_s, _settle)
        return delivery

    async def send_and_wait(
        self,
        topic: str,
        value: Optional[bytes] = None,
        key: Optional[bytes] = None,
        headers: Optional[list[tuple[str, bytes]]] = None,
    ) -> None:
        delivery = await self.send(topic, value=value, key=key, headers=headers)
        await delivery

    def transaction(self) -> "FakeTransaction":
        return FakeTransaction(self.broker)

    async def send_offsets_to_transaction(self, offsets: Any, group_id: str) -> None:
        self.broker.events.append(("txn.offsets", offsets, group_id))

    async def abort_transaction(self) -> None:
        self.broker.events.append(("txn.abort_call",))
        # 真实 aiokafka 在没有进行中的事务时也会抛错
        raise RuntimeError("no transaction in progress")

    async def stop(self) -> None:
        self.broker.events.append(("producer.stop",))
        if self.broker.producer_stop_delays:
            await asyncio.sleep(self.broker.producer_stop_delays.popleft())
        if self.broker.producer_stop_error is not None:
            raise self.broker.producer_stop_error


class FakeTransaction:
    def __init__(self, broker: FakeBroker) -> None:
        self.broker = broker

    async def __aenter__(self) -> "FakeTransaction":
        self.broker.events.append(("txn.begin",))
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if exc_type is not None:
            self.broker.events.append(("txn.abort",))
            return
        self.broker.events.append(("txn.commit",))
        if self.broker.txn_commit_error is not None:
            raise self.broker.txn_commit_error


class RecordingHandler:
    def __init__(
        self,
        result: Any = HandleResult.ACK,
        error: Optional[Exception] = None,
        on_call: Optional[Callable[[Envelope], None]] = None,
    ) -> None:
        self.result = result
        self.error = error
        self.on_call = on_call
        self.envs: list[Envelope] = []

    def __call__(self, env: Envelope) -> Any:
        self.envs.append(env)
        if self.on_call is not None:
            self.on_call(env)
        if self.error is not None:
            raise self.error
        return self.result


class RecordingMiddleware:
    def __init__(self, name: str, calls: list[tuple[Any, ...]]) -> None:
        self.name = name
        self.calls = calls

    def before_handle(self, topic: str, partition: int, offset: int, env: Envelope) -> Envelope:
        self.calls.append((self.name, "before", topic, partition, offset, env))
        return Envelope(payload=(self.name, env.payload), key=env.key, headers=env.headers)

    def after_handle(
        self,
        topic: str,
        partition: int,
        offset: int,
        env: Envelope,
        result: HandleResult,
        exc: Optional[BaseException] = None,
    ) -> None:
        self.calls.append((self.name, "after", topic, partition, offset, env, result, exc))


class ExplodingMiddleware(RecordingMiddleware):
    def before_handle(self, topic: str, partition: int, offset: int, env: Envelope) -> Envelope:
        raise RuntimeError("middleware broke")


class FailingSerializer:
    def __init__(self, message: str = "bad json") -> None:
        self.message = message

    def dumps(self, obj: Any) -> bytes:
        raise AssertionError("consumer must not serialize")

    def loads(self, data: bytes) -> Any:
        raise ValueError(self.message)


def record(
    offset: int = 0,
    *,
    topic: str = "orders",
    partition: int = 0,
    value: Optional[bytes] = b'{"id": 1}',
    key: Optional[bytes] = b"k",
    headers: Optional[list[tuple[str, bytes]]] = None,
) -> FakeRecord:
    return FakeRecord(topic, partition, offset, value, key, headers)


def ack(env: Envelope) -> HandleResult:
    return HandleResult.ACK


def run_until_drained(consumer: AiokafkaConsumer, handler: Callable[[Envelope], Any]) -> None:
    """跑 start() 直到 fake getmany 脚本耗尽（_StopLoop 透出 start）。"""
    with pytest.raises(_StopLoop):
        consumer.start(handler)


def warnings_from(
    caplog: pytest.LogCaptureFixture, name: str = LOGGER_NAME
) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.name == name and r.levelno == logging.WARNING]


@pytest.fixture
def broker(monkeypatch: pytest.MonkeyPatch) -> FakeBroker:
    fake = FakeBroker()
    monkeypatch.setattr(aiokafka, "AIOKafkaConsumer", lambda **kw: FakeConsumer(fake, **kw))
    monkeypatch.setattr(aiokafka, "AIOKafkaProducer", lambda **kw: FakeProducer(fake, **kw))
    return fake


@pytest.fixture
def make_consumer(broker: FakeBroker) -> Iterator[Callable[..., AiokafkaConsumer]]:
    created: list[AiokafkaConsumer] = []

    def _make(
        *,
        cfg: Optional[KafkaConfig] = None,
        retry: Optional[RetryConfig] = None,
        serializer: Any = None,
        middlewares: Optional[list[Any]] = None,
        logger: Optional[logging.Logger] = None,
        subscribe: bool = True,
    ) -> AiokafkaConsumer:
        consumer = AiokafkaConsumer(
            cfg or KafkaConfig(),
            retry or RetryConfig(),
            serializer or JsonSerializer(),
            middlewares,
            logger,
        )
        if subscribe:
            consumer.subscribe(["orders"], "group-1")
        created.append(consumer)
        return consumer

    yield _make
    for consumer in created:
        if consumer._loop._thread.is_alive():
            consumer._loop.stop()


@pytest.fixture
def ssl_calls(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Any, ...]]:
    calls: list[tuple[Any, ...]] = []

    def _default_certs(self: ssl.SSLContext, purpose: Any = None) -> None:
        calls.append(("load_default_certs",))

    def _verify_locations(
        self: ssl.SSLContext, cafile: Any = None, capath: Any = None, cadata: Any = None
    ) -> None:
        calls.append(("load_verify_locations", cafile))
        if cafile == BAD_CA:
            raise OSError("no such file")

    def _cert_chain(
        self: ssl.SSLContext, certfile: Any, keyfile: Any = None, password: Any = None
    ) -> None:
        calls.append(("load_cert_chain", certfile, keyfile))

    monkeypatch.setattr(ssl.SSLContext, "load_default_certs", _default_certs)
    monkeypatch.setattr(ssl.SSLContext, "load_verify_locations", _verify_locations)
    monkeypatch.setattr(ssl.SSLContext, "load_cert_chain", _cert_chain)
    return calls


# ---------------------------------------------------------------------------
# 启停、退出与建连
# ---------------------------------------------------------------------------


def test_init_raises_import_error_without_aiokafka(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "aiokafka", None)

    with pytest.raises(ImportError, match="aiokafka is required for AiokafkaConsumer"):
        AiokafkaConsumer(KafkaConfig(), RetryConfig(), JsonSerializer())


def test_start_requires_subscribe(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    consumer = make_consumer(subscribe=False)

    with pytest.raises(RuntimeError, match=r"Call subscribe\(topics, group_id\) before start\(\)"):
        consumer.start(ack)

    assert broker.consumer is None
    assert not consumer._loop._thread.is_alive()


@pytest.mark.parametrize(("topics", "group_id"), [([], "group-1"), (["orders"], "")])
def test_start_rejects_empty_topics_or_group(
    broker: FakeBroker,
    make_consumer: Callable[..., AiokafkaConsumer],
    topics: list[str],
    group_id: str,
) -> None:
    consumer = make_consumer(subscribe=False)
    consumer.subscribe(topics, group_id)

    with pytest.raises(RuntimeError, match="Call subscribe"):
        consumer.start(ack)

    assert broker.consumer is None


def test_start_builds_clients_from_config(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    cfg = KafkaConfig(bootstrap_servers="kafka:9092", client_id="svc")
    cfg.consumer.enable_auto_commit = True  # 被忽略：始终手动提交
    cfg.consumer.auto_offset_reset = "earliest"
    cfg.consumer.max_poll_interval_ms = 123_000
    cfg.consumer.session_timeout_ms = 20_000
    cfg.consumer.fetch_min_bytes = 2
    cfg.consumer.fetch_max_bytes = 1_024
    cfg.producer.compression_type = "gzip"

    run_until_drained(make_consumer(cfg=cfg), ack)

    assert broker.consumer is not None and broker.producer is not None
    assert broker.consumer.kwargs == {
        "bootstrap_servers": "kafka:9092",
        "client_id": "svc",
        "group_id": "group-1",
        "enable_auto_commit": False,
        "auto_offset_reset": "earliest",
        "max_poll_interval_ms": 123_000,
        "rebalance_timeout_ms": 123_000,
        "session_timeout_ms": 20_000,
        "fetch_min_bytes": 2,
        "fetch_max_bytes": 1_024,
        "security_protocol": "PLAINTEXT",
        "ssl_context": None,
        "sasl_mechanism": None,
        "sasl_plain_username": None,
        "sasl_plain_password": None,
    }
    assert broker.producer.kwargs == {
        "bootstrap_servers": "kafka:9092",
        "client_id": "svc.consumer-producer",
        "acks": "all",
        "enable_idempotence": True,
        "compression_type": "gzip",
        "linger_ms": 5,
        "max_batch_size": 65_536,
        "request_timeout_ms": 120_000,
        "security_protocol": "PLAINTEXT",
        "ssl_context": None,
        "sasl_mechanism": None,
        "sasl_plain_username": None,
        "sasl_plain_password": None,
    }
    assert broker.event_names() == [
        "consumer.start",
        "producer.start",
        "subscribe",
        "consumer.stop",
        "producer.stop",
    ]
    assert broker.events[2] == ("subscribe", ["orders"])


def test_stop_inside_handler_ends_loop_after_that_record_and_flushes_offsets(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    consumer = make_consumer()

    def _request_stop(env: Envelope) -> None:
        consumer.stop()  # 在事件循环线程里调用：只置位，不等待自己

    handler = RecordingHandler(on_call=_request_stop)
    broker.feed(record(1), record(2))

    consumer.start(handler)

    assert len(handler.envs) == 1
    assert len(broker.records) == 1  # 第二条没被拉取
    assert broker.commits() == [{TopicPartition("orders", 0): 2}]
    assert broker.event_names()[-3:] == ["commit", "consumer.stop", "producer.stop"]


def test_stopped_before_start_never_polls(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    consumer = make_consumer()
    consumer.stop()  # 还没 start：只置位，立刻返回
    broker.feed(record(1))

    consumer.start(ack)

    assert broker.event_names() == [
        "consumer.start",
        "producer.start",
        "subscribe",
        "consumer.stop",
        "producer.stop",
    ]


def test_poll_error_propagates_after_stopping_clients(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    run_until_drained(make_consumer(), ack)

    assert broker.event_names()[-2:] == ["consumer.stop", "producer.stop"]


def test_client_stop_errors_are_swallowed(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    broker.consumer_stop_error = RuntimeError("consumer stop failed")
    broker.producer_stop_error = RuntimeError("producer stop failed")

    run_until_drained(make_consumer(), ack)

    assert broker.event_names()[-2:] == ["consumer.stop", "producer.stop"]


def test_consumer_start_failure_stops_the_consumer(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    broker.consumer_start_error = ConnectionError("broker down")

    with pytest.raises(ConnectionError, match="broker down"):
        make_consumer().start(ack)

    assert broker.producer is None
    assert broker.event_names() == ["consumer.start", "consumer.stop"]


def test_producer_start_failure_stops_both_clients(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    broker.producer_start_error = ConnectionError("producer down")

    with pytest.raises(ConnectionError, match="producer down"):
        make_consumer().start(ack)

    assert broker.event_names() == [
        "consumer.start",
        "producer.start",
        "consumer.stop",
        "producer.stop",
    ]


def test_subscribe_failure_stops_both_clients(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    broker.subscribe_error = TypeError("bad listener")

    with pytest.raises(TypeError, match="bad listener"):
        make_consumer().start(ack)

    assert broker.event_names() == [
        "consumer.start",
        "producer.start",
        "subscribe",
        "consumer.stop",
        "producer.stop",
    ]


def _start_in_thread(
    consumer: AiokafkaConsumer, handler: Callable[[Envelope], Any]
) -> tuple[threading.Thread, dict[str, Exception]]:
    outcome: dict[str, Exception] = {}

    def _run_start() -> None:
        try:
            consumer.start(handler)
        except Exception as exc:  # noqa: BLE001 - 记录给主线程断言
            outcome["error"] = exc

    starter = threading.Thread(target=_run_start, daemon=True)
    starter.start()
    return starter, outcome


def test_handler_runs_on_its_own_thread_while_the_event_loop_stays_responsive(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    consumer = make_consumer()
    in_handler, release = threading.Event(), threading.Event()
    handler_threads: list[threading.Thread] = []

    def _first_is_slow(env: Envelope) -> HandleResult:
        handler_threads.append(threading.current_thread())
        if len(handler_threads) == 1:
            in_handler.set()
            release.wait(5)
        return HandleResult.ACK

    broker.feed(record(1), record(2))
    starter, outcome = _start_in_thread(consumer, _first_is_slow)
    assert in_handler.wait(5)

    async def _ping() -> str:
        return "alive"

    # handler 还卡着，事件循环照样能跑别的协程：真实 aiokafka 的心跳就跑在这里
    assert consumer._loop.submit(_ping()).result(timeout=1) == "alive"
    release.set()
    starter.join(timeout=5)

    assert isinstance(outcome.get("error"), _StopLoop)
    # 两条都在同一个专用 handler 线程上跑，不在事件循环线程上
    assert len(set(handler_threads)) == 1
    assert handler_threads[0] is not consumer._loop._thread
    assert handler_threads[0].name.startswith("kafka-consumer-handler")
    assert handler_threads[0].daemon  # 卡死的 handler 不拦进程退出


def test_handler_sees_the_context_set_by_before_handle(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    request_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
        "request_id", default=None
    )
    seen_in_handler: list[Optional[str]] = []
    seen_after: list[Optional[str]] = []

    class _SetsContext:
        def before_handle(self, topic: str, partition: int, offset: int, env: Envelope) -> Envelope:
            request_id.set(f"req-{offset}")
            return env

        def after_handle(self, *args: Any) -> None:
            seen_after.append(request_id.get())

    def handler(env: Envelope) -> HandleResult:
        seen_in_handler.append(request_id.get())
        return HandleResult.ACK

    broker.feed(record(7))

    run_until_drained(make_consumer(middlewares=[_SetsContext()]), handler)

    # 中间件留在事件循环上，before/after 共用一个上下文；handler 在它的副本里跑
    assert seen_in_handler == ["req-7"]
    assert seen_after == ["req-7"]


def test_rebalance_timeout_follows_max_poll_interval(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    cfg = KafkaConfig()
    cfg.consumer.session_timeout_ms = 6_000
    cfg.consumer.max_poll_interval_ms = 77_000

    run_until_drained(make_consumer(cfg=cfg), ack)

    # 不传的话 aiokafka 用 session_timeout_ms（6s）：再均衡不等慢 handler，记录被别的成员拿走
    assert broker.consumer.kwargs["rebalance_timeout_ms"] == 77_000


def test_stuck_handler_thread_does_not_block_interpreter_exit() -> None:
    script = (
        "import threading, time\n"
        "from infrastructure.external.messaging.providers.aiokafka._loop import HandlerThread\n"
        "HandlerThread('kafka-consumer-handler').submit(threading.Event().wait)\n"
        "time.sleep(0.2)\n"
        "print('main thread finished', flush=True)\n"
    )
    started = time.monotonic()

    # 换成 ThreadPoolExecutor 的话，解释器退出时会 join 这个永远不返回的 worker
    done = subprocess.run(  # nosec B603 - fixed argv, no shell
        [sys.executable, "-c", script],
        cwd=BACKEND_DIR,
        env={**os.environ, "PYTHONPATH": str(BACKEND_DIR)},
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert done.returncode == 0, done.stderr
    assert "main thread finished" in done.stdout
    assert time.monotonic() - started < 10


def test_never_started_consumer_leaves_no_event_loop_behind() -> None:
    gc.collect()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        for _ in range(3):
            consumer = AiokafkaConsumer(KafkaConfig(), RetryConfig(), JsonSerializer())
            # 事件循环在 start() 时才创建，handler 线程第一次用到时才起
            assert consumer._loop._loop is None
            assert not consumer._handlers.started
        del consumer
        gc.collect()

    assert [str(w.message) for w in caught if "unclosed" in str(w.message).lower()] == []


def test_consumer_cannot_be_restarted(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    consumer = make_consumer()
    run_until_drained(consumer, ack)

    with pytest.raises(
        RuntimeError, match="AiokafkaConsumer cannot be restarted; create a new one"
    ):
        consumer.start(ack)


def test_stop_from_another_thread_flushes_offsets_returns_start_and_closes_clients(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    consumer = make_consumer()
    broker.idle_when_drained = True
    broker.feed(record(1), record(2))
    starter, outcome = _start_in_thread(consumer, ack)
    assert broker.idle_polled.wait(5)  # 两条都处理完，循环在空转

    stop_called = time.monotonic()
    consumer.stop()

    # stop() 等 start() 收尾完才返回；循环最多晚一个轮询周期（500ms）发现停止标志
    assert time.monotonic() - stop_called < 2
    starter.join(timeout=2)
    assert not starter.is_alive()
    assert outcome == {}
    assert broker.commits() == [{TopicPartition("orders", 0): 3}]
    assert broker.event_names()[-3:] == ["commit", "consumer.stop", "producer.stop"]
    assert not consumer._loop._thread.is_alive()


def test_stop_timeout_logs_and_lets_the_loop_finish_shutdown(
    broker: FakeBroker,
    make_consumer: Callable[..., AiokafkaConsumer],
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    caplog.set_level(logging.WARNING, logger=LOGGER_NAME)
    monkeypatch.setattr(consumer_module, "_STOP_TIMEOUT_S", 0.05)
    consumer = make_consumer()
    in_handler, release = threading.Event(), threading.Event()

    def _slow_handler(env: Envelope) -> HandleResult:
        in_handler.set()
        release.wait(5)  # 慢 handler 占住事件循环线程
        return HandleResult.ACK

    broker.feed(record(1))
    starter, outcome = _start_in_thread(consumer, _slow_handler)
    assert in_handler.wait(5)

    consumer.stop()

    [warning] = warnings_from(caplog)
    assert warning.getMessage() == "consumer did not stop in time; offsets may stay uncommitted"
    # 事件循环没被 stop() 冻结：handler 一结束，循环照常冲刷位点、关客户端，start() 返回
    release.set()
    starter.join(timeout=5)
    assert not starter.is_alive()
    assert outcome == {}
    assert broker.commits() == [{TopicPartition("orders", 0): 2}]
    assert broker.event_names()[-3:] == ["commit", "consumer.stop", "producer.stop"]


# ---------------------------------------------------------------------------
# 安全协议与 TLS
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("tls", "mechanism", "expected"),
    [
        (False, None, "PLAINTEXT"),
        (False, "PLAIN", "SASL_PLAINTEXT"),
        (True, None, "SSL"),
        (True, "SCRAM-SHA-512", "SASL_SSL"),
    ],
)
def test_security_protocol_matrix(
    broker: FakeBroker,
    make_consumer: Callable[..., AiokafkaConsumer],
    ssl_calls: list[tuple[Any, ...]],
    tls: bool,
    mechanism: Optional[str],
    expected: str,
) -> None:
    cfg = KafkaConfig(
        tls=TLSConfig(enable=tls),
        sasl=SASLConfig(mechanism=mechanism, username="svc-user", password=TEST_SASL_CRED),
    )

    run_until_drained(make_consumer(cfg=cfg), ack)

    for kwargs in (broker.consumer.kwargs, broker.producer.kwargs):
        assert kwargs["security_protocol"] == expected
        assert kwargs["sasl_mechanism"] == mechanism
        assert kwargs["sasl_plain_username"] == "svc-user"
        assert kwargs["sasl_plain_password"] == TEST_SASL_CRED
        assert isinstance(kwargs["ssl_context"], ssl.SSLContext) is tls
    assert broker.consumer.kwargs["ssl_context"] is broker.producer.kwargs["ssl_context"]


@pytest.mark.parametrize(
    ("tls", "mechanism"),
    [(False, None), (False, "PLAIN"), (True, None), (True, "SCRAM-SHA-512")],
)
def test_client_kwargs_are_accepted_by_real_aiokafka(
    broker: FakeBroker,
    make_consumer: Callable[..., AiokafkaConsumer],
    ssl_calls: list[tuple[Any, ...]],
    tls: bool,
    mechanism: Optional[str],
) -> None:
    cfg = KafkaConfig(
        tls=TLSConfig(enable=tls),
        sasl=SASLConfig(mechanism=mechanism, username="svc-user", password=TEST_SASL_CRED),
    )
    run_until_drained(make_consumer(cfg=cfg), ack)  # 默认 compression_type=zstd
    consumer_kwargs = broker.consumer.kwargs
    producer_kwargs = broker.producer.kwargs

    async def _construct_real_clients() -> None:
        # 真实构造会校验参数名、取值和压缩编解码器；不 start 就不连 broker
        real_consumer = REAL_AIOKAFKA_CONSUMER(**consumer_kwargs)
        real_producer = REAL_AIOKAFKA_PRODUCER(**producer_kwargs)
        await real_consumer.stop()
        await real_producer.stop()

    asyncio.run(_construct_real_clients())


def test_tls_verify_without_ca_loads_default_certs(
    broker: FakeBroker,
    make_consumer: Callable[..., AiokafkaConsumer],
    ssl_calls: list[tuple[Any, ...]],
) -> None:
    run_until_drained(make_consumer(cfg=KafkaConfig(tls=TLSConfig(enable=True))), ack)

    ctx = broker.consumer.kwargs["ssl_context"]
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname is True
    assert ssl_calls == [("load_default_certs",)]


def test_tls_custom_ca_is_loaded(
    broker: FakeBroker,
    make_consumer: Callable[..., AiokafkaConsumer],
    ssl_calls: list[tuple[Any, ...]],
) -> None:
    cfg = KafkaConfig(tls=TLSConfig(enable=True, ca_location="/etc/kafka/ca.pem"))

    run_until_drained(make_consumer(cfg=cfg), ack)

    assert ssl_calls == [("load_verify_locations", "/etc/kafka/ca.pem")]


def test_tls_ca_load_failure_falls_back_to_default_certs(
    broker: FakeBroker,
    make_consumer: Callable[..., AiokafkaConsumer],
    ssl_calls: list[tuple[Any, ...]],
) -> None:
    cfg = KafkaConfig(tls=TLSConfig(enable=True, ca_location=BAD_CA))

    run_until_drained(make_consumer(cfg=cfg), ack)

    assert ssl_calls == [("load_verify_locations", BAD_CA), ("load_default_certs",)]


def test_tls_without_verification_disables_hostname_and_cert_checks(
    broker: FakeBroker,
    make_consumer: Callable[..., AiokafkaConsumer],
    ssl_calls: list[tuple[Any, ...]],
) -> None:
    cfg = KafkaConfig(tls=TLSConfig(enable=True, verify=False, ca_location="/ignored.pem"))

    run_until_drained(make_consumer(cfg=cfg), ack)

    ctx = broker.consumer.kwargs["ssl_context"]
    assert ctx.check_hostname is False
    assert ctx.verify_mode == ssl.CERT_NONE
    assert ssl_calls == []


@pytest.mark.parametrize(
    ("certificate", "key", "expected_chain"),
    [
        (
            "/tls/client.pem",
            "/tls/client.key",
            [("load_cert_chain", "/tls/client.pem", "/tls/client.key")],
        ),
        ("/tls/client.pem", None, []),
        (None, "/tls/client.key", []),
    ],
)
def test_tls_client_cert_needs_both_cert_and_key(
    broker: FakeBroker,
    make_consumer: Callable[..., AiokafkaConsumer],
    ssl_calls: list[tuple[Any, ...]],
    certificate: Optional[str],
    key: Optional[str],
    expected_chain: list[tuple[Any, ...]],
) -> None:
    cfg = KafkaConfig(tls=TLSConfig(enable=True, certificate=certificate, key=key))

    run_until_drained(make_consumer(cfg=cfg), ack)

    assert [c for c in ssl_calls if c[0] == "load_cert_chain"] == expected_chain


# ---------------------------------------------------------------------------
# 正常处理路径与反序列化
# ---------------------------------------------------------------------------


def test_ack_passes_envelope_commits_and_tracks_next_offset(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    consumer = make_consumer()
    handler = RecordingHandler()
    broker.feed(record(5, headers=[("h", b"v"), ("h", b"last")]))

    run_until_drained(consumer, handler)

    [env] = handler.envs
    assert env.payload == {"id": 1}
    assert env.key == b"k"
    assert env.headers == {"h": b"last"}  # 重复 header 后者覆盖
    # 只提交已处理记录的下一位点；一条攒不满一批，循环退出时冲刷
    assert broker.commits() == [{TopicPartition("orders", 0): 6}]
    assert consumer._offsets.next_offsets == {("orders", 0): 6}
    assert consumer._offsets.uncommitted() == {}
    assert broker.sent == []


def test_none_value_skips_deserializer(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    handler = RecordingHandler()
    broker.feed(record(1, value=None))

    run_until_drained(make_consumer(serializer=FailingSerializer()), handler)

    assert handler.envs[0].payload is None
    assert handler.envs[0].headers == {}
    assert broker.commits() == [{TopicPartition("orders", 0): 2}]


def test_deserialization_failure_goes_to_dlq_without_handler_or_middlewares(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    calls: list[tuple[Any, ...]] = []
    consumer = make_consumer(
        serializer=FailingSerializer("bad json"), middlewares=[RecordingMiddleware("m", calls)]
    )
    handler = RecordingHandler()
    broker.feed(record(3, value=b"{oops", headers=[("h", b"v")]))

    run_until_drained(consumer, handler)

    assert handler.envs == []
    assert calls == []
    [sent] = broker.sent
    assert sent.topic == "orders.dlq"
    assert sent.value == b"{oops"
    assert sent.key == b"k"
    assert sent.headers == [
        ("h", b"v"),
        ("x-error-class", b"SerializationError"),
        ("x-error-msg", b"bad json"),
    ]
    # 转 DLQ 成功后立刻提交，不等批次
    assert broker.commits() == [{TopicPartition("orders", 0): 4}]
    assert consumer._offsets.next_offsets == {("orders", 0): 4}


def test_deserialization_error_message_is_truncated_to_2048_bytes(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    broker.feed(record(1))

    run_until_drained(make_consumer(serializer=FailingSerializer("x" * 5000)), ack)

    assert broker.sent[0].header_map["x-error-msg"] == b"x" * 2048


def test_deserialization_failure_on_retry_topic_uses_retry_topic_dlq_name(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    broker.feed(record(1, topic="orders.retry.5s"))

    run_until_drained(make_consumer(serializer=FailingSerializer()), ack)

    assert broker.sent[0].topic == "orders.retry.5s.dlq"


# ---------------------------------------------------------------------------
# 中间件
# ---------------------------------------------------------------------------


def test_middlewares_wrap_handler_in_order(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    calls: list[tuple[Any, ...]] = []
    consumer = make_consumer(
        middlewares=[RecordingMiddleware("a", calls), RecordingMiddleware("b", calls)]
    )
    handler = RecordingHandler()
    broker.feed(record(4, partition=1))

    run_until_drained(consumer, handler)

    final_env = handler.envs[0]
    assert final_env.payload == ("b", ("a", {"id": 1}))
    assert [c[:5] for c in calls] == [
        ("a", "before", "orders", 1, 4),
        ("b", "before", "orders", 1, 4),
        ("a", "after", "orders", 1, 4),
        ("b", "after", "orders", 1, 4),
    ]
    assert calls[1][5].payload == ("a", {"id": 1})
    for after in calls[2:]:
        assert after[5] is final_env
        assert after[6] is HandleResult.ACK
        assert after[7] is None


def test_after_handle_receives_result_and_error(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    calls: list[tuple[Any, ...]] = []
    error = RetryableError("try later")
    broker.feed(record(1))

    run_until_drained(
        make_consumer(middlewares=[RecordingMiddleware("a", calls)]), RecordingHandler(error=error)
    )

    after = calls[-1]
    assert after[1] == "after"
    assert after[6] is HandleResult.RETRY
    assert after[7] is error


def test_after_handle_runs_even_when_requeue_fails(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    calls: list[tuple[Any, ...]] = []
    broker.send_errors.append(RuntimeError("down"))
    broker.feed(record(1))

    run_until_drained(
        make_consumer(retry=FAST_RETRY, middlewares=[RecordingMiddleware("a", calls)]),
        RecordingHandler(error=ValueError("boom")),
    )

    # 重投失败那次也跑 after_handle；退避后重新消费、重投成功，再跑一轮
    assert [c[1] for c in calls] == ["before", "after", "before", "after"]


def test_before_handle_error_propagates_and_stops_clients(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    calls: list[tuple[Any, ...]] = []
    handler = RecordingHandler()
    broker.feed(record(1))

    with pytest.raises(RuntimeError, match="middleware broke"):
        make_consumer(middlewares=[ExplodingMiddleware("x", calls)]).start(handler)

    assert handler.envs == []
    assert calls == []
    assert broker.commits() == []
    assert broker.event_names()[-2:] == ["consumer.stop", "producer.stop"]


# ---------------------------------------------------------------------------
# 重试分层、DLQ、commit 与位点
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("error", "expected_topic", "expected_class"),
    [
        (RetryableError("transient"), "orders.retry.5s", b"RetryableError"),
        (NonRetryableError("permanent"), "orders.dlq", b"NonRetryableError"),
        (ValueError("unexpected"), "orders.retry.5s", b"ValueError"),
    ],
)
def test_handler_exceptions_map_to_retry_or_dlq(
    broker: FakeBroker,
    make_consumer: Callable[..., AiokafkaConsumer],
    error: Exception,
    expected_topic: str,
    expected_class: bytes,
) -> None:
    consumer = make_consumer()
    broker.feed(record(2))

    run_until_drained(consumer, RecordingHandler(error=error))

    [sent] = broker.sent
    assert sent.topic == expected_topic
    assert sent.value == b'{"id": 1}'
    assert sent.key == b"k"
    assert sent.header_map["x-error-class"] == expected_class
    assert sent.header_map["x-error-msg"] == str(error).encode()
    # 重投成功后立刻提交，避免进程崩溃时同一条被重投两次
    assert broker.commits() == [{TopicPartition("orders", 0): 3}]
    assert consumer._offsets.next_offsets == {("orders", 0): 3}


def test_retry_sets_headers_in_order(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    broker.feed(record(1, headers=[("h", b"v")]))
    before = now_ms()

    run_until_drained(make_consumer(), RecordingHandler(error=RetryableError("boom")))

    after = now_ms()
    [sent] = broker.sent
    assert [k for k, _ in sent.headers] == [
        "h",
        "x-original-topic",
        "x-attempts",
        "x-retry-not-before",
        "x-error-class",
        "x-error-msg",
    ]
    headers = sent.header_map
    assert headers["x-original-topic"] == b"orders"
    assert headers["x-attempts"] == b"1"
    assert before + 5_000 <= int(headers["x-retry-not-before"]) <= after + 5_000
    assert headers["x-error-msg"] == b"boom"


def test_retry_advances_to_next_layer_and_keeps_original_topic(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    broker.feed(
        record(
            1,
            topic="orders.retry.5s",
            headers=[("x-original-topic", b"orders"), ("x-attempts", b"1")],
        )
    )
    before = now_ms()

    run_until_drained(make_consumer(), RecordingHandler(error=RetryableError("again")))

    after = now_ms()
    [sent] = broker.sent
    assert sent.topic == "orders.retry.1m"
    headers = sent.header_map
    assert headers["x-original-topic"] == b"orders"
    assert headers["x-attempts"] == b"2"
    assert before + 60_000 <= int(headers["x-retry-not-before"]) <= after + 60_000


def test_retry_on_last_layer_goes_to_main_dlq_and_keeps_stale_not_before(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    broker.feed(
        record(
            1,
            topic="orders.retry.10m",
            headers=[
                ("x-original-topic", b"orders"),
                ("x-attempts", b"3"),
                ("x-retry-not-before", b"1"),
            ],
        )
    )

    run_until_drained(make_consumer(), RecordingHandler(error=RetryableError("exhausted")))

    [sent] = broker.sent
    assert sent.topic == "orders.dlq"
    headers = sent.header_map
    assert headers["x-attempts"] == b"4"
    assert headers["x-retry-not-before"] == b"1"  # 进 DLQ 时不刷新，原值透传


def test_returned_retry_without_exception_has_no_error_headers(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    broker.feed(record(1))

    run_until_drained(make_consumer(), RecordingHandler(result=HandleResult.RETRY))

    [sent] = broker.sent
    assert sent.topic == "orders.retry.5s"
    assert "x-error-class" not in sent.header_map
    assert "x-error-msg" not in sent.header_map
    assert broker.commits() == [{TopicPartition("orders", 0): 2}]


def test_returned_drop_without_exception_goes_to_dlq_without_error_headers(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    broker.feed(record(1, headers=[("h", b"v")]))

    run_until_drained(make_consumer(), RecordingHandler(result=HandleResult.DROP))

    [sent] = broker.sent
    assert sent.topic == "orders.dlq"
    assert sent.headers == [("h", b"v")]
    assert broker.commits() == [{TopicPartition("orders", 0): 2}]


def test_drop_on_retry_topic_uses_retry_topic_dlq_name(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    broker.feed(record(1, topic="orders.retry.5s"))

    run_until_drained(make_consumer(), RecordingHandler(error=NonRetryableError("bad")))

    # DROP 直接拼当前 topic，和重试耗尽时的 orders.dlq 不一致
    assert broker.sent[0].topic == "orders.retry.5s.dlq"


@pytest.mark.parametrize("result", [HandleResult.RETRY, HandleResult.DROP])
def test_handler_error_message_is_truncated_to_2048_bytes(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer], result: HandleResult
) -> None:
    error: Exception = (
        RetryableError("y" * 3000)
        if result is HandleResult.RETRY
        else NonRetryableError("y" * 3000)
    )
    broker.feed(record(1))

    run_until_drained(make_consumer(), RecordingHandler(error=error))

    assert broker.sent[0].header_map["x-error-msg"] == b"y" * 2048


@pytest.mark.parametrize(
    ("first_value", "handler_error", "expected_topic", "expected_message", "expected_handled"),
    [
        (b'{"id": 11}', RetryableError("x"), "orders.retry.fast", RETRY_SEND_FAILED, [11, 11, 12]),
        (b'{"id": 11}', NonRetryableError("x"), "orders.dlq", DLQ_SEND_FAILED, [11, 11, 12]),
        (b"{oops", None, "orders.dlq", DLQ_SEND_FAILED, [12]),  # 反序列化失败转 DLQ
    ],
)
def test_failed_requeue_send_is_consumed_again_and_committed_only_after_success(
    broker: FakeBroker,
    make_consumer: Callable[..., AiokafkaConsumer],
    caplog: pytest.LogCaptureFixture,
    first_value: bytes,
    handler_error: Optional[Exception],
    expected_topic: str,
    expected_message: str,
    expected_handled: list[int],
) -> None:
    caplog.set_level(logging.WARNING, logger=LOGGER_NAME)
    consumer = make_consumer(retry=FAST_RETRY)
    broker.send_errors.append(RuntimeError("broker unavailable"))
    broker.feed(
        record(11, partition=3, value=first_value), record(12, partition=3, value=b'{"id": 12}')
    )
    handled: list[int] = []

    def handler(env: Envelope) -> HandleResult:
        handled.append(env.payload["id"])
        if env.payload["id"] == 11 and handler_error is not None:
            raise handler_error
        return HandleResult.ACK

    run_until_drained(consumer, handler)

    tp3 = TopicPartition("orders", 3)
    # 第一次发送失败：不越过 11，同分区的 12 排在它后面；退避后 11 重新消费、发送成功
    assert handled == expected_handled
    assert [s.topic for s in broker.sent] == [expected_topic, expected_topic]
    names = broker.event_names()
    first_send, second_send = [i for i, name in enumerate(names) if name == "send"]
    pause_at, seek_at, resume_at = names.index("pause"), names.index("seek"), names.index("resume")
    assert first_send < pause_at < seek_at < resume_at < second_send
    assert broker.events[seek_at][1:] == (tp3, 11)
    # 退避取第一层重试延迟，但不少于一个轮询周期（500ms）：不是忙等
    assert broker.events[resume_at][2] - broker.events[pause_at][2] >= 0.45
    # 位点只在重投成功之后提交，12 的位点在它之后
    assert names.index("commit") > second_send
    assert broker.commits() == [{tp3: 12}, {tp3: 13}]
    [warning] = warnings_from(caplog)
    assert warning.getMessage() == expected_message
    assert {k: warning.__dict__[k] for k in ("topic", "partition", "offset", "error")} == {
        "topic": "orders",
        "partition": 3,
        "offset": 11,
        "error": "broker unavailable",
    }


def test_requeue_that_keeps_failing_holds_its_partition_while_others_commit(
    broker: FakeBroker,
    make_consumer: Callable[..., AiokafkaConsumer],
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING, logger=LOGGER_NAME)
    consumer = make_consumer(retry=FAST_RETRY)
    broker.send_error = RuntimeError("retry topic unavailable")
    tp0, tp1 = TopicPartition("orders", 0), TopicPartition("orders", 1)
    broker.feed(
        record(3, partition=0, value=b'{"id": 3}'),
        record(4, partition=0, value=b'{"id": 4}'),
        record(7, partition=1, value=b'{"id": 7}'),
        record(8, partition=1, value=b'{"id": 8}'),
    )
    handled: list[int] = []

    def handler(env: Envelope) -> HandleResult:
        handled.append(env.payload["id"])
        if env.payload["id"] == 3:
            raise RetryableError("later")
        return HandleResult.ACK

    starter, outcome = _start_in_thread(consumer, handler)
    deadline = time.monotonic() + 10
    while handled.count(3) < 3 and time.monotonic() < deadline:
        time.sleep(0.02)
    consumer.stop()
    starter.join(timeout=5)

    assert not starter.is_alive()
    assert outcome == {}
    # 3 每次退避后重试；同分区后面的 4 一直排在它后面，没被处理
    assert handled.count(3) >= 3
    assert 4 not in handled
    assert sorted(i for i in handled if i != 3) == [7, 8]
    # 分区 0 一个位点都没提交（不会越过失败的 3）；分区 1 照常提交
    assert all(tp0 not in offsets for offsets in broker.commits())
    assert {tp1: 9} in broker.commits()
    assert set(consumer._paused) == {tp0}
    # 每次暂停到恢复至少隔一个退避（500ms）：没有忙等
    pauses = [event[2] for event in broker.events if event[0] == "pause"]
    resumes = [event[2] for event in broker.events if event[0] == "resume"]
    assert all(resumed - paused >= 0.45 for paused, resumed in zip(pauses, resumes))
    warnings = warnings_from(caplog)
    assert len(warnings) == handled.count(3)
    assert {w.getMessage() for w in warnings} == {RETRY_SEND_FAILED}


def test_requeue_commit_failure_keeps_offset_pending_and_logs(
    broker: FakeBroker,
    make_consumer: Callable[..., AiokafkaConsumer],
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING, logger=LOGGER_NAME)
    consumer = make_consumer()
    broker.commit_error = RuntimeError("commit refused")
    broker.feed(record(1))

    run_until_drained(consumer, RecordingHandler(error=RetryableError("x")))

    # 重投已经成功、只是提交失败：位点留在待提交里，退出时再试一次（仍失败）
    assert [s.topic for s in broker.sent] == ["orders.retry.5s"]
    tp0 = TopicPartition("orders", 0)
    assert broker.commits() == [{tp0: 2}, {tp0: 2}]
    warnings = warnings_from(caplog)
    assert [w.getMessage() for w in warnings] == [COMMIT_FAILED, COMMIT_FAILED]
    assert {w.__dict__["error"] for w in warnings} == {"commit refused"}
    assert consumer._offsets.uncommitted() == {("orders", 0): 2}


def test_requeue_send_is_bounded_by_delivery_wait(
    broker: FakeBroker,
    make_consumer: Callable[..., AiokafkaConsumer],
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING, logger=LOGGER_NAME)
    broker.send_delay_s = 5.0
    consumer = make_consumer(cfg=KafkaConfig(producer=ProducerTuning(delivery_wait_s=0.05)))
    broker.feed(record(1))
    started = time.monotonic()

    # 处理完这条就停：否则它会按退避一直重试
    consumer.start(RecordingHandler(error=RetryableError("x"), on_call=lambda env: consumer.stop()))

    assert time.monotonic() - started < 2
    [warning] = warnings_from(caplog)
    assert warning.getMessage() == RETRY_SEND_FAILED
    assert warning.__dict__["error"] == ""  # TimeoutError 的 str 为空
    assert broker.commits() == []
    assert set(consumer._paused) == {TopicPartition("orders", 0)}


def test_acks_are_committed_in_batches_of_commit_every_n(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    cfg = KafkaConfig(consumer=ConsumerTuning(commit_every_n=2, commit_interval_ms=60_000))
    broker.feed(*(record(offset) for offset in range(5)))

    run_until_drained(make_consumer(cfg=cfg), ack)

    tp0 = TopicPartition("orders", 0)
    # 每 2 条提交一次；最后不满一批的那条在循环退出时冲刷
    assert broker.commits() == [{tp0: 2}, {tp0: 4}, {tp0: 5}]


def test_commit_interval_flushes_a_partial_batch(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    cfg = KafkaConfig(consumer=ConsumerTuning(commit_every_n=100, commit_interval_ms=200))
    broker.feed(record(0, partition=0), record(0, partition=1))
    handled: list[int] = []

    def _first_is_slow(env: Envelope) -> HandleResult:
        handled.append(len(handled))
        if len(handled) == 1:
            time.sleep(0.3)  # 第一条处理完时已超过 200ms 间隔
        return HandleResult.ACK

    run_until_drained(make_consumer(cfg=cfg), _first_is_slow)

    # 间隔到了，不满一批也提交；第二条紧接着处理，没到间隔，留到退出时冲刷
    assert broker.commits() == [
        {TopicPartition("orders", 0): 1},
        {TopicPartition("orders", 1): 1},
    ]


def test_batch_commit_failure_is_logged_and_retried_with_the_next_batch(
    broker: FakeBroker,
    make_consumer: Callable[..., AiokafkaConsumer],
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING, logger=LOGGER_NAME)
    calls: list[tuple[Any, ...]] = []
    cfg = KafkaConfig(consumer=ConsumerTuning(commit_every_n=1))
    consumer = make_consumer(cfg=cfg, middlewares=[RecordingMiddleware("a", calls)])
    broker.commit_errors.append(RuntimeError("commit refused"))
    broker.feed(record(1), record(2))

    run_until_drained(consumer, ack)

    # 提交失败不打断消费：第二条照常处理，它那一批把位点一起提交
    assert [c[1] for c in calls] == ["before", "after", "before", "after"]
    tp0 = TopicPartition("orders", 0)
    assert broker.commits() == [{tp0: 2}, {tp0: 3}]
    [warning] = warnings_from(caplog)
    assert warning.getMessage() == COMMIT_FAILED
    assert {k: warning.__dict__[k] for k in ("partitions", "error")} == {
        "partitions": 1,
        "error": "commit refused",
    }
    assert consumer._offsets.uncommitted() == {}


def test_partition_lost_during_a_requeue_is_left_out_of_later_commits(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    consumer = make_consumer()
    broker.send_delay_s = 0.05
    tp0, tp1 = TopicPartition("orders", 0), TopicPartition("orders", 1)
    broker.feed(
        record(4, partition=0, value=b'{"id": 4}'), record(9, partition=1, value=b'{"id": 9}')
    )

    def handler(env: Envelope) -> HandleResult:
        if env.payload["id"] == 4:
            # 分区 0 丢了、但没有成功的撤销冲刷（例如成员被踢出组）
            broker.assigned.discard(tp0)
            raise RetryableError("later")
        return HandleResult.ACK

    run_until_drained(consumer, handler)

    # 分区 0 的重投完成时它已不归本消费者，位点不再提交；
    # 否则 aiokafka 会拒绝之后每一次带上它的提交，分区 1 的位点也永远提交不上
    assert [s.topic for s in broker.sent] == ["orders.retry.5s"]
    assert broker.commits() == [{tp1: 10}]
    assert consumer._offsets.next_offsets == {("orders", 1): 10}


def test_unknown_handler_result_commits_nothing(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    calls: list[tuple[Any, ...]] = []
    consumer = make_consumer(middlewares=[RecordingMiddleware("a", calls)])
    broker.feed(record(1))

    run_until_drained(consumer, RecordingHandler(result=None))

    assert broker.commits() == []
    assert broker.sent == []
    assert consumer._offsets.next_offsets == {}
    assert calls[-1][6] is None


def test_custom_logger_receives_warnings(
    broker: FakeBroker,
    make_consumer: Callable[..., AiokafkaConsumer],
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING)
    custom = logging.getLogger("tests.custom.messaging")
    broker.send_error = RuntimeError("down")
    broker.feed(record(1))
    consumer = make_consumer(logger=custom)

    consumer.start(RecordingHandler(error=RetryableError("x"), on_call=lambda env: consumer.stop()))

    assert len(warnings_from(caplog, "tests.custom.messaging")) == 1
    assert warnings_from(caplog) == []


# ---------------------------------------------------------------------------
# 事务性重投（KAFKA__TRANSACTIONAL_ID）
# ---------------------------------------------------------------------------

TXN_ID = "vibejet-txn-1"


def _txn_events(broker: FakeBroker) -> list[tuple[Any, ...]]:
    return [e for e in broker.events if e[0] == "send" or e[0].startswith("txn.")]


def test_transactional_id_makes_requeue_transactional_and_reads_committed(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    run_until_drained(make_consumer(cfg=KafkaConfig(transactional_id=TXN_ID)), ack)

    assert broker.producer.kwargs["transactional_id"] == TXN_ID
    assert broker.consumer.kwargs["isolation_level"] == "read_committed"


def test_without_transactional_id_clients_are_not_transactional(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    broker.feed(record(1))

    run_until_drained(make_consumer(), RecordingHandler(error=RetryableError("x")))

    assert "transactional_id" not in broker.producer.kwargs
    assert "isolation_level" not in broker.consumer.kwargs
    assert not any(e[0].startswith("txn.") for e in broker.events)


def test_transactional_kwargs_are_accepted_by_real_aiokafka(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    run_until_drained(make_consumer(cfg=KafkaConfig(transactional_id=TXN_ID)), ack)
    consumer_kwargs = broker.consumer.kwargs
    producer_kwargs = broker.producer.kwargs

    async def _construct_real_clients() -> None:
        real_consumer = REAL_AIOKAFKA_CONSUMER(**consumer_kwargs)
        real_producer = REAL_AIOKAFKA_PRODUCER(**producer_kwargs)
        await real_consumer.stop()
        await real_producer.stop()

    asyncio.run(_construct_real_clients())


@pytest.mark.parametrize(
    ("handler_error", "serializer", "expected_topic"),
    [
        (RetryableError("later"), None, "orders.retry.5s"),
        (NonRetryableError("bad"), None, "orders.dlq"),
        (None, FailingSerializer(), "orders.dlq"),
    ],
)
def test_transactional_requeue_sends_and_commits_offset_in_one_transaction(
    broker: FakeBroker,
    make_consumer: Callable[..., AiokafkaConsumer],
    handler_error: Optional[Exception],
    serializer: Any,
    expected_topic: str,
) -> None:
    consumer = make_consumer(cfg=KafkaConfig(transactional_id=TXN_ID), serializer=serializer)
    broker.feed(record(4, partition=2))

    run_until_drained(consumer, RecordingHandler(error=handler_error))

    assert _txn_events(broker) == [
        ("txn.begin",),
        ("send", expected_topic),
        ("txn.offsets", {TopicPartition("orders", 2): 5}, "group-1"),
        ("txn.commit",),
    ]
    assert broker.commits() == []  # 位点随事务提交，不再单独 commit
    assert consumer._offsets.next_offsets == {("orders", 2): 5}
    assert consumer._offsets.uncommitted() == {}


@pytest.mark.parametrize(
    ("send_error", "commit_error", "expected_tail"),
    [
        # 被拒的记录让事务中止，而不是连同源位点一起提交（否则这条就丢了）
        (
            RuntimeError("broker down"),
            None,
            ["send", "txn.offsets", "txn.abort", "txn.abort_call"],
        ),
        (
            None,
            RuntimeError("commit refused"),
            ["send", "txn.offsets", "txn.commit", "txn.abort_call"],
        ),
    ],
)
def test_failed_transactional_requeue_aborts_and_leaves_offset_uncommitted(
    broker: FakeBroker,
    make_consumer: Callable[..., AiokafkaConsumer],
    caplog: pytest.LogCaptureFixture,
    send_error: Optional[Exception],
    commit_error: Optional[Exception],
    expected_tail: list[str],
) -> None:
    caplog.set_level(logging.WARNING, logger=LOGGER_NAME)
    broker.send_error = send_error
    broker.txn_commit_error = commit_error
    consumer = make_consumer(cfg=KafkaConfig(transactional_id=TXN_ID))
    broker.feed(record(4))

    consumer.start(RecordingHandler(error=RetryableError("x"), on_call=lambda env: consumer.stop()))

    assert [e[0] for e in _txn_events(broker)] == ["txn.begin", *expected_tail]
    [warning] = warnings_from(caplog)
    assert warning.getMessage() == RETRY_SEND_FAILED
    assert warning.__dict__["error"] == str(send_error or commit_error)
    assert consumer._offsets.next_offsets == {}
    assert broker.commits() == []
    # 中止的事务没提交位点：分区回退到这条并暂停，退避后重新消费
    tp0 = TopicPartition("orders", 0)
    assert broker.events[broker.event_names().index("seek")][1:] == (tp0, 4)
    assert set(consumer._paused) == {tp0}


def test_failed_transactional_requeue_is_retried_in_a_new_transaction(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    broker.send_errors.append(RuntimeError("broker down"))
    consumer = make_consumer(cfg=KafkaConfig(transactional_id=TXN_ID), retry=FAST_RETRY)
    handler = RecordingHandler(error=RetryableError("x"))
    broker.feed(record(4, partition=2))

    run_until_drained(consumer, handler)

    # 第一次事务中止、位点没提交；退避后重新消费，换新 producer 在新事务里重投并提交位点
    offsets = ("txn.offsets", {TopicPartition("orders", 2): 5}, "group-1")
    assert len(handler.envs) == 2
    assert _txn_events(broker) == [
        ("txn.begin",),
        ("send", "orders.retry.fast"),
        offsets,
        ("txn.abort",),
        ("txn.abort_call",),
        ("txn.begin",),
        ("send", "orders.retry.fast"),
        offsets,
        ("txn.commit",),
    ]
    assert len(broker.producers) == 2
    assert broker.commits() == []
    assert consumer._offsets.uncommitted() == {}


@pytest.mark.parametrize(
    ("send_error", "fatal_state"),
    [(ProducerFenced(), False), (RuntimeError("Invalid state transition"), True)],
)
def test_fenced_or_fatal_requeue_producer_stops_the_consumer_with_a_clear_error(
    broker: FakeBroker,
    make_consumer: Callable[..., AiokafkaConsumer],
    caplog: pytest.LogCaptureFixture,
    send_error: Exception,
    fatal_state: bool,
) -> None:
    caplog.set_level(logging.WARNING, logger=LOGGER_NAME)
    broker.send_error = send_error
    broker.producer_fatal = fatal_state
    consumer = make_consumer(cfg=KafkaConfig(transactional_id=TXN_ID), retry=FAST_RETRY)
    broker.feed(*(record(n, value=f'{{"id": {n}}}'.encode()) for n in (3, 4, 5)))
    handled: list[int] = []

    def handler(env: Envelope) -> HandleResult:
        handled.append(env.payload["id"])
        if env.payload["id"] == 4:
            raise RetryableError("later")
        return HandleResult.ACK

    with pytest.raises(RequeueProducerFatalError) as excinfo:
        consumer.start(handler)

    assert f"KAFKA__TRANSACTIONAL_ID={TXN_ID!r} must be unique per consumer instance" in str(
        excinfo.value
    )
    assert excinfo.value.__cause__ is send_error
    # 被隔离的 producer 不再写：只试了一次，没有退避重试、没换 producer，也没刷告警
    assert broker.event_names().count("send") == 1
    assert len(broker.producers) == 1
    assert warnings_from(caplog) == []
    # 已处理的 3 照常提交，4 没提交，5 没被拉取；客户端都关了
    assert handled == [3, 4]
    assert broker.commits() == [{TopicPartition("orders", 0): 4}]
    assert broker.event_names()[-3:] == ["commit", "consumer.stop", "producer.stop"]


def test_failed_requeue_gets_a_new_producer_before_the_retry(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    broker.send_errors.append(RuntimeError("OutOfOrderSequenceNumber"))
    broker.feed(record(1))

    run_until_drained(make_consumer(retry=FAST_RETRY), RecordingHandler(error=RetryableError("x")))

    # aiokafka 在一次被拒之后，这个分区的序号再也对不上：重试前换一个新 producer
    names = broker.event_names()
    first_send, second_send = [i for i, name in enumerate(names) if name == "send"]
    swap = [name for name in names[first_send:second_send] if name.startswith("producer.")]
    assert swap == ["producer.stop", "producer.start"]
    first, second = broker.producers
    assert first.kwargs == second.kwargs


def test_slow_stop_of_a_replaced_requeue_producer_is_logged_with_its_name(
    broker: FakeBroker,
    make_consumer: Callable[..., AiokafkaConsumer],
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING, logger=LOGGER_NAME)
    broker.send_errors.append(RuntimeError("rejected"))
    broker.producer_stop_delays.append(1.0)  # 被换下来的那个 producer 关得很慢
    cfg = KafkaConfig(producer=ProducerTuning(delivery_wait_s=0.1))
    broker.feed(record(1))

    run_until_drained(
        make_consumer(cfg=cfg, retry=FAST_RETRY), RecordingHandler(error=RetryableError("x"))
    )

    # 不再悄悄丢下：告警点名是哪个 producer；重试照常换新 producer 进行
    [stuck] = [w for w in warnings_from(caplog) if w.getMessage() == OLD_PRODUCER_STUCK]
    assert stuck.__dict__["producer"] == repr(broker.producers[0])
    assert stuck.__dict__["client_id"] == "app-messaging.consumer-producer"
    assert len(broker.producers) == 2


def test_acked_record_is_committed_while_the_next_requeue_on_its_partition_fails(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    cfg = KafkaConfig(consumer=ConsumerTuning(commit_every_n=1))
    consumer = make_consumer(cfg=cfg, retry=FAST_RETRY)
    broker.send_errors.append(RuntimeError("retry topic unavailable"))
    broker.feed(record(5, value=b'{"id": 5}'), record(6, value=b'{"id": 6}'))
    handled: list[int] = []

    def handler(env: Envelope) -> HandleResult:
        handled.append(env.payload["id"])
        if env.payload["id"] == 6:
            raise RetryableError("later")
        return HandleResult.ACK

    run_until_drained(consumer, handler)

    # 5 处理完就提交到 6；6 的重投失败时不越过它，退避后重投成功才提交到 7
    tp0 = TopicPartition("orders", 0)
    assert handled == [5, 6, 6]
    assert broker.commits() == [{tp0: 6}, {tp0: 7}]
    names = broker.event_names()
    first_commit, second_commit = [i for i, name in enumerate(names) if name == "commit"]
    first_send, second_send = [i for i, name in enumerate(names) if name == "send"]
    assert first_commit < first_send < second_send < second_commit


# ---------------------------------------------------------------------------
# 延迟重投（x-retry-not-before）
# ---------------------------------------------------------------------------


def _not_before(delay_ms: int) -> list[tuple[str, bytes]]:
    return [("x-retry-not-before", str(now_ms() + delay_ms).encode())]


def _mark_handled(broker: FakeBroker) -> Callable[[Envelope], None]:
    def _mark(env: Envelope) -> None:
        broker.events.append(("handled", env.payload["id"]))

    return _mark


def test_not_due_record_pauses_only_its_partition_while_others_flow(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    broker.feed(
        record(7, partition=0, value=b'{"id": 7}', headers=_not_before(300)),
        record(1, partition=1, value=b'{"id": 1}'),
        record(2, partition=1, value=b'{"id": 2}'),
    )
    handler = RecordingHandler(on_call=_mark_handled(broker))

    run_until_drained(make_consumer(), handler)

    tp0 = TopicPartition("orders", 0)
    names = broker.event_names()
    pause_at, seek_at, resume_at = names.index("pause"), names.index("seek"), names.index("resume")
    handled_at = [i for i, name in enumerate(names) if name == "handled"]
    assert [broker.events[i][1] for i in handled_at] == [1, 2, 7]
    # 分区 1 在分区 0 等待期间照常处理；记录 7 在 resume 之后才处理
    assert pause_at < seek_at < handled_at[0] < handled_at[1] < resume_at < handled_at[2]
    assert broker.events[pause_at][1] == (tp0,)
    assert broker.events[seek_at][1:] == (tp0, 7)
    assert broker.events[resume_at][1] == (tp0,)
    assert broker.events[resume_at][2] - broker.events[pause_at][2] >= 0.25
    # 循环按到期时间缩短轮询超时，而不是睡过整段延迟
    assert max(broker.poll_timeouts) <= 500
    assert min(broker.poll_timeouts) < 500


def test_far_future_retry_never_blocks_the_poll_loop(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    consumer = make_consumer()
    broker.feed(
        record(7, partition=0, value=b'{"id": 7}', headers=_not_before(600_000)),
        record(1, partition=1, value=b'{"id": 1}'),
        record(2, partition=1, value=b'{"id": 2}'),
    )

    def _stop_after_second(env: Envelope) -> None:
        if env.payload["id"] == 2:
            consumer.stop()

    handler = RecordingHandler(on_call=_stop_after_second)
    started = time.monotonic()

    consumer.start(handler)

    # 600s 的延迟不占用循环：其它分区立刻处理完，暂停的分区留到到期再恢复
    assert time.monotonic() - started < 3
    assert [env.payload["id"] for env in handler.envs] == [1, 2]
    assert "resume" not in broker.event_names()
    assert set(consumer._paused) == {TopicPartition("orders", 0)}
    assert max(broker.poll_timeouts) <= 500


def test_revoke_drops_pause_state_of_revoked_partitions(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    consumer = make_consumer()
    broker.feed(
        record(7, partition=0, value=b'{"id": 7}', headers=_not_before(600_000)),
        record(1, partition=1, value=b'{"id": 1}'),
    )

    def _stop(env: Envelope) -> None:
        consumer.stop()

    consumer.start(RecordingHandler(on_call=_stop))
    assert set(consumer._paused) == {TopicPartition("orders", 0)}

    asyncio.run(broker.consumer.listener.on_partitions_revoked({TopicPartition("orders", 0)}))

    assert consumer._paused == {}


@pytest.mark.parametrize("not_before", [b"1", b"not-a-number"])
def test_past_or_invalid_not_before_is_processed_immediately(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer], not_before: bytes
) -> None:
    handler = RecordingHandler()
    broker.feed(record(1, headers=[("x-retry-not-before", not_before)]))

    run_until_drained(make_consumer(), handler)

    assert "pause" not in broker.event_names()
    assert len(handler.envs) == 1


def test_pause_and_resume_arguments_are_accepted_by_real_aiokafka(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    delayed = record(7, headers=[("x-retry-not-before", str(now_ms() + 20).encode())])
    broker.feed(delayed)
    run_until_drained(make_consumer(), ack)
    names = broker.event_names()
    pause_args = broker.events[names.index("pause")][1]
    resume_args = broker.events[names.index("resume")][1]
    tp = TopicPartition("orders", 0)

    async def _replay_on_real_consumer() -> tuple[set[Any], set[Any]]:
        # 手动 assign 的真实 consumer 不连 broker 也能 pause/resume
        real = REAL_AIOKAFKA_CONSUMER(bootstrap_servers="127.0.0.1:9")
        try:
            real.assign([tp])
            real.pause(*pause_args)
            paused = set(real.paused())
            real.resume(*resume_args)
            return paused, set(real.paused())
        finally:
            await real.stop()

    paused, after_resume = asyncio.run(_replay_on_real_consumer())

    assert paused == {tp}
    assert after_resume == set()


# ---------------------------------------------------------------------------
# 再均衡监听
# ---------------------------------------------------------------------------


def test_listener_assigned_clears_tracked_offsets(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    consumer = make_consumer()
    broker.feed(record(5, partition=0), record(9, partition=1))
    run_until_drained(consumer, ack)
    assert consumer._offsets.next_offsets == {("orders", 0): 6, ("orders", 1): 10}

    broker.consumer.listener.on_partitions_assigned([TopicPartition("orders", 0)])

    assert consumer._offsets.next_offsets == {("orders", 1): 10}


def test_revoke_waits_for_the_record_in_flight_then_flushes_offsets(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    def _revoke(env: Envelope) -> None:
        broker.consumer.revoke_soon(TopicPartition("orders", 0), TopicPartition("orders", 1))
        time.sleep(0.1)  # 撤销回调此刻已在事件循环上开始，正等这条处理完

    handlers = iter([RecordingHandler(), RecordingHandler(on_call=_revoke)])
    broker.feed(record(5), record(6))

    run_until_drained(make_consumer(), lambda env: next(handlers)(env))

    # 撤销在 handler 还在跑时就开始了：等 6 处理完再冲刷（5、6 都处理完 → 7）；
    # 不等的话只能提交到 6，6 会被新的属主再处理一次。没处理过记录的分区 1 不提交
    assert broker.commits() == [{TopicPartition("orders", 0): 7}]


def test_revoke_without_processed_offsets_commits_nothing_for_it(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    def _revoke(env: Envelope) -> None:
        broker.consumer.revoke_soon(TopicPartition("orders", 4))

    broker.feed(record(1))

    run_until_drained(make_consumer(), RecordingHandler(on_call=_revoke))

    # 撤销的分区没有处理过的记录：不为它提交；分区 0 的位点在退出时冲刷
    assert broker.commits() == [{TopicPartition("orders", 0): 2}]


def test_revoke_commit_failure_is_logged_and_offsets_are_dropped(
    broker: FakeBroker,
    make_consumer: Callable[..., AiokafkaConsumer],
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING, logger=LOGGER_NAME)
    consumer = make_consumer()
    broker.commit_error = RuntimeError("revoke commit failed")

    def _revoke(env: Envelope) -> None:
        broker.consumer.revoke_soon(TopicPartition("orders", 0))

    handlers = iter([RecordingHandler(), RecordingHandler(on_call=_revoke)])
    broker.feed(record(1), record(2))

    run_until_drained(consumer, lambda env: next(handlers)(env))

    # 撤销时提交失败只记告警：分区已交给别的成员，它会从上次提交处重投这些记录
    assert broker.commits() == [{TopicPartition("orders", 0): 3}]
    [warning] = warnings_from(caplog)
    assert warning.getMessage() == COMMIT_FAILED
    assert warning.__dict__["error"] == "revoke commit failed"
    assert consumer._offsets.next_offsets == {}


def test_listener_is_accepted_by_real_aiokafka(
    broker: FakeBroker, make_consumer: Callable[..., AiokafkaConsumer]
) -> None:
    run_until_drained(make_consumer(), ack)
    listener = broker.consumer.listener

    assert isinstance(listener, ConsumerRebalanceListener)

    async def _subscribe_real() -> set[str]:
        real = REAL_AIOKAFKA_CONSUMER(bootstrap_servers="127.0.0.1:9", group_id="g")
        try:
            real.subscribe(["orders"], listener=listener)
            return set(real.subscription())
        finally:
            await real.stop()

    assert asyncio.run(_subscribe_real()) == {"orders"}
