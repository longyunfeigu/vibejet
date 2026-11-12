from __future__ import annotations

from typing import List, Optional

from .base import ConsumeMiddleware, Consumer, Publisher, PublishMiddleware, Serializer
from .config import MessagingConfig

# The aiokafka provider modules import aiokafka lazily (inside the client
# constructors), so this package stays importable without the `aiokafka` extra;
# the constructors raise ImportError when it is missing.
from .providers.aiokafka.consumer import AiokafkaConsumer
from .providers.aiokafka.publisher import AiokafkaPublisher


def _ensure_supported(cfg: MessagingConfig) -> None:
    if cfg.provider != "kafka":
        raise ValueError(f"Unsupported provider: {cfg.provider}")
    if cfg.kafka.driver != "aiokafka":
        raise ValueError(
            f"Unsupported Kafka driver: {cfg.kafka.driver!r}; only 'aiokafka' is supported "
            "(the confluent driver was removed)."
        )


def create_publisher(
    cfg: MessagingConfig,
    serializer: Serializer,
    middlewares: Optional[List[PublishMiddleware]] = None,
) -> Publisher:
    _ensure_supported(cfg)
    return AiokafkaPublisher(cfg.kafka, serializer, middlewares)


def create_consumer(
    cfg: MessagingConfig,
    serializer: Serializer,
    middlewares: Optional[List[ConsumeMiddleware]] = None,
) -> Consumer:
    _ensure_supported(cfg)
    return AiokafkaConsumer(cfg.kafka, cfg.retry, serializer, middlewares)
