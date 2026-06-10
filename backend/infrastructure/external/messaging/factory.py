from __future__ import annotations

from typing import List, Optional

from .base import ConsumeMiddleware, Consumer, PublishMiddleware, Publisher, Serializer
from .config import MessagingConfig

# Both kafka drivers are optional extras; import lazily so this package stays
# importable when neither `vibejet[kafka]` nor `vibejet[aiokafka]` is installed.
try:
    from .providers.kafka.publisher import KafkaPublisher
    from .providers.kafka.consumer import KafkaConsumer
except Exception:
    KafkaPublisher = None  # type: ignore
    KafkaConsumer = None  # type: ignore

try:
    from .providers.aiokafka.publisher import AiokafkaPublisher
    from .providers.aiokafka.consumer import AiokafkaConsumer
except Exception:
    AiokafkaPublisher = None  # type: ignore
    AiokafkaConsumer = None  # type: ignore


def create_publisher(
    cfg: MessagingConfig,
    serializer: Serializer,
    middlewares: Optional[List[PublishMiddleware]] = None,
) -> Publisher:
    if cfg.provider == "kafka":
        if cfg.kafka.driver == "confluent":
            if KafkaPublisher is None:
                raise ImportError("confluent-kafka not installed. `pip install vibejet[kafka]`.")
            return KafkaPublisher(cfg.kafka, serializer, middlewares)
        elif cfg.kafka.driver == "aiokafka":
            if AiokafkaPublisher is None:
                raise ImportError("aiokafka not installed. `pip install vibejet[aiokafka]`.")
            return AiokafkaPublisher(cfg.kafka, serializer, middlewares)
    raise ValueError(f"Unsupported provider: {cfg.provider}")


def create_consumer(
    cfg: MessagingConfig,
    serializer: Serializer,
    middlewares: Optional[List[ConsumeMiddleware]] = None,
) -> Consumer:
    if cfg.provider == "kafka":
        if cfg.kafka.driver == "confluent":
            if KafkaConsumer is None:
                raise ImportError("confluent-kafka not installed. `pip install vibejet[kafka]`.")
            return KafkaConsumer(cfg.kafka, cfg.retry, serializer, middlewares)
        elif cfg.kafka.driver == "aiokafka":
            if AiokafkaConsumer is None:
                raise ImportError("aiokafka not installed. `pip install vibejet[aiokafka]`.")
            return AiokafkaConsumer(cfg.kafka, cfg.retry, serializer, middlewares)
    raise ValueError(f"Unsupported provider: {cfg.provider}")
