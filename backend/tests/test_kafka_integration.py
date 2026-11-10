# input: 真实 Kafka broker（KAFKA_INTEGRATION_BOOTSTRAP=host:port，未设置则整体 skip）, AiokafkaPublisher/AiokafkaConsumer, aiokafka admin 与原生 producer/consumer 作旁路投递与校验
# output: aiokafka 驱动端到端集成测试：发布→消费并提交位点、RetryableError 经 retry topic 延迟重投、未到期记录只暂停所在分区（其它分区照常消费）、DLQ（反序列化失败 + NonRetryableError）、转投 DLQ 被 broker 拒收时不越过该记录（它前面已处理的照常提交，退避重试直到成功，其它分区照常消费）、事务里被拒的转投让事务中止（源位点不提交、DLQ 里什么都没有、这条会被重试）并在新事务里重试成功、发布者被拒一条后紧接着的发送就换新 producer 写同一分区、慢 handler 在再均衡中不被别的成员同时处理（rebalance_timeout = max_poll_interval）、handler 永不返回时进程照样能退出、handler 比会话超时还慢也不被踢出组、共用 transactional_id 被隔离的消费者 start() 报错退出、再均衡撤销时冲刷已处理位点、事务性重投、批量提交在消费者重启后不多重投、跨线程 stop()、publish_many 批量发送、幂等 producer 从 broker 拿到 producer id
# pos: 后端测试 - Kafka 驱动"真的能用"的证据（opt-in，需要 broker）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Opt-in integration tests against a real Kafka broker.

本地运行（单节点 KRaft broker）::

    docker run -d --name vj-kafka-it -p 9092:9092 apache/kafka:3.9.1
    cd backend && KAFKA_INTEGRATION_BOOTSTRAP=localhost:9092 \\
        uv run pytest tests/test_kafka_integration.py -v
    docker rm -f vj-kafka-it

每个测试用独立的 topic 前缀和 consumer group，可重复运行、互不干扰。
消费循环由 handler 里调用 consumer.stop() 结束（只置位），或从测试线程调用 stop()。
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess  # nosec B404 - runs the test's own interpreter
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Optional

import pytest

from infrastructure.external.messaging.base import Envelope, HandleResult
from infrastructure.external.messaging.config import (
    ConsumerTuning,
    KafkaConfig,
    RetryConfig,
    RetryLayer,
)
from infrastructure.external.messaging.envelope import now_ms
from infrastructure.external.messaging.exceptions import (
    NonRetryableError,
    PublishError,
    RequeueProducerFatalError,
    RetryableError,
)
from infrastructure.external.messaging.providers.aiokafka import consumer as consumer_module
from infrastructure.external.messaging.providers.aiokafka.consumer import AiokafkaConsumer
from infrastructure.external.messaging.providers.aiokafka.publisher import AiokafkaPublisher
from infrastructure.external.messaging.serializers.json import JsonSerializer

BOOTSTRAP = os.environ.get("KAFKA_INTEGRATION_BOOTSTRAP", "")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not BOOTSTRAP, reason="set KAFKA_INTEGRATION_BOOTSTRAP=host:port to run"),
]

aiokafka = pytest.importorskip("aiokafka")
aiokafka_admin = pytest.importorskip("aiokafka.admin")
aiokafka_config = pytest.importorskip("aiokafka.admin.config_resource")
aiokafka_errors = pytest.importorskip("aiokafka.errors")
TopicPartition = aiokafka.TopicPartition

RUN_TIMEOUT_S = 60.0
BACKEND_DIR = Path(__file__).resolve().parents[1]
# 由 handler 永远不返回的消费者组成的独立进程（改自评审的 stuck_exit 探针）
STUCK_EXIT_SCRIPT = """
import threading, time
from infrastructure.external.messaging.config import ConsumerTuning, KafkaConfig, RetryConfig
from infrastructure.external.messaging.providers.aiokafka import consumer as consumer_module
from infrastructure.external.messaging.providers.aiokafka.consumer import AiokafkaConsumer
from infrastructure.external.messaging.serializers.json import JsonSerializer

consumer_module._STOP_TIMEOUT_S = 2.0
cfg = KafkaConfig(
    bootstrap_servers="{bootstrap}",
    client_id="{group}",
    consumer=ConsumerTuning(auto_offset_reset="earliest"),
)
consumer = AiokafkaConsumer(cfg, RetryConfig(), JsonSerializer())
consumer.subscribe(["{topic}"], "{group}")
entered = threading.Event()


def handler(env):
    entered.set()
    threading.Event().wait()  # never returns


threading.Thread(target=consumer.start, args=(handler,), daemon=True).start()
if not entered.wait(60):
    raise SystemExit("handler never ran")
consumer.stop()
print("main finished at", time.time(), flush=True)
"""
RETRY_DELAY_MS = 2_000
RETRY = RetryConfig(layers=[RetryLayer(suffix="retry.2s", delay_ms=RETRY_DELAY_MS)])
# 只有退出/撤销时的冲刷会提交：批次大、间隔长
FLUSH_ONLY = ConsumerTuning(
    auto_offset_reset="earliest", commit_every_n=100, commit_interval_ms=600_000
)


@pytest.fixture
def prefix() -> str:
    return f"vj-it-{uuid.uuid4().hex[:8]}"


def _kafka_config(client_id: str, consumer: Optional[ConsumerTuning] = None) -> KafkaConfig:
    return KafkaConfig(
        bootstrap_servers=BOOTSTRAP,
        client_id=client_id,
        consumer=consumer or ConsumerTuning(auto_offset_reset="earliest"),
    )


def _create_topics(
    *topics: str, partitions: int = 1, configs: Optional[dict[str, str]] = None
) -> None:
    async def _create() -> None:
        admin = aiokafka_admin.AIOKafkaAdminClient(bootstrap_servers=BOOTSTRAP)
        await admin.start()
        try:
            await admin.create_topics(
                [
                    aiokafka_admin.NewTopic(
                        name=t,
                        num_partitions=partitions,
                        replication_factor=1,
                        topic_configs=configs or {},
                    )
                    for t in topics
                ]
            )
        finally:
            await admin.close()

    asyncio.run(_create())


def _publish(topic: str, *envelopes: Envelope) -> None:
    publisher = AiokafkaPublisher(_kafka_config("vj-it-publisher"), JsonSerializer())
    try:
        for env in envelopes:
            publisher.publish(topic, env)
    finally:
        publisher.close()


def _produce_raw(
    topic: str,
    partition: int,
    *values: bytes,
    headers: Optional[list[tuple[str, bytes]]] = None,
) -> None:
    """Write straight to one partition (the publisher has no partition argument)."""

    async def _send() -> None:
        producer = aiokafka.AIOKafkaProducer(bootstrap_servers=BOOTSTRAP)
        await producer.start()
        try:
            for value in values:
                await producer.send_and_wait(
                    topic, value=value, partition=partition, headers=headers
                )
        finally:
            await producer.stop()

    asyncio.run(_send())


def _start_in_thread(
    consumer: AiokafkaConsumer, handler: Callable[[Envelope], HandleResult]
) -> tuple[threading.Thread, list[Exception]]:
    errors: list[Exception] = []

    def _target() -> None:
        try:
            consumer.start(handler)
        except Exception as exc:  # noqa: BLE001 - 交给主线程断言
            errors.append(exc)

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    return thread, errors


def _wait_until_finished(
    consumer: AiokafkaConsumer, thread: threading.Thread, errors: list[Exception]
) -> None:
    thread.join(RUN_TIMEOUT_S)
    assert not thread.is_alive(), "consumer did not finish in time"
    if errors:
        raise errors[0]


def _consume(consumer: AiokafkaConsumer, handler: Callable[[Envelope], HandleResult]) -> None:
    thread, errors = _start_in_thread(consumer, handler)
    _wait_until_finished(consumer, thread, errors)


def _wait_for(condition: Callable[[], bool], timeout_s: float = RUN_TIMEOUT_S) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.1)
    return condition()


def _read_topic(
    topic: str, count: int, isolation_level: str = "read_uncommitted", wait_s: float = 20.0
) -> list[Any]:
    async def _read() -> list[Any]:
        reader = aiokafka.AIOKafkaConsumer(
            bootstrap_servers=BOOTSTRAP,
            auto_offset_reset="earliest",
            isolation_level=isolation_level,
        )
        await reader.start()
        try:
            tp = TopicPartition(topic, 0)
            reader.assign([tp])
            records: list[Any] = []
            deadline = time.monotonic() + wait_s
            while len(records) < count and time.monotonic() < deadline:
                batch = await reader.getmany(tp, timeout_ms=500)
                records.extend(batch.get(tp, []))
            return records
        finally:
            await reader.stop()

    return asyncio.run(_read())


def _committed(group: str, topic: str, partition: int = 0) -> Optional[int]:
    async def _fetch() -> Optional[int]:
        probe = aiokafka.AIOKafkaConsumer(
            bootstrap_servers=BOOTSTRAP, group_id=group, enable_auto_commit=False
        )
        await probe.start()
        try:
            committed: Optional[int] = await probe.committed(TopicPartition(topic, partition))
            return committed
        finally:
            await probe.stop()

    return asyncio.run(_fetch())


def _alter_topic_config(topic: str, configs: dict[str, str]) -> None:
    async def _alter() -> None:
        admin = aiokafka_admin.AIOKafkaAdminClient(bootstrap_servers=BOOTSTRAP)
        await admin.start()
        try:
            resource = aiokafka_config.ConfigResource(
                aiokafka_config.ConfigResourceType.TOPIC, topic, configs
            )
            await admin.alter_configs([resource])
        finally:
            await admin.close()

    asyncio.run(_alter())


def _end_offset(topic: str, partition: int = 0) -> int:
    async def _fetch() -> int:
        reader = aiokafka.AIOKafkaConsumer(bootstrap_servers=BOOTSTRAP)
        await reader.start()
        try:
            tp = TopicPartition(topic, partition)
            offsets = await reader.end_offsets([tp])
            return int(offsets[tp])
        finally:
            await reader.stop()

    return asyncio.run(_fetch())


class _WarningCollector(logging.Handler):
    """A consumer logger that records its warnings and signals the first one."""

    def __init__(self, name: str) -> None:
        super().__init__(level=logging.WARNING)
        self.messages: list[str] = []
        self.errors: list[str] = []
        self.first = threading.Event()
        self.logger = logging.getLogger(name)
        self.logger.addHandler(self)

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())
        self.errors.append(str(getattr(record, "error", "")))
        self.first.set()


def _new_consumer(
    prefix: str, topics: list[str], tuning: Optional[ConsumerTuning] = None
) -> AiokafkaConsumer:
    consumer = AiokafkaConsumer(_kafka_config(prefix, tuning), RETRY, JsonSerializer())
    consumer.subscribe(topics, f"{prefix}-group")
    return consumer


def _signal_assignment(monkeypatch: pytest.MonkeyPatch) -> threading.Event:
    """Set an event once the consumer has been assigned partitions."""
    assigned = threading.Event()
    callbacks = consumer_module._RebalanceCallbacks
    original = callbacks.on_partitions_assigned

    def _spy(self: Any, partitions: Any) -> None:
        original(self, partitions)
        if partitions:
            assigned.set()

    monkeypatch.setattr(callbacks, "on_partitions_assigned", _spy)
    return assigned


def test_publish_then_consume_commits_offsets(prefix: str) -> None:
    topic = f"{prefix}-orders"
    _create_topics(topic)
    _publish(
        topic,
        Envelope(payload={"n": 1}, key=b"k1", headers={"h": b"1"}),
        Envelope(payload={"n": 2}, key=b"k2"),
        Envelope(payload={"n": 3}, key=b"k3"),
    )
    consumer = _new_consumer(prefix, [topic])
    received: list[Envelope] = []

    def handler(env: Envelope) -> HandleResult:
        received.append(env)
        if len(received) == 3:
            consumer.stop()
        return HandleResult.ACK

    _consume(consumer, handler)

    assert [e.payload for e in received] == [{"n": 1}, {"n": 2}, {"n": 3}]
    assert [e.key for e in received] == [b"k1", b"k2", b"k3"]
    assert received[0].headers == {"h": b"1"}
    assert _committed(f"{prefix}-group", topic) == 3


def test_retryable_error_is_redelivered_from_retry_topic_after_delay(
    prefix: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    topic = f"{prefix}-orders"
    retry_topic = f"{topic}.retry.2s"
    _create_topics(topic, retry_topic, f"{topic}.dlq")
    deferrals: list[tuple[str, bool]] = []
    original_defer = AiokafkaConsumer._defer_if_not_due

    def _spy_defer(self: AiokafkaConsumer, msg: Any, headers: Any) -> bool:
        deferred: bool = original_defer(self, msg, headers)
        deferrals.append((msg.topic, deferred))
        return deferred

    monkeypatch.setattr(AiokafkaConsumer, "_defer_if_not_due", _spy_defer)
    _publish(topic, Envelope(payload={"order": 42}))
    consumer = _new_consumer(prefix, [topic, retry_topic])
    handled: list[tuple[float, Envelope]] = []

    def handler(env: Envelope) -> HandleResult:
        handled.append((time.monotonic(), env))
        if len(handled) == 1:
            raise RetryableError("try again")
        consumer.stop()
        return HandleResult.ACK

    _consume(consumer, handler)

    assert len(handled) == 2
    (first_at, _), (second_at, redelivered) = handled
    assert redelivered.payload == {"order": 42}
    assert redelivered.headers["x-original-topic"] == topic.encode()
    assert redelivered.headers["x-attempts"] == b"1"
    assert redelivered.headers["x-error-class"] == b"RetryableError"
    # 重投记录先被 pause/seek 挂起，到 x-retry-not-before 才 resume 处理
    assert (retry_topic, True) in deferrals
    assert second_at - first_at >= (RETRY_DELAY_MS / 1000) * 0.9
    assert _committed(f"{prefix}-group", topic) == 1
    assert _committed(f"{prefix}-group", retry_topic) == 1


def test_not_due_record_pauses_only_its_partition_while_another_keeps_flowing(
    prefix: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    topic = f"{prefix}-orders"
    delay_ms = 3_000
    _create_topics(topic, partitions=2)
    assigned = _signal_assignment(monkeypatch)
    deferred_at: list[float] = []
    original_defer = AiokafkaConsumer._defer_if_not_due

    def _spy_defer(self: AiokafkaConsumer, msg: Any, headers: Any) -> bool:
        deferred: bool = original_defer(self, msg, headers)
        if deferred:
            deferred_at.append(time.monotonic())
        return deferred

    monkeypatch.setattr(AiokafkaConsumer, "_defer_if_not_due", _spy_defer)
    consumer = _new_consumer(prefix, [topic])
    handled: list[tuple[float, Any]] = []

    def handler(env: Envelope) -> HandleResult:
        handled.append((time.monotonic(), env.payload))
        if env.payload == {"n": "delayed"}:
            consumer.stop()
        return HandleResult.ACK

    thread, errors = _start_in_thread(consumer, handler)
    assert assigned.wait(RUN_TIMEOUT_S), "consumer was not assigned partitions"
    due_at = time.monotonic() + delay_ms / 1000
    not_before = str(now_ms() + delay_ms).encode()
    _produce_raw(topic, 0, b'{"n": "delayed"}', headers=[("x-retry-not-before", not_before)])
    deadline = time.monotonic() + RUN_TIMEOUT_S
    while not deferred_at and time.monotonic() < deadline:
        time.sleep(0.05)
    assert deferred_at, "the not-yet-due record was not deferred"
    # 分区 0 暂停之后才往分区 1 写：这些记录必须在分区 0 等待期间被处理
    _produce_raw(topic, 1, b'{"n": 1}', b'{"n": 2}', b'{"n": 3}')
    _wait_until_finished(consumer, thread, errors)

    assert [payload for _, payload in handled] == [{"n": 1}, {"n": 2}, {"n": 3}, {"n": "delayed"}]
    flowing_done_at, delayed_at = handled[2][0], handled[3][0]
    assert deferred_at[0] < handled[0][0]
    # 没有整轮循环的 sleep：分区 1 远早于到期时间处理完；分区 0 到期后才处理
    assert flowing_done_at < due_at - 1.0
    assert delayed_at >= due_at - 0.05
    group = f"{prefix}-group"
    assert (_committed(group, topic, 0), _committed(group, topic, 1)) == (1, 3)


def test_undecodable_and_non_retryable_records_go_to_dead_letter_topic(prefix: str) -> None:
    topic = f"{prefix}-orders"
    dlq = f"{topic}.dlq"
    _create_topics(topic, dlq)
    _publish(
        topic,
        Envelope(payload=b"{not json"),
        Envelope(payload={"kind": "drop"}),
        Envelope(payload={"kind": "stop"}),
    )
    consumer = _new_consumer(prefix, [topic])

    def handler(env: Envelope) -> HandleResult:
        if env.payload == {"kind": "drop"}:
            raise NonRetryableError("cannot process")
        consumer.stop()
        return HandleResult.ACK

    _consume(consumer, handler)

    dead = _read_topic(dlq, 2)
    assert [r.value for r in dead] == [b"{not json", b'{"kind":"drop"}']
    undecodable, dropped = (dict(r.headers) for r in dead)
    assert undecodable["x-error-class"] == b"SerializationError"
    assert dropped["x-error-class"] == b"NonRetryableError"
    assert dropped["x-error-msg"] == b"cannot process"
    assert _committed(f"{prefix}-group", topic) == 3


def test_rebalance_listener_flushes_processed_offsets_on_revoke(
    prefix: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    topic = f"{prefix}-orders"
    group = f"{prefix}-group"
    _create_topics(topic)
    calls: list[tuple[str, set[Any]]] = []
    assigned = threading.Event()
    revoked = threading.Event()
    callbacks = consumer_module._RebalanceCallbacks
    original_assigned = callbacks.on_partitions_assigned
    original_revoked = callbacks.on_partitions_revoked

    def _spy_assigned(self: Any, partitions: Any) -> None:
        calls.append(("assigned", set(partitions)))
        original_assigned(self, partitions)
        assigned.set()

    async def _spy_revoked(self: Any, partitions: Any) -> None:
        calls.append(("revoked", set(partitions)))
        await original_revoked(self, partitions)
        if partitions:  # aiokafka also reports an empty revoke before the first join
            revoked.set()

    monkeypatch.setattr(callbacks, "on_partitions_assigned", _spy_assigned)
    monkeypatch.setattr(callbacks, "on_partitions_revoked", _spy_revoked)
    consumer = _new_consumer(prefix, [topic], FLUSH_ONLY)
    first_handled = threading.Event()

    def handler(env: Envelope) -> HandleResult:
        if env.payload == {"stop": True}:
            consumer.stop()
        else:
            first_handled.set()
        return HandleResult.ACK

    thread, errors = _start_in_thread(consumer, handler)
    assert assigned.wait(RUN_TIMEOUT_S), "listener was not told about the initial assignment"
    _publish(topic, Envelope(payload={"n": 1}))
    assert first_handled.wait(RUN_TIMEOUT_S)
    assert _committed(group, topic) is None  # 批没满、间隔没到：还没提交

    async def _second_member_joins_then_leaves() -> None:
        # 同组第二个成员加入会触发再均衡：我们的分区先被撤销
        other = aiokafka.AIOKafkaConsumer(
            bootstrap_servers=BOOTSTRAP, group_id=group, enable_auto_commit=False
        )
        other.subscribe([topic])
        await other.start()
        try:
            deadline = time.monotonic() + RUN_TIMEOUT_S
            while not revoked.is_set() and time.monotonic() < deadline:
                await other.getmany(timeout_ms=200)
        finally:
            await other.stop()

    asyncio.run(_second_member_joins_then_leaves())
    # 撤销回调在交出分区前把已处理的位点提交了
    assert _committed(group, topic) == 1
    _publish(topic, Envelope(payload={"stop": True}))
    _wait_until_finished(consumer, thread, errors)

    tp = TopicPartition(topic, 0)
    non_empty = [call for call in calls if call[1]]
    assert non_empty[0] == ("assigned", {tp})
    assert ("revoked", {tp}) in non_empty
    assert _committed(group, topic) == 2


def test_transactional_requeue_commits_dead_letter_and_offset_together(prefix: str) -> None:
    topic = f"{prefix}-orders"
    dlq = f"{topic}.dlq"
    group = f"{prefix}-group"
    _create_topics(topic, dlq)
    _publish(topic, Envelope(payload={"kind": "drop"}))
    cfg = _kafka_config(prefix)
    cfg.transactional_id = f"{prefix}-txn"
    consumer = AiokafkaConsumer(cfg, RETRY, JsonSerializer())
    consumer.subscribe([topic], group)

    def handler(env: Envelope) -> HandleResult:
        consumer.stop()  # 这条处理完就退出；它的位点只能由事务提交
        raise NonRetryableError("cannot process")

    _consume(consumer, handler)

    # read_committed 读得到 DLQ 记录 = 事务已提交；组位点 1 = 源位点在同一事务里提交
    dead = _read_topic(dlq, 1, isolation_level="read_committed")
    assert [r.value for r in dead] == [b'{"kind":"drop"}']
    assert dict(dead[0].headers)["x-error-class"] == b"NonRetryableError"
    assert _committed(group, topic) == 1


def test_batched_commits_survive_a_restart_without_extra_redelivery(
    prefix: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    topic = f"{prefix}-orders"
    group = f"{prefix}-group"
    _create_topics(topic)
    _publish(topic, *(Envelope(payload={"n": n}) for n in range(7)))
    tuning = ConsumerTuning(
        auto_offset_reset="earliest", commit_every_n=3, commit_interval_ms=600_000
    )
    first = _new_consumer(prefix, [topic], tuning)
    first_seen: list[int] = []

    async def _no_flush(keys: Any = None) -> None:
        return None

    def crash_after_last(env: Envelope) -> HandleResult:
        first_seen.append(env.payload["n"])
        if env.payload["n"] == 6:
            # 模拟进程在第 7 条之后崩溃：退出时不再冲刷未满一批的位点
            monkeypatch.setattr(first, "_commit_offsets", _no_flush)
            first.stop()
        return HandleResult.ACK

    _consume(first, crash_after_last)

    assert first_seen == list(range(7))
    # 两整批（每批 3 条）已提交；第 7 条还在未满的批里
    assert _committed(group, topic) == 6

    second = _new_consumer(prefix, [topic], tuning)
    second_seen: list[int] = []

    def take_one(env: Envelope) -> HandleResult:
        second_seen.append(env.payload["n"])
        second.stop()
        return HandleResult.ACK

    _consume(second, take_one)

    # 重启后从已提交位点继续：只重投没提交的第 7 条，前 6 条不再投递
    assert second_seen == [6]
    assert _committed(group, topic) == 7


def test_stop_from_another_thread_returns_start_flushes_and_closes_clients(prefix: str) -> None:
    topic = f"{prefix}-orders"
    group = f"{prefix}-group"
    _create_topics(topic)
    consumer = _new_consumer(prefix, [topic], FLUSH_ONLY)
    handled: list[int] = []
    both_handled = threading.Event()

    def handler(env: Envelope) -> HandleResult:
        handled.append(env.payload["n"])
        if len(handled) == 2:
            both_handled.set()
        return HandleResult.ACK

    thread, errors = _start_in_thread(consumer, handler)
    _publish(topic, Envelope(payload={"n": 1}), Envelope(payload={"n": 2}))
    assert both_handled.wait(RUN_TIMEOUT_S)
    assert _committed(group, topic) is None  # 批没满、间隔没到：还没提交

    stop_called = time.monotonic()
    consumer.stop()
    stop_took = time.monotonic() - stop_called

    thread.join(5)
    assert not thread.is_alive(), "start() did not return after stop()"
    assert errors == []
    assert stop_took < 5
    assert consumer._consumer._closed is True
    assert consumer._producer._closed is True
    assert _committed(group, topic) == 2  # stop() 冲刷了已处理的位点


def test_publish_many_sends_the_whole_batch_before_waiting_for_delivery(prefix: str) -> None:
    topic = f"{prefix}-orders"
    linger_s = 0.3
    _create_topics(topic)
    cfg = _kafka_config("vj-it-publisher")
    cfg.producer.linger_ms = int(linger_s * 1000)
    publisher = AiokafkaPublisher(cfg, JsonSerializer())
    try:
        started = time.monotonic()
        for n in range(5):
            publisher.publish(topic, Envelope(payload={"seq": n}))
        one_by_one_s = time.monotonic() - started

        started = time.monotonic()
        results = publisher.publish_many(topic, [Envelope(payload={"batch": n}) for n in range(20)])
        batched_s = time.monotonic() - started
    finally:
        publisher.close()

    # aiokafka 的 sender 每发完一轮就等满 linger 再发下一轮：逐条等送达，每条最多多等一轮。
    # publish_many 先把 20 条全部入队再一起等，只占一轮；逐条等的实现要约 20 轮
    per_record_s = one_by_one_s / 5
    assert per_record_s >= linger_s / 3  # linger 确实拖慢了逐条发送，下面的比较才有意义
    assert batched_s < one_by_one_s
    assert batched_s < 5 * per_record_s
    assert [(r.partition, r.offset) for r in results] == [(0, n) for n in range(5, 25)]
    records = _read_topic(topic, 25)
    assert [json.loads(r.value) for r in records[5:]] == [{"batch": n} for n in range(20)]


def test_idempotent_producer_gets_a_producer_id_from_the_broker(prefix: str) -> None:
    topic = f"{prefix}-orders"
    _create_topics(topic)
    cfg = _kafka_config("vj-it-idempotent")
    assert (cfg.producer.enable_idempotence, cfg.producer.acks) == (True, "all")  # 默认值
    publisher = AiokafkaPublisher(cfg, JsonSerializer())
    try:
        result = publisher.publish(topic, Envelope(payload={"n": 1}))
        txn_manager = publisher._slot.current._txn_manager
    finally:
        publisher.close()

    # 只有开启幂等时 aiokafka 才建 txn_manager；producer id 来自 broker 的 InitProducerId
    assert txn_manager is not None
    assert txn_manager.producer_id >= 0
    assert result.offset == 0
    assert [r.value for r in _read_topic(topic, 1)] == [b'{"n":1}']


def test_failed_dead_letter_send_holds_the_record_but_commits_the_ones_before_it(
    prefix: str,
) -> None:
    topic = f"{prefix}-orders"
    dlq = f"{topic}.dlq"
    group = f"{prefix}-group"
    _create_topics(topic, partitions=2)
    # DLQ 先只收 1KB 以内的记录：下面这条 2KB 的不可解码记录转投 DLQ 必然被 broker 拒收
    _create_topics(dlq, configs={"max.message.bytes": "1024"})
    undecodable = b"\xff" + os.urandom(2048)  # 不是 UTF-8，解不成 JSON；随机字节压缩不小
    _produce_raw(topic, 0, b'{"n": "before"}', undecodable, b'{"n": "after"}')
    warnings = _WarningCollector(f"vj-it.{prefix}")
    # 每 200ms 提交一次：卡住期间，它前面已处理的记录也要照常提交出去
    tuning = ConsumerTuning(
        auto_offset_reset="earliest", commit_every_n=100, commit_interval_ms=200
    )
    consumer = AiokafkaConsumer(
        _kafka_config(prefix, tuning), RETRY, JsonSerializer(), logger=warnings.logger
    )
    consumer.subscribe([topic], group)
    handled: list[Any] = []
    other_partition_done = threading.Event()

    def handler(env: Envelope) -> HandleResult:
        handled.append(env.payload)
        if env.payload == {"n": 2}:
            other_partition_done.set()
        if env.payload == {"n": "after"}:
            consumer.stop()
        return HandleResult.ACK

    thread, errors = _start_in_thread(consumer, handler)
    assert warnings.first.wait(RUN_TIMEOUT_S), "the dead-letter send did not fail"
    # 卡在转投失败的记录上时，它前面已处理的 before 照常提交（到 1），但提交不会越过它
    assert _wait_for(lambda: _committed(group, topic, 0) == 1), "the acked record was not committed"
    # 分区 0 卡住期间，分区 1 照常消费
    _produce_raw(topic, 1, b'{"n": 1}', b'{"n": 2}')
    assert other_partition_done.wait(RUN_TIMEOUT_S)
    assert {"n": "after"} not in handled  # 同分区后面的记录没有越过它
    assert _committed(group, topic, 0) == 1
    _alter_topic_config(dlq, {"max.message.bytes": "1048588"})
    _wait_until_finished(consumer, thread, errors)

    # 放开限制后，退避重试把这条转投成功；同分区后面的记录这才被处理
    assert handled == [{"n": "before"}, {"n": 1}, {"n": 2}, {"n": "after"}]
    assert _end_offset(dlq) == 1  # 只转投成功了一次
    [dead] = _read_topic(dlq, 1)
    assert dead.value == undecodable
    assert dict(dead.headers)["x-error-class"] == b"SerializationError"
    assert set(warnings.messages) == {"dlq send failed, message will be redelivered"}
    assert all("MessageSizeTooLarge" in error for error in warnings.errors)
    assert (_committed(group, topic, 0), _committed(group, topic, 1)) == (3, 2)


def test_rejected_transactional_requeue_aborts_and_is_retried_in_a_new_transaction(
    prefix: str,
) -> None:
    topic = f"{prefix}-orders"
    dlq = f"{topic}.dlq"
    group = f"{prefix}-group"
    _create_topics(topic)
    _create_topics(dlq, configs={"max.message.bytes": "1024"})  # 先拒收这条 2KB 的记录
    undecodable = b"\xff" + os.urandom(2048)
    _produce_raw(topic, 0, undecodable, b'{"n": "after"}')
    warnings = _WarningCollector(f"vj-it.{prefix}")
    cfg = _kafka_config(prefix)
    cfg.transactional_id = f"{prefix}-txn"
    consumer = AiokafkaConsumer(cfg, RETRY, JsonSerializer(), logger=warnings.logger)
    consumer.subscribe([topic], group)
    handled: list[Any] = []

    def handler(env: Envelope) -> HandleResult:
        handled.append(env.payload)
        consumer.stop()
        return HandleResult.ACK

    thread, errors = _start_in_thread(consumer, handler)
    assert warnings.first.wait(RUN_TIMEOUT_S), "the transactional dead-letter send did not fail"
    # 记录被拒，事务中止：源位点没跟着提交（这条不会丢），DLQ 里也没有已提交的记录
    assert _committed(group, topic) is None
    assert _read_topic(dlq, 1, isolation_level="read_committed", wait_s=1) == []
    _alter_topic_config(dlq, {"max.message.bytes": "1048588"})
    _wait_until_finished(consumer, thread, errors)

    # 退避后换了新 producer（新 epoch，序号从零开始），在新事务里转投成功、源位点随事务提交
    dead = _read_topic(dlq, 2, isolation_level="read_committed", wait_s=3)
    assert [r.value for r in dead] == [undecodable]
    assert dict(dead[0].headers)["x-error-class"] == b"SerializationError"
    assert handled == [{"n": "after"}]
    assert set(warnings.messages) == {"dlq send failed, message will be redelivered"}
    assert all("MessageSizeTooLarge" in error for error in warnings.errors)
    assert _committed(group, topic) == 2


def test_slow_handler_longer_than_the_session_timeout_keeps_its_membership(
    prefix: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    topic = f"{prefix}-orders"
    group = f"{prefix}-group"
    _create_topics(topic)
    revoked_while_running: list[set[Any]] = []
    callbacks = consumer_module._RebalanceCallbacks
    original_revoked = callbacks.on_partitions_revoked

    async def _spy_revoked(self: Any, partitions: Any) -> None:
        if partitions and not self._parent._stopped:
            revoked_while_running.append(set(partitions))
        await original_revoked(self, partitions)

    monkeypatch.setattr(callbacks, "on_partitions_revoked", _spy_revoked)
    # 6s 是 broker 默认允许的最小会话超时；max_poll_interval 远大于 handler 用时
    tuning = ConsumerTuning(
        auto_offset_reset="earliest",
        session_timeout_ms=6_000,
        max_poll_interval_ms=60_000,
        commit_every_n=100,
        commit_interval_ms=600_000,
    )
    _publish(topic, Envelope(payload={"n": 1}), Envelope(payload={"n": 2}))
    consumer = _new_consumer(prefix, [topic], tuning)
    handled: list[int] = []

    def handler(env: Envelope) -> HandleResult:
        handled.append(env.payload["n"])
        if env.payload["n"] == 1:
            time.sleep(8.0)  # 比会话超时长：心跳必须在 handler 跑的时候照常发出去
        else:
            consumer.stop()
        return HandleResult.ACK

    _consume(consumer, handler)

    # 没被踢出组：没有撤销；也没有重复处理（被踢的话，没提交的 1 会再来一次）
    assert handled == [1, 2]
    assert revoked_while_running == []
    assert _committed(group, topic) == 2


def test_fenced_transactional_consumer_stops_with_a_clear_error(
    prefix: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    txn_id = f"{prefix}-shared-txn"
    topic_a, topic_b = f"{prefix}-a", f"{prefix}-b"
    _create_topics(topic_a, f"{topic_a}.dlq", topic_b)
    assigned: list[Any] = []
    callbacks = consumer_module._RebalanceCallbacks
    original_assigned = callbacks.on_partitions_assigned

    def _spy_assigned(self: Any, partitions: Any) -> None:
        original_assigned(self, partitions)
        if partitions:
            assigned.append(self._parent)

    monkeypatch.setattr(callbacks, "on_partitions_assigned", _spy_assigned)

    def _transactional(name: str, topic: str) -> tuple[AiokafkaConsumer, _WarningCollector]:
        collector = _WarningCollector(f"vj-it.{prefix}.{name}")
        cfg = _kafka_config(f"{prefix}-{name}")
        cfg.transactional_id = txn_id  # 配置错误：两个实例共用一个 transactional_id
        consumer = AiokafkaConsumer(cfg, RETRY, JsonSerializer(), logger=collector.logger)
        consumer.subscribe([topic], f"{prefix}-{name}-group")
        return consumer, collector

    first, first_warnings = _transactional("first", topic_a)
    second, _ = _transactional("second", topic_b)
    handled: list[Any] = []

    def drop(env: Envelope) -> HandleResult:
        handled.append(env.payload)
        raise NonRetryableError("cannot process")

    first_thread, first_errors = _start_in_thread(first, drop)
    assert _wait_for(lambda: first in assigned)
    second_thread, second_errors = _start_in_thread(second, lambda env: HandleResult.ACK)
    # 第二个实例拿到 producer id 时，同一 transactional_id 的第一个实例就被隔离了
    assert _wait_for(lambda: second in assigned and second._producer._txn_manager.has_pid())
    _publish(topic_a, Envelope(payload={"n": 1}))

    first_thread.join(RUN_TIMEOUT_S)
    assert not first_thread.is_alive(), "the fenced consumer kept running"
    [error] = first_errors
    assert isinstance(error, RequeueProducerFatalError)
    assert f"KAFKA__TRANSACTIONAL_ID={txn_id!r} must be unique per consumer instance" in str(error)
    # 只处理了一次，没有退避重试、没有告警刷屏；客户端都关了；位点没提交，重启后这条会再处理
    assert handled == [{"n": 1}]
    assert first_warnings.messages == []
    assert first._consumer._closed and first._producer._closed
    assert _committed(f"{prefix}-first-group", topic_a) is None

    second.stop()
    second_thread.join(RUN_TIMEOUT_S)
    assert not second_thread.is_alive()
    assert second_errors == []


def test_rejected_record_in_a_transaction_commits_nothing_and_is_retried(prefix: str) -> None:
    topic = f"{prefix}-orders"
    dlq = f"{topic}.dlq"
    group = f"{prefix}-group"
    _create_topics(topic)
    _create_topics(dlq, configs={"max.message.bytes": "1024"})  # 一直拒收下面这条
    # 合法 JSON，但随机十六进制压缩后仍远超 1KB
    big = json.dumps({"blob": os.urandom(2048).hex()}).encode()
    _produce_raw(topic, 0, big)
    warnings = _WarningCollector(f"vj-it.{prefix}")
    cfg = _kafka_config(prefix)
    cfg.transactional_id = f"{prefix}-txn"
    consumer = AiokafkaConsumer(cfg, RETRY, JsonSerializer(), logger=warnings.logger)
    consumer.subscribe([topic], group)
    attempts: list[float] = []

    def drop(env: Envelope) -> HandleResult:
        attempts.append(time.monotonic())
        raise NonRetryableError("cannot process")

    thread, errors = _start_in_thread(consumer, drop)
    # 每次转投 DLQ 都被拒：退避后这条被重新消费、handler 再被调用（没有被跳过）
    assert _wait_for(lambda: len(attempts) >= 2), "the rejected record was not retried"
    consumer.stop()
    _wait_until_finished(consumer, thread, errors)

    # 被拒的事务没有提交：源位点没提交，DLQ 里不论已提交还是未提交都没有记录
    assert _committed(group, topic) is None
    assert _read_topic(dlq, 1, wait_s=1) == []
    assert _read_topic(dlq, 1, isolation_level="read_committed", wait_s=1) == []
    assert len(warnings.messages) >= 2
    assert set(warnings.messages) == {"dlq send failed, message will be redelivered"}
    assert all("MessageSizeTooLarge" in error for error in warnings.errors)
    assert attempts[1] - attempts[0] >= (RETRY_DELAY_MS / 1000) * 0.9


def test_publisher_rebuilds_its_producer_after_a_rejected_record(prefix: str) -> None:
    topic = f"{prefix}-capped"
    _create_topics(topic, configs={"max.message.bytes": "1024"})
    warnings = _WarningCollector(f"vj-it.{prefix}")
    publisher = AiokafkaPublisher(
        _kafka_config("vj-it-publisher"), JsonSerializer(), logger=warnings.logger
    )
    try:
        first = publisher._slot.current
        # 分区上先有这个 producer 的序号
        publisher.publish(topic, Envelope(payload={"n": "before"}))
        with pytest.raises(PublishError) as rejected:
            publisher.publish(topic, Envelope(payload=b"\xff" + os.urandom(2048)))
        # 被拒后 producer 立即标记失效：紧接着的这一条就换新 producer 发出，
        # 不会再撞上 aiokafka 0.13 对不上的序号（OutOfOrderSequenceNumber）
        result = publisher.publish(topic, Envelope(payload={"n": "after"}))
        rebuilt = publisher._slot.current
    finally:
        publisher.close()

    assert isinstance(rejected.value.__cause__, aiokafka_errors.MessageSizeTooLargeError)
    assert rebuilt is not first
    assert warnings.messages == [
        "producer rebuilt after the broker rejected a batch; later sends use it"
    ]
    # 同一个 publisher 实例紧接着往同一分区写成功
    assert (result.partition, result.offset) == (0, 1)
    records = _read_topic(topic, 2)
    assert [json.loads(r.value) for r in records] == [{"n": "before"}, {"n": "after"}]


def test_slow_handler_keeps_its_record_through_a_rebalance(prefix: str) -> None:
    topic = f"{prefix}-orders"
    group = f"{prefix}-group"
    _create_topics(topic)
    _publish(topic, Envelope(payload={"n": 0}))
    # 会话 6s，max_poll_interval 60s；只有撤销冲刷和 stop 会提交
    tuning = ConsumerTuning(
        auto_offset_reset="earliest",
        session_timeout_ms=6_000,
        max_poll_interval_ms=60_000,
        commit_every_n=100,
        commit_interval_ms=600_000,
    )
    consumer = _new_consumer(prefix, [topic], tuning)
    timeline: list[str] = []
    started, finished = threading.Event(), threading.Event()

    def slow(env: Envelope) -> HandleResult:
        timeline.append("A start")
        started.set()
        time.sleep(10.0)  # 比会话超时长；第二个成员在这期间加入组
        timeline.append("A done")
        finished.set()
        return HandleResult.ACK

    thread, errors = _start_in_thread(consumer, slow)
    assert started.wait(RUN_TIMEOUT_S)

    async def _second_member() -> None:
        other = aiokafka.AIOKafkaConsumer(
            bootstrap_servers=BOOTSTRAP,
            group_id=group,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
        )
        other.subscribe([topic])
        await other.start()
        try:
            deadline = time.monotonic() + RUN_TIMEOUT_S
            settled_at: Optional[float] = None
            while time.monotonic() < deadline and (
                settled_at is None or time.monotonic() < settled_at
            ):
                for records in (await other.getmany(timeout_ms=500)).values():
                    timeline.extend(f"B got offset {r.offset}" for r in records)
                if finished.is_set() and settled_at is None:
                    settled_at = time.monotonic() + 5  # 再均衡完成后再看一会
        finally:
            await other.stop()

    asyncio.run(_second_member())
    committed = _committed(group, topic)
    consumer.stop()
    _wait_until_finished(consumer, thread, errors)

    # 再均衡等 A 处理完（rebalance_timeout = max_poll_interval）：A 在撤销时提交了它，
    # B 从 1 开始，拿不到 0；没有两个成员同时处理同一条
    assert timeline == ["A start", "A done"]
    assert committed == 1


def test_never_returning_handler_does_not_block_process_exit(prefix: str, tmp_path: Path) -> None:
    topic = f"{prefix}-orders"
    _create_topics(topic)
    _publish(topic, Envelope(payload={"n": 0}))
    script = tmp_path / "stuck_exit.py"
    script.write_text(
        STUCK_EXIT_SCRIPT.format(bootstrap=BOOTSTRAP, topic=topic, group=f"{prefix}-group"),
        encoding="utf-8",
    )

    done = subprocess.run(  # nosec B603 - fixed argv, no shell
        [sys.executable, str(script)],
        cwd=BACKEND_DIR,
        env={**os.environ, "PYTHONPATH": str(BACKEND_DIR)},
        capture_output=True,
        text=True,
        timeout=90,
    )
    exited_at = time.time()

    assert done.returncode == 0, done.stdout + done.stderr
    [finished_line] = [ln for ln in done.stdout.splitlines() if ln.startswith("main finished at")]
    # stop() 等满 2s 后返回、主线程结束；卡死的 handler 在守护线程上，进程随即退出
    assert exited_at - float(finished_line.split()[-1]) < 5
