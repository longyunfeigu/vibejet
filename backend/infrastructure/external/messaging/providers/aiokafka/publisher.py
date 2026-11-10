# input: aiokafka（AIOKafkaProducer，运行期延迟导入）, KafkaConfig, Serializer, PublishMiddleware
# output: AiokafkaPublisher（同步 publish / 批量 publish_many：先编码（SerializationError 原样抛出，什么都不发），再全部交给 producer、一起等送达；发送失败都抛 PublishError（__cause__ 为原错误），失败前已交出的记录可能已送达、整批重试会重复；send_wait_s 限制入队、delivery_wait_s 限制送达；幂等 producer 有一批被 broker 拒收后立即标记失效，下一次发送前换新 producer（并发安全、每次换告警一次）；与被拒记录同批的记录也会以同一错误失败（Kafka 按批拒收）；构造失败时关闭 producer 和事件循环线程）
# owner: unknown
# pos: 基础设施层 - Kafka 发布者（aiokafka 驱动；客户端参数统一由 _client_config 映射，可替换 producer 见 _producer_slot）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
from __future__ import annotations

import asyncio
import contextlib
import functools
import logging
from typing import Any, Iterable, List, Optional, Sequence

from ...base import Envelope, Publisher, PublishMiddleware, PublishResult, Serializer
from ...config import KafkaConfig
from ...exceptions import PublishError
from ._client_config import producer_kwargs, security_kwargs
from ._loop import LoopThread
from ._producer_slot import ProducerSlot

_PRODUCER_REBUILT = "producer rebuilt after the broker rejected a batch; later sends use it"
_REBUILD_FAILED = "producer rebuild failed; the next send tries again"


def _to_headers(headers: dict[str, bytes]) -> List[tuple[str, bytes]]:
    return [(k, v) for k, v in headers.items()]


def _summarize(failures: Sequence[BaseException]) -> str:
    text = "; ".join(str(f) for f in failures[:3])
    return text + (" ..." if len(failures) > 3 else "")


class AiokafkaPublisher(Publisher):
    def __init__(
        self,
        cfg: KafkaConfig,
        serializer: Serializer,
        middlewares: Optional[List[PublishMiddleware]] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.cfg = cfg
        self.serializer = serializer
        self.middlewares = middlewares or []
        self.log = logger or logging.getLogger("messaging.aiokafka.publisher")
        try:
            from aiokafka import AIOKafkaProducer
        except Exception as e:  # noqa: BLE001
            raise ImportError(
                "aiokafka is required for AiokafkaPublisher. Install via `pip install aiokafka`."
            ) from e
        self._AIOKafkaProducer = AIOKafkaProducer
        # aiokafka 0.13 never resets a partition's sequence number after the broker rejects
        # a batch, so an idempotent producer is replaced after any rejected delivery
        self._idempotent = cfg.producer.enable_idempotence
        self._slot = ProducerSlot(self._create_producer, self.log, cfg.producer.delivery_wait_s)
        self._loop = LoopThread()
        self._loop.start()
        try:
            self._loop.run_coro(self._slot.open())
        except BaseException:
            # a failed constructor must not leave its loop thread behind
            self._loop.stop()
            raise

    async def _create_producer(self) -> Any:
        from aiokafka import AIOKafkaProducer

        producer = AIOKafkaProducer(
            bootstrap_servers=self.cfg.bootstrap_servers,
            client_id=self.cfg.client_id,
            **producer_kwargs(self.cfg),
            **security_kwargs(self.cfg),
        )
        try:
            await producer.start()
        except BaseException:
            # close the half-started client (connections, sender) before giving up
            with contextlib.suppress(Exception):
                await producer.stop()
            raise
        return producer

    def publish(self, topic: str, env: Envelope) -> PublishResult:
        """Send one record and wait for its delivery.

        A SerializationError propagates as is and nothing is sent (retrying cannot help).
        Any send failure raises PublishError, with the underlying error as its __cause__.
        """
        env = self._before_publish(topic, env)
        value = self._encode(env)
        md = self._loop.run_coro(self._send(topic, env, value))
        return self._after_publish(topic, env, md)

    def publish_many(self, topic: str, envs: Iterable[Envelope]) -> List[PublishResult]:
        """Encode every record, hand them all to the producer, then wait for the deliveries.

        A SerializationError propagates as is before anything is sent. Any send failure
        raises PublishError, with the first underlying error as its __cause__. Records
        handed over before the failure may still be delivered, so retrying the whole
        batch can deliver some of them twice (at-least-once).
        """
        prepared = [self._before_publish(topic, env) for env in envs]
        values = [self._encode(env) for env in prepared]
        outcomes = self._loop.run_coro(self._send_all(topic, prepared, values))
        failures = [o for o in outcomes if isinstance(o, BaseException)]
        if failures:
            raise PublishError(_summarize(failures)) from failures[0]
        return [self._after_publish(topic, env, md) for env, md in zip(prepared, outcomes)]

    def _before_publish(self, topic: str, env: Envelope) -> Envelope:
        for m in self.middlewares:
            env = m.before_publish(topic, env)
        return env

    def _after_publish(self, topic: str, env: Envelope, md: Any) -> PublishResult:
        result = PublishResult(
            topic=topic, partition=md.partition, offset=md.offset, timestamp=None
        )
        for m in self.middlewares:
            m.after_publish(topic, env, result)
        return result

    def _encode(self, env: Envelope) -> Any:
        if isinstance(env.payload, (bytes, bytearray)):
            return env.payload
        return self.serializer.dumps(env.payload)

    async def _send(self, topic: str, env: Envelope, value: Any) -> Any:
        await self._refresh_producer()
        async with self._slot.lease() as producer:
            delivery = await self._enqueue(producer, topic, env, value)
            try:
                # shield: giving up the wait must not cancel aiokafka's own delivery future
                return await asyncio.wait_for(
                    asyncio.shield(delivery), timeout=self.cfg.producer.delivery_wait_s
                )
            except asyncio.TimeoutError as e:
                raise PublishError("Delivery wait timeout for produced message") from e
            except Exception as e:
                raise PublishError(f"Failed to publish record: {e}") from e

    async def _send_all(self, topic: str, envs: List[Envelope], values: List[Any]) -> List[Any]:
        await self._refresh_producer()
        async with self._slot.lease() as producer:
            deliveries = [
                await self._enqueue(producer, topic, env, value) for env, value in zip(envs, values)
            ]
            return await self._wait_all(deliveries)

    async def _wait_all(self, deliveries: List[Any]) -> List[Any]:
        waiting = asyncio.gather(*(asyncio.shield(d) for d in deliveries), return_exceptions=True)
        try:
            return list(await asyncio.wait_for(waiting, timeout=self.cfg.producer.delivery_wait_s))
        except asyncio.TimeoutError as e:
            raise PublishError("Delivery wait timeout for produced messages") from e

    async def _enqueue(self, producer: Any, topic: str, env: Envelope, value: Any) -> Any:
        """Hand the record to the producer, waiting at most send_wait_s.

        The wait covers aiokafka's topic-metadata lookup and room in its buffer. These
        client-side errors leave the producer usable; a rejected delivery does not.
        """
        try:
            delivery = await asyncio.wait_for(
                producer.send(topic, value=value, key=env.key, headers=_to_headers(env.headers)),
                timeout=self.cfg.producer.send_wait_s,
            )
        except asyncio.TimeoutError as e:
            raise PublishError("Producer queue full: timed out while enqueueing") from e
        except Exception as e:
            raise PublishError(f"Failed to enqueue record: {e}") from e
        delivery.add_done_callback(functools.partial(self._note_delivery, producer))
        return delivery

    def _note_delivery(self, producer: Any, delivery: asyncio.Future[Any]) -> None:
        """When the broker rejects a batch, have the next send use a new producer.

        aiokafka (0.13) has already moved that partition's sequence number past the
        rejected batch and never resets it, so the producer's next batch there would fail
        with OutOfOrderSequenceNumber. Reading the error also keeps an abandoned delivery
        from being logged as never retrieved.
        """
        if delivery.cancelled() or delivery.exception() is None:
            return
        if self._idempotent:
            self._slot.mark_stale(producer)

    async def _refresh_producer(self) -> None:
        """Replace a stale producer before the next send; concurrent callers share one rebuild."""
        if not self._slot.stale:
            return
        try:
            rebuilt = await self._slot.replace_stale()
        except Exception as e:  # noqa: BLE001 - keep sending with the old producer
            self.log.warning(_REBUILD_FAILED, extra={"error": str(e)})
            return
        if rebuilt:
            self.log.warning(_PRODUCER_REBUILT)

    def close(self) -> None:
        try:
            self._loop.run_coro(self._slot.close())
        finally:
            self._loop.stop()
