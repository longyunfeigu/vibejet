# input: AiokafkaPublisher + 真实 AIOKafkaProducer 的离线子类（只跳过联网的 start 与 send，构造期参数与编解码器校验照常生效）
# output: 发布端测试：ProducerTuning→aiokafka 参数映射（max_batch_size/idempotence/request_timeout_ms/acks 数值化，不传 max_in_flight）、默认 zstd 有编解码器、send_wait_s/delivery_wait_s 超时抛 PublishError、元数据与中间件；publish_many 先全部发出再一起等送达、任一失败或超时抛 PublishError（入队与送达错误都挂在 __cause__）；构造失败不留线程、不留未关闭的 producer；只在 OutOfOrderSequenceNumber/UnknownProducerId 时换新 producer（触发的调用照样抛 PublishError，并发只换一次、只告警一次，旧 producer 借用都结束后才关）
# pos: 后端测试 - Kafka 发布者与真实 aiokafka 构造契约的对齐验证；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
from __future__ import annotations

import asyncio
import gc
import logging
import threading
import time
import warnings
from collections import deque
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Optional, Union

import pytest

from infrastructure.external.messaging.base import Envelope, PublishResult
from infrastructure.external.messaging.config import KafkaConfig, ProducerTuning
from infrastructure.external.messaging.exceptions import PublishError
from infrastructure.external.messaging.providers.aiokafka._client_config import (
    aiokafka_acks,
    producer_kwargs,
)
from infrastructure.external.messaging.providers.aiokafka.publisher import AiokafkaPublisher
from infrastructure.external.messaging.serializers.json import JsonSerializer

aiokafka = pytest.importorskip("aiokafka")
aiokafka_errors = pytest.importorskip("aiokafka.errors")

PUBLISHER_LOGGER = "messaging.aiokafka.publisher"
PRODUCER_REBUILT = "producer rebuilt after a sequence error; later sends use a new producer"


def publisher_warnings(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [
        r.getMessage()
        for r in caplog.records
        if r.name == PUBLISHER_LOGGER and r.levelno == logging.WARNING
    ]


@dataclass
class OfflineProducers:
    """离线 producer 的控制面：记录构造参数与发送，按 mode 模拟入队/送达卡住或失败。"""

    created: list[Any] = field(default_factory=list)
    sent: list[tuple[Any, ...]] = field(default_factory=list)
    # ok | hang_enqueue | hang_delivery | fail_delivery | fail_second | batch
    mode: str = "ok"
    # mode=batch：攒够 batch_size 条才一起送达（逐条等送达会一直卡住）
    batch_size: int = 0
    undelivered: list[Any] = field(default_factory=list)
    # mode=batch 时这一批统一失败的错误（None 表示都送达）
    batch_error: Optional[BaseException] = None
    # 依次落到后续送达上的错误，用完后照 mode 处理
    delivery_errors: deque[BaseException] = field(default_factory=deque)
    # 每次发送用的是哪个 producer、哪些 producer 被关了、关了之后有没有再被用
    sent_by: list[Any] = field(default_factory=list)
    stopped: list[Any] = field(default_factory=list)
    used_after_stop: bool = False


@pytest.fixture
def producers(monkeypatch: pytest.MonkeyPatch) -> OfflineProducers:
    from aiokafka import AIOKafkaProducer

    control = OfflineProducers()

    class _OfflineProducer(AIOKafkaProducer):
        """真实构造（参数名、取值、编解码器都校验），只是不连 broker。"""

        def __init__(self, **kwargs: Any) -> None:
            super().__init__(**kwargs)
            self.passed_kwargs = kwargs
            control.created.append(self)

        async def start(self) -> None:
            return None

        async def stop(self) -> None:
            control.stopped.append(self)
            await super().stop()

        async def send(
            self,
            topic: str,
            value: Any = None,
            key: Any = None,
            partition: Any = None,
            timestamp_ms: Any = None,
            headers: Any = None,
        ) -> Any:
            control.sent.append((topic, value, key, headers))
            control.sent_by.append(self)
            if self in control.stopped:
                control.used_after_stop = True
            if control.mode == "fail_enqueue_second" and len(control.sent) == 2:
                raise RuntimeError("buffer refused")
            if control.mode == "hang_enqueue":
                await asyncio.sleep(10)
            delivery: asyncio.Future[Any] = asyncio.get_running_loop().create_future()
            _settle_offline_delivery(control, delivery)
            return delivery

    monkeypatch.setattr(aiokafka, "AIOKafkaProducer", _OfflineProducer)
    return control


def _settle_offline_delivery(control: OfflineProducers, delivery: "asyncio.Future[Any]") -> None:
    """按 mode 给刚发出的那条定送达结果（hang_delivery 时一直不送达）。"""
    if control.delivery_errors:
        delivery.set_exception(control.delivery_errors.popleft())
        return
    offset = len(control.sent) - 1
    if control.mode in ("ok", "fail_enqueue_second") or (
        control.mode == "fail_second" and offset != 1
    ):
        delivery.set_result(SimpleNamespace(partition=0, offset=offset))
    elif control.mode in ("fail_delivery", "fail_second"):
        delivery.set_exception(RuntimeError("broker rejected"))
    elif control.mode == "batch":
        control.undelivered.append(delivery)
        if len(control.undelivered) == control.batch_size:
            _release_batch(control)


def _release_batch(control: OfflineProducers) -> None:
    for n, pending in enumerate(control.undelivered):
        if control.batch_error is not None:
            pending.set_exception(control.batch_error)
        else:
            pending.set_result(SimpleNamespace(partition=0, offset=n))


def test_publisher_maps_tuning_onto_real_aiokafka_parameters(producers: OfflineProducers) -> None:
    cfg = KafkaConfig(
        bootstrap_servers="kafka:9092",
        client_id="svc",
        producer=ProducerTuning(
            acks="all",
            compression_type="gzip",
            linger_ms=7,
            batch_size=32_768,
            max_in_flight=3,
            message_timeout_ms=90_000,
        ),
    )

    publisher = AiokafkaPublisher(cfg, JsonSerializer())
    try:
        [producer] = producers.created
        # max_in_flight 在 aiokafka 里没有对应参数，不传
        assert producer.passed_kwargs == {
            "bootstrap_servers": "kafka:9092",
            "client_id": "svc",
            "acks": "all",
            "enable_idempotence": True,
            "compression_type": "gzip",
            "linger_ms": 7,
            "max_batch_size": 32_768,
            "request_timeout_ms": 90_000,
            "security_protocol": "PLAINTEXT",
            "ssl_context": None,
            "sasl_mechanism": None,
            "sasl_plain_username": None,
            "sasl_plain_password": None,
        }
    finally:
        publisher.close()


def test_default_zstd_compression_has_a_codec(producers: OfflineProducers) -> None:
    from aiokafka.codec import has_zstd

    assert has_zstd(), "aiokafka extra must pull the zstd codec (aiokafka[zstd])"

    publisher = AiokafkaPublisher(KafkaConfig(), JsonSerializer())
    try:
        assert producers.created[0].passed_kwargs["compression_type"] == "zstd"
    finally:
        publisher.close()


@pytest.mark.parametrize(
    ("acks", "idempotence", "expected"),
    [("all", True, "all"), ("-1", True, -1), ("1", False, 1), ("0", False, 0)],
)
def test_acks_text_maps_onto_aiokafka_values(
    producers: OfflineProducers, acks: str, idempotence: bool, expected: Union[int, str]
) -> None:
    cfg = KafkaConfig(producer=ProducerTuning(acks=acks, enable_idempotence=idempotence))

    publisher = AiokafkaPublisher(cfg, JsonSerializer())
    try:
        assert producers.created[0].passed_kwargs["acks"] == expected
    finally:
        publisher.close()
    assert aiokafka_acks(acks) == expected


def test_idempotence_requires_acks_all_in_real_aiokafka() -> None:
    from aiokafka import AIOKafkaProducer

    cfg = KafkaConfig(producer=ProducerTuning(acks="1", enable_idempotence=True))

    async def _construct() -> None:
        AIOKafkaProducer(bootstrap_servers="127.0.0.1:9", **producer_kwargs(cfg))

    with pytest.raises(ValueError, match="acks=1 not supported if enable_idempotence=True"):
        asyncio.run(_construct())


def test_publish_returns_metadata_and_runs_middlewares(producers: OfflineProducers) -> None:
    calls: list[tuple[Any, ...]] = []

    class _Recorder:
        def before_publish(self, topic: str, env: Envelope) -> Envelope:
            calls.append(("before", topic))
            return env

        def after_publish(self, topic: str, env: Envelope, result: PublishResult) -> None:
            calls.append(("after", topic, result))

    publisher = AiokafkaPublisher(KafkaConfig(), JsonSerializer(), [_Recorder()])
    try:
        result = publisher.publish(
            "orders", Envelope(payload={"id": 1}, key=b"k", headers={"h": b"v"})
        )
    finally:
        publisher.close()

    assert result == PublishResult(topic="orders", partition=0, offset=0, timestamp=None)
    assert producers.sent == [("orders", b'{"id":1}', b"k", [("h", b"v")])]
    assert calls == [("before", "orders"), ("after", "orders", result)]


@pytest.mark.parametrize(
    ("mode", "tuning", "message"),
    [
        ("hang_enqueue", ProducerTuning(send_wait_s=0.05), "queue full"),
        ("hang_delivery", ProducerTuning(delivery_wait_s=0.05), "Delivery wait timeout"),
    ],
)
def test_publish_gives_up_after_the_configured_wait(
    producers: OfflineProducers, mode: str, tuning: ProducerTuning, message: str
) -> None:
    producers.mode = mode
    publisher = AiokafkaPublisher(KafkaConfig(producer=tuning), JsonSerializer())
    started = time.monotonic()
    try:
        with pytest.raises(PublishError, match=message):
            publisher.publish("orders", Envelope(payload={"id": 1}))
    finally:
        publisher.close()

    assert time.monotonic() - started < 2


def test_delivery_failure_raises_publish_error_without_rebuilding(
    producers: OfflineProducers,
) -> None:
    producers.mode = "fail_delivery"
    publisher = AiokafkaPublisher(KafkaConfig(), JsonSerializer())
    try:
        with pytest.raises(PublishError, match="Failed to publish record: broker rejected") as exc:
            publisher.publish("orders", Envelope(payload={"id": 1}))
    finally:
        publisher.close()

    assert isinstance(exc.value.__cause__, RuntimeError)
    assert len(producers.created) == 1  # 只有序号类错误才换 producer


@pytest.mark.parametrize("error_name", ["OutOfOrderSequenceNumber", "UnknownProducerId"])
def test_sequence_error_rebuilds_the_producer_and_still_raises(
    producers: OfflineProducers, caplog: pytest.LogCaptureFixture, error_name: str
) -> None:
    caplog.set_level(logging.WARNING, logger=PUBLISHER_LOGGER)
    error = getattr(aiokafka_errors, error_name)()
    producers.delivery_errors.append(error)
    publisher = AiokafkaPublisher(KafkaConfig(), JsonSerializer())
    try:
        with pytest.raises(PublishError) as excinfo:
            publisher.publish("orders", Envelope(payload={"n": 1}))
        result = publisher.publish("orders", Envelope(payload={"n": 2}))
    finally:
        publisher.close()

    first, second = producers.created
    # 触发的那次照样报错（不偷偷重发）；换了一次 producer，下一条走新的
    assert excinfo.value.__cause__ is error
    assert producers.sent_by == [first, second]
    assert result.offset == 1
    assert publisher_warnings(caplog) == [PRODUCER_REBUILT]
    assert producers.stopped == [first, second]
    assert not producers.used_after_stop


def test_concurrent_sequence_errors_share_one_rebuild_and_retire_the_old_producer(
    producers: OfflineProducers, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING, logger=PUBLISHER_LOGGER)
    # 两条并发的发送都卡在同一个 producer 上，一起收到 OutOfOrderSequenceNumber
    producers.mode = "batch"
    producers.batch_size = 2
    producers.batch_error = aiokafka_errors.OutOfOrderSequenceNumber()
    cfg = KafkaConfig(producer=ProducerTuning(delivery_wait_s=2.0))
    publisher = AiokafkaPublisher(cfg, JsonSerializer())
    errors: list[BaseException] = []

    def _publish(n: int) -> None:
        try:
            publisher.publish("orders", Envelope(payload={"n": n}))
        except PublishError as exc:
            errors.append(exc)

    try:
        callers = [threading.Thread(target=_publish, args=(n,)) for n in range(2)]
        for caller in callers:
            caller.start()
        for caller in callers:
            caller.join(timeout=5)
        producers.mode = "ok"
        publisher.publish("orders", Envelope(payload={"n": 2}))
    finally:
        publisher.close()

    first, second = producers.created
    # 两个调用各自拿到 PublishError，但只换了一次 producer、只告警一次
    assert len(errors) == 2
    assert all(
        isinstance(exc.__cause__, aiokafka_errors.OutOfOrderSequenceNumber) for exc in errors
    )
    assert publisher_warnings(caplog) == [PRODUCER_REBUILT]
    # 旧 producer 等两次借用都结束才关；关了之后没再被用；之后的发送走新的
    assert producers.sent_by == [first, first, second]
    assert producers.stopped == [first, second]
    assert not producers.used_after_stop


class _OrderRecorder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    def before_publish(self, topic: str, env: Envelope) -> Envelope:
        self.calls.append(("before", env.payload["n"]))
        return env

    def after_publish(self, topic: str, env: Envelope, result: PublishResult) -> None:
        self.calls.append(("after", env.payload["n"]))


def test_publish_many_sends_everything_before_waiting_for_delivery(
    producers: OfflineProducers,
) -> None:
    # 送达要等 3 条都发出后才完成：逐条等送达的实现会卡到 delivery_wait_s 超时
    producers.mode = "batch"
    producers.batch_size = 3
    recorder = _OrderRecorder()
    cfg = KafkaConfig(producer=ProducerTuning(delivery_wait_s=1.0))
    publisher = AiokafkaPublisher(cfg, JsonSerializer(), [recorder])
    try:
        results = publisher.publish_many("orders", [Envelope(payload={"n": n}) for n in range(3)])
    finally:
        publisher.close()

    assert results == [
        PublishResult(topic="orders", partition=0, offset=n, timestamp=None) for n in range(3)
    ]
    assert [sent[1] for sent in producers.sent] == [b'{"n":0}', b'{"n":1}', b'{"n":2}']
    assert recorder.calls == [
        ("before", 0),
        ("before", 1),
        ("before", 2),
        ("after", 0),
        ("after", 1),
        ("after", 2),
    ]


def test_publish_many_raises_publish_error_when_any_delivery_fails(
    producers: OfflineProducers,
) -> None:
    producers.mode = "fail_second"
    recorder = _OrderRecorder()
    publisher = AiokafkaPublisher(KafkaConfig(), JsonSerializer(), [recorder])
    try:
        with pytest.raises(PublishError, match="^broker rejected$") as excinfo:
            publisher.publish_many("orders", [Envelope(payload={"n": n}) for n in range(3)])
    finally:
        publisher.close()

    # 三条都发出了；有一条失败就整体报错（原错误挂在 __cause__），after_publish 一条都不调用
    assert isinstance(excinfo.value.__cause__, RuntimeError)
    assert len(producers.sent) == 3
    assert [call[0] for call in recorder.calls] == ["before", "before", "before"]


def test_publish_many_error_lists_at_most_three_failures(producers: OfflineProducers) -> None:
    producers.mode = "fail_delivery"
    publisher = AiokafkaPublisher(KafkaConfig(), JsonSerializer())
    try:
        with pytest.raises(PublishError) as excinfo:
            publisher.publish_many("orders", [Envelope(payload={"n": n}) for n in range(5)])
    finally:
        publisher.close()

    assert str(excinfo.value) == "broker rejected; broker rejected; broker rejected ..."


def test_publish_many_wraps_an_enqueue_error_as_publish_error(
    producers: OfflineProducers,
) -> None:
    producers.mode = "fail_enqueue_second"
    publisher = AiokafkaPublisher(KafkaConfig(), JsonSerializer())
    try:
        with pytest.raises(
            PublishError, match="Failed to enqueue record: buffer refused"
        ) as excinfo:
            publisher.publish_many("orders", [Envelope(payload={"n": n}) for n in range(3)])
    finally:
        publisher.close()

    assert isinstance(excinfo.value.__cause__, RuntimeError)
    # 第一条已经交给 producer：它可能照样送达，整批重试会重复它（at-least-once）
    assert len(producers.sent) == 2


def test_failed_constructor_leaves_no_thread_or_open_client() -> None:
    from aiokafka.errors import KafkaConnectionError

    cfg = KafkaConfig(bootstrap_servers="127.0.0.1:1")  # 这个端口上没有 broker
    gc.collect()
    threads_before = threading.active_count()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        for _ in range(4):
            with pytest.raises(KafkaConnectionError):
                AiokafkaPublisher(cfg, JsonSerializer())
        gc.collect()

    # 每次失败都关掉了自己的事件循环线程和 producer
    assert threading.active_count() == threads_before
    assert [str(w.message) for w in caught if "Unclosed" in str(w.message)] == []


def test_publish_many_gives_up_after_delivery_wait(producers: OfflineProducers) -> None:
    producers.mode = "hang_delivery"
    cfg = KafkaConfig(producer=ProducerTuning(delivery_wait_s=0.05))
    publisher = AiokafkaPublisher(cfg, JsonSerializer())
    started = time.monotonic()
    try:
        with pytest.raises(PublishError, match="Delivery wait timeout for produced messages"):
            publisher.publish_many("orders", [Envelope(payload={"n": n}) for n in range(3)])
    finally:
        publisher.close()

    assert time.monotonic() - started < 2
