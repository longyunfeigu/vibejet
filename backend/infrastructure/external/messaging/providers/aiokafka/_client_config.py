# input: KafkaConfig（TLS/SASL、ProducerTuning、ConsumerTuning）
# output: security_kwargs / producer_kwargs / requeue_producer_kwargs / consumer_kwargs / build_ssl_context / aiokafka_acks（映射到 AIOKafkaProducer/AIOKafkaConsumer 的真实参数；rebalance_timeout_ms 取 max_poll_interval_ms）
# owner: unknown
# pos: 基础设施层 - aiokafka 客户端参数映射（发布者与消费者共用的唯一来源）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Map vibejet's KafkaConfig onto aiokafka client parameters.

Settings with no aiokafka equivalent are not passed: ProducerTuning.max_in_flight and
ConsumerTuning.max_concurrency / inflight_max. Auto-commit is always off because
AiokafkaConsumer commits offsets itself.
"""

from __future__ import annotations

import ssl
from typing import Any, Dict, Optional, Union

from ...config import KafkaConfig, TLSConfig

_NUMERIC_ACKS = {"0": 0, "1": 1, "-1": -1}


def security_protocol(cfg: KafkaConfig) -> str:
    use_sasl = bool(cfg.sasl.mechanism)
    if cfg.tls.enable:
        return "SASL_SSL" if use_sasl else "SSL"
    return "SASL_PLAINTEXT" if use_sasl else "PLAINTEXT"


def build_ssl_context(tls: TLSConfig) -> Optional[ssl.SSLContext]:
    """Build an SSL context from the provided files and verify flag; None when TLS is off."""
    if not tls.enable:
        return None
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    if tls.verify:
        ctx.verify_mode = ssl.CERT_REQUIRED
        _load_trust_store(ctx, tls.ca_location)
    else:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    if tls.certificate and tls.key:
        ctx.load_cert_chain(certfile=tls.certificate, keyfile=tls.key)
    return ctx


def _load_trust_store(ctx: ssl.SSLContext, ca_location: Optional[str]) -> None:
    try:
        if ca_location:
            ctx.load_verify_locations(cafile=ca_location)
        else:
            ctx.load_default_certs()
    except Exception:
        # Fall back to default certs if custom CA load fails
        ctx.load_default_certs()


def security_kwargs(cfg: KafkaConfig) -> Dict[str, Any]:
    """TLS/SASL parameters; build once per client pair so both share one SSL context."""
    return {
        "security_protocol": security_protocol(cfg),
        "ssl_context": build_ssl_context(cfg.tls),
        "sasl_mechanism": cfg.sasl.mechanism,
        "sasl_plain_username": cfg.sasl.username,
        "sasl_plain_password": cfg.sasl.password,
    }


def aiokafka_acks(value: str) -> Union[int, str]:
    """Settings carry acks as text; aiokafka accepts the ints 0, 1, -1 or "all"."""
    normalized = value.strip().lower()
    return _NUMERIC_ACKS.get(normalized, normalized)


def producer_kwargs(cfg: KafkaConfig) -> Dict[str, Any]:
    """ProducerTuning as AIOKafkaProducer parameters (publisher and requeue producer).

    aiokafka rejects enable_idempotence=True unless acks is "all" (or -1).
    message_timeout_ms maps to request_timeout_ms, which aiokafka also uses as the
    delivery deadline of a queued batch (librdkafka's message.timeout.ms).
    """
    tuning = cfg.producer
    return {
        "acks": aiokafka_acks(tuning.acks),
        "enable_idempotence": tuning.enable_idempotence,
        "compression_type": tuning.compression_type,
        "linger_ms": tuning.linger_ms,
        "max_batch_size": tuning.batch_size,
        "request_timeout_ms": tuning.message_timeout_ms,
    }


def requeue_producer_kwargs(cfg: KafkaConfig) -> Dict[str, Any]:
    """The consumer's retry/DLQ producer: transactional when transactional_id is set."""
    kwargs = producer_kwargs(cfg)
    if cfg.transactional_id:
        kwargs["transactional_id"] = cfg.transactional_id
    return kwargs


def consumer_kwargs(cfg: KafkaConfig, group_id: Optional[str]) -> Dict[str, Any]:
    """ConsumerTuning as AIOKafkaConsumer parameters."""
    tuning = cfg.consumer
    kwargs: Dict[str, Any] = {
        "group_id": group_id,
        # AiokafkaConsumer commits processed offsets itself (at-least-once)
        "enable_auto_commit": False,
        "auto_offset_reset": tuning.auto_offset_reset,
        "max_poll_interval_ms": tuning.max_poll_interval_ms,
        # How long the group waits for a member to rejoin during a rebalance. aiokafka
        # defaults it to session_timeout_ms, shorter than a slow handler: the partition then
        # moves while its record is still being handled. Java uses max.poll.interval.ms too.
        "rebalance_timeout_ms": tuning.max_poll_interval_ms,
        "session_timeout_ms": tuning.session_timeout_ms,
        "fetch_min_bytes": tuning.fetch_min_bytes,
        "fetch_max_bytes": tuning.fetch_max_bytes,
    }
    if cfg.transactional_id:
        # skip records of aborted requeue transactions on the retry topics
        kwargs["isolation_level"] = "read_committed"
    return kwargs
