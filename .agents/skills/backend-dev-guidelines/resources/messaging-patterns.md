# Messaging Patterns - Kafka & Event-Driven Architecture

Production-ready messaging patterns for FastAPI microservices using Apache Kafka.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Configuration Patterns](#configuration-patterns)
- [Publisher Patterns](#publisher-patterns)
- [Consumer Patterns](#consumer-patterns)
- [Serialization](#serialization)
- [Middleware Pipeline](#middleware-pipeline)
- [Retry & Dead Letter Queue](#retry--dead-letter-queue)
- [Error Handling](#error-handling)
- [Distributed Tracing](#distributed-tracing)
- [Testing Patterns](#testing-patterns)
- [Anti-Patterns](#anti-patterns)

---

## Architecture Overview

### Provider-Agnostic Abstraction

```
Application Layer (Services)
         ↓
    Factory Pattern
         ↓
Base Abstraction (Publisher/Consumer protocols)
         ↓
Provider Implementations:
  ├── confluent-kafka (synchronous, production-grade)
  └── aiokafka (asynchronous, Python-native)
```

### Directory Structure

```
infrastructure/external/messaging/
├── __init__.py              # Public exports
├── base.py                  # Abstract Publisher/Consumer protocols
├── envelope.py              # Message envelope data class
├── config.py                # Configuration dataclasses
├── exceptions.py            # Error hierarchy
├── factory.py               # Provider factory
├── serializers/
│   ├── __init__.py
│   └── json.py              # JSON serializer
├── middlewares/
│   ├── __init__.py
│   ├── logging.py           # Logging middleware
│   ├── metrics.py           # Prometheus metrics
│   ├── tracing.py           # OpenTelemetry tracing
│   └── retry.py             # Retry policy
└── providers/
    ├── kafka/               # confluent-kafka driver
    │   ├── consumer.py
    │   └── publisher.py
    └── aiokafka/            # aiokafka driver
        ├── _loop.py         # Async event loop bridge
        ├── consumer.py
        └── publisher.py
```

### Core Abstractions

#### Message Envelope

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

@dataclass
class Envelope:
    """Unified message wrapper separating payload from Kafka concerns."""
    payload: Any                              # Business data
    key: Optional[bytes] = None               # Partition key
    headers: Dict[str, bytes] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    version: str = "1.0"

# Standard header constants
H_ATTEMPTS = "x-attempts"           # Retry count
H_ORIGINAL_TOPIC = "x-original-topic"
H_RETRY_NOT_BEFORE = "x-retry-not-before"  # Delay timestamp (ms)
H_CORRELATION_ID = "x-corr-id"
H_TRACEPARENT = "x-traceparent"     # W3C trace context
H_BAGGAGE = "x-baggage"
H_ERROR_CLASS = "x-error-class"     # For DLQ
H_ERROR_MESSAGE = "x-error-msg"
```

#### Handler Result

```python
import enum

class HandleResult(enum.Enum):
    """Consumer handler return values."""
    ACK = "ACK"      # Successfully processed, commit offset
    RETRY = "RETRY"  # Requeue to retry topic with delay
    DROP = "DROP"    # Send to dead letter queue
```

#### Protocol Definitions

```python
from typing import Protocol, Callable, List, Optional
from abc import abstractmethod

class Publisher(Protocol):
    @abstractmethod
    def publish(self, topic: str, envelope: Envelope) -> PublishResult:
        """Publish single message, return partition/offset."""
        ...

    @abstractmethod
    def publish_many(self, topic: str, envelopes: List[Envelope]) -> List[PublishResult]:
        """Batch publish for efficiency."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Graceful shutdown."""
        ...

class Consumer(Protocol):
    @abstractmethod
    def subscribe(self, topics: List[str], group_id: str) -> None:
        """Subscribe to topics with consumer group."""
        ...

    @abstractmethod
    def start(self, handler: Callable[[Envelope], HandleResult]) -> None:
        """Start consuming messages."""
        ...

    @abstractmethod
    def stop(self) -> None:
        """Graceful shutdown."""
        ...
```

---

## Configuration Patterns

### Complete Kafka Configuration

```python
from dataclasses import dataclass, field
from typing import List, Literal, Optional

@dataclass
class TLSConfig:
    """TLS/SSL configuration."""
    enable: bool = False
    ca_location: Optional[str] = None
    certificate: Optional[str] = None
    key: Optional[str] = None
    verify: bool = True

@dataclass
class SASLConfig:
    """SASL authentication configuration."""
    mechanism: Literal["PLAIN", "SCRAM-SHA-256", "SCRAM-SHA-512"] = "PLAIN"
    username: Optional[str] = None
    password: Optional[str] = None

@dataclass
class ProducerTuning:
    """Producer performance tuning."""
    acks: Literal["0", "1", "all"] = "all"  # Wait for all replicas
    enable_idempotence: bool = True          # Prevent duplicates
    compression_type: str = "zstd"           # Best compression ratio
    linger_ms: int = 5                       # Batch delay
    batch_size: int = 65536                  # 64KB batches
    max_in_flight: int = 5                   # Ordering guarantee
    message_timeout_ms: int = 120_000        # 2 minutes
    send_wait_s: float = 5.0                 # Backpressure timeout
    delivery_wait_s: float = 30.0            # Delivery confirmation timeout

@dataclass
class ConsumerTuning:
    """Consumer performance tuning."""
    enable_auto_commit: bool = False         # Manual commits only!
    auto_offset_reset: str = "latest"        # Start from latest
    max_poll_interval_ms: int = 300_000      # 5 minutes
    session_timeout_ms: int = 45_000         # 45 seconds
    fetch_min_bytes: int = 1
    fetch_max_bytes: int = 52_428_800        # 50MB
    commit_every_n: int = 100                # Commit every N messages
    commit_interval_ms: int = 2_000          # Or every 2 seconds

@dataclass
class RetryLayer:
    """Single retry tier configuration."""
    suffix: str
    delay_ms: int

@dataclass
class RetryConfig:
    """Multi-tier retry configuration."""
    layers: List[RetryLayer] = field(default_factory=lambda: [
        RetryLayer(suffix="retry.5s", delay_ms=5_000),
        RetryLayer(suffix="retry.1m", delay_ms=60_000),
        RetryLayer(suffix="retry.10m", delay_ms=600_000),
    ])
    dlq_suffix: str = "dlq"

@dataclass
class KafkaConfig:
    """Complete Kafka configuration."""
    bootstrap_servers: str
    client_id: str = "fastapi-service"
    driver: Literal["confluent", "aiokafka"] = "confluent"
    tls: TLSConfig = field(default_factory=TLSConfig)
    sasl: SASLConfig = field(default_factory=SASLConfig)
    producer: ProducerTuning = field(default_factory=ProducerTuning)
    consumer: ConsumerTuning = field(default_factory=ConsumerTuning)
    retry: RetryConfig = field(default_factory=RetryConfig)
    transactional_id: Optional[str] = None  # For exactly-once semantics
```

### pydantic-settings Integration

```python
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # Kafka settings
    KAFKA_BOOTSTRAP_SERVERS: str = Field(default="localhost:9092")
    KAFKA_CLIENT_ID: str = Field(default="knowledge-hub")
    KAFKA_DRIVER: str = Field(default="confluent")

    # Security
    KAFKA_TLS_ENABLE: bool = Field(default=False)
    KAFKA_SASL_MECHANISM: str = Field(default="PLAIN")
    KAFKA_SASL_USERNAME: Optional[str] = Field(default=None)
    KAFKA_SASL_PASSWORD: Optional[str] = Field(default=None)

    # Producer tuning
    KAFKA_PRODUCER_ACKS: str = Field(default="all")
    KAFKA_PRODUCER_COMPRESSION: str = Field(default="zstd")

    # Consumer tuning
    KAFKA_CONSUMER_GROUP_PREFIX: str = Field(default="knowledge-hub")
    KAFKA_CONSUMER_AUTO_COMMIT: bool = Field(default=False)

    def get_kafka_config(self) -> KafkaConfig:
        return KafkaConfig(
            bootstrap_servers=self.KAFKA_BOOTSTRAP_SERVERS,
            client_id=self.KAFKA_CLIENT_ID,
            driver=self.KAFKA_DRIVER,
            tls=TLSConfig(enable=self.KAFKA_TLS_ENABLE),
            sasl=SASLConfig(
                mechanism=self.KAFKA_SASL_MECHANISM,
                username=self.KAFKA_SASL_USERNAME,
                password=self.KAFKA_SASL_PASSWORD,
            ),
        )
```

---

## Publisher Patterns

### Basic Publisher Usage

```python
from infrastructure.external.messaging import (
    create_publisher,
    Envelope,
    JsonSerializer,
)
from infrastructure.external.messaging.middlewares import (
    LoggingMiddleware,
    MetricsMiddleware,
    TracingMiddleware,
)

# Initialize publisher with middleware stack
publisher = create_publisher(
    config=settings.get_kafka_config(),
    serializer=JsonSerializer(),
    middlewares=[
        LoggingMiddleware(),
        MetricsMiddleware(),
        TracingMiddleware(),
    ],
)

# Simple publish
envelope = Envelope(
    payload={"user_id": 123, "action": "created"},
    key=b"user-123",  # Ensures ordering per user
)
result = publisher.publish("user-events", envelope)
# result.topic, result.partition, result.offset

# Batch publish for efficiency
envelopes = [
    Envelope(payload={"id": i}, key=f"key-{i}".encode())
    for i in range(100)
]
results = publisher.publish_many("batch-topic", envelopes)
```

### Publisher Patterns by Use Case

#### 1. Fire-and-Forget (Async Events)

```python
async def emit_user_created_event(user: User) -> None:
    """Emit event without waiting for confirmation."""
    envelope = Envelope(
        payload={
            "event_type": "user.created",
            "user_id": str(user.id),
            "email": user.email,
            "timestamp": datetime.utcnow().isoformat(),
        },
        key=str(user.id).encode(),  # Partition by user
    )
    try:
        publisher.publish("user-events", envelope)
    except PublishError:
        logger.error("Failed to emit user created event", user_id=user.id)
        # Don't fail the main operation
```

#### 2. Command Pattern (Reliable Delivery)

```python
from domain.events import DocumentProcessCommand

class DocumentCommandPublisher:
    """Publish commands with delivery confirmation."""

    def __init__(self, publisher: Publisher):
        self._publisher = publisher

    def send_process_command(
        self,
        document_id: str,
        correlation_id: str,
    ) -> PublishResult:
        envelope = Envelope(
            payload={
                "command": "process_document",
                "document_id": document_id,
            },
            key=document_id.encode(),
            headers={
                H_CORRELATION_ID: correlation_id.encode(),
            },
        )
        # Raises on failure - caller must handle
        return self._publisher.publish("document-commands", envelope)
```

#### 3. Transactional Outbox Pattern

```python
from sqlalchemy.ext.asyncio import AsyncSession

class OutboxPublisher:
    """Reliable event publishing via outbox pattern."""

    async def publish_with_outbox(
        self,
        session: AsyncSession,
        topic: str,
        envelope: Envelope,
    ) -> None:
        """Insert to outbox table within transaction."""
        outbox_entry = OutboxMessage(
            topic=topic,
            key=envelope.key,
            payload=envelope.payload,
            headers=envelope.headers,
            created_at=datetime.utcnow(),
        )
        session.add(outbox_entry)
        # Committed with main transaction
        # Background worker polls outbox and publishes
```

### Backpressure Handling

The confluent-kafka publisher handles backpressure automatically:

```python
# Internal implementation pattern
def publish(self, topic: str, envelope: Envelope) -> PublishResult:
    send_deadline = time.monotonic() + self._send_wait_s

    while True:
        try:
            self._producer.produce(
                topic=topic,
                value=serialized,
                key=envelope.key,
                headers=headers,
                on_delivery=callback,
            )
            break
        except BufferError:
            # Queue full - poll to drain
            self._producer.poll(0.1)
            if time.monotonic() >= send_deadline:
                raise PublishError(f"Producer queue full after {self._send_wait_s}s")

    # Wait for delivery confirmation
    delivery_deadline = time.monotonic() + self._delivery_wait_s
    while "result" not in holder:
        self._producer.poll(0.05)
        if time.monotonic() >= delivery_deadline:
            raise PublishError("Delivery confirmation timeout")
```

---

## Consumer Patterns

### Basic Consumer Usage

```python
from infrastructure.external.messaging import create_consumer

# Initialize consumer
consumer = create_consumer(
    config=settings.get_kafka_config(),
    serializer=JsonSerializer(),
    middlewares=[
        LoggingMiddleware(),
        MetricsMiddleware(),
        TracingMiddleware(),
    ],
)

# Define handler
def handle_user_event(envelope: Envelope) -> HandleResult:
    try:
        payload = envelope.payload
        if payload["event_type"] == "user.created":
            process_user_creation(payload)
        return HandleResult.ACK
    except ValidationError as e:
        logger.error("Invalid message", error=str(e))
        return HandleResult.DROP  # Send to DLQ
    except ExternalServiceError as e:
        logger.warning("External service unavailable", error=str(e))
        return HandleResult.RETRY  # Retry later

# Start consuming
consumer.subscribe(["user-events"], group_id="user-processor")
consumer.start(handle_user_event)
```

### Consumer Patterns by Use Case

#### 1. Idempotent Consumer

```python
class IdempotentConsumer:
    """Ensure exactly-once processing semantics."""

    def __init__(self, redis: RedisClient, ttl: int = 86400):
        self._redis = redis
        self._ttl = ttl

    async def handle(self, envelope: Envelope) -> HandleResult:
        # Extract idempotency key from headers or payload
        message_id = envelope.headers.get(H_CORRELATION_ID, b"").decode()
        if not message_id:
            message_id = hashlib.md5(
                json.dumps(envelope.payload, sort_keys=True).encode()
            ).hexdigest()

        # Check if already processed
        dedup_key = f"processed:{message_id}"
        if await self._redis.exists(dedup_key):
            logger.info("Duplicate message, skipping", message_id=message_id)
            return HandleResult.ACK

        try:
            # Process message
            await self._process(envelope.payload)

            # Mark as processed
            await self._redis.set(dedup_key, "1", ttl=self._ttl)
            return HandleResult.ACK

        except Exception as e:
            logger.error("Processing failed", error=str(e))
            return HandleResult.RETRY
```

#### 2. Batch Consumer

```python
class BatchConsumer:
    """Accumulate messages for batch processing."""

    def __init__(self, batch_size: int = 100, flush_interval: float = 5.0):
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._buffer: List[Envelope] = []
        self._last_flush = time.monotonic()

    def handle(self, envelope: Envelope) -> HandleResult:
        self._buffer.append(envelope)

        should_flush = (
            len(self._buffer) >= self._batch_size or
            time.monotonic() - self._last_flush >= self._flush_interval
        )

        if should_flush:
            try:
                self._process_batch(self._buffer)
                self._buffer.clear()
                self._last_flush = time.monotonic()
                return HandleResult.ACK
            except Exception as e:
                logger.error("Batch processing failed", error=str(e))
                return HandleResult.RETRY

        return HandleResult.ACK
```

#### 3. Saga Orchestrator

```python
class DocumentProcessingSaga:
    """Orchestrate multi-step document processing."""

    STEPS = ["parse", "extract", "index", "notify"]

    async def handle(self, envelope: Envelope) -> HandleResult:
        payload = envelope.payload
        current_step = payload.get("step", self.STEPS[0])
        document_id = payload["document_id"]

        try:
            # Execute current step
            if current_step == "parse":
                result = await self._parse_document(document_id)
            elif current_step == "extract":
                result = await self._extract_entities(document_id)
            elif current_step == "index":
                result = await self._index_document(document_id)
            elif current_step == "notify":
                await self._send_notification(document_id)
                return HandleResult.ACK

            # Emit next step
            next_idx = self.STEPS.index(current_step) + 1
            if next_idx < len(self.STEPS):
                await self._emit_next_step(
                    document_id,
                    self.STEPS[next_idx],
                    result,
                )

            return HandleResult.ACK

        except Exception as e:
            await self._handle_saga_failure(document_id, current_step, e)
            return HandleResult.DROP  # Compensate and move to DLQ
```

### Offset Management

```python
# Consumer handles offsets automatically with dual commit strategy

# By count (every N messages)
if processed_since_commit >= commit_every_n:
    consumer.commit()
    processed_since_commit = 0

# By time (every T seconds)
if (now - last_commit) >= commit_interval_ms:
    consumer.commit()
    last_commit = now

# On rebalance (commit before partition revoke)
def on_revoke(partitions):
    for tp in partitions:
        if tp in assignments:
            consumer.commit(offsets=[tp.offset])
```

### Partition Pause/Resume for Delays

```python
# Consumer pauses partition instead of requeuing for retry delays

def _handle_retry_delay(self, partition, offset, delay_until_ms):
    """Pause partition until retry delay expires."""
    tp = TopicPartition(topic, partition)

    # Pause partition
    self._consumer.pause([tp])

    # Seek back to current message
    self._consumer.seek(tp, offset)

    # Schedule resume
    heapq.heappush(self._paused_heap, (delay_until_ms, tp))

def _resume_due_partitions(self):
    """Resume partitions whose delay has expired."""
    now_ms = int(time.time() * 1000)
    while self._paused_heap and self._paused_heap[0][0] <= now_ms:
        _, tp = heapq.heappop(self._paused_heap)
        self._consumer.resume([tp])
```

---

## Serialization

### JSON Serializer (Default)

```python
import json
from typing import Any

class JsonSerializer:
    """JSON serializer with UTF-8 encoding."""

    def dumps(self, obj: Any) -> bytes:
        """Serialize to JSON bytes."""
        return json.dumps(
            obj,
            separators=(",", ":"),  # Compact format
            ensure_ascii=False,      # Support Unicode
        ).encode("utf-8")

    def loads(self, data: bytes) -> Any:
        """Deserialize from JSON bytes."""
        return json.loads(data.decode("utf-8"))
```

### Custom Serializer Protocol

```python
from typing import Protocol

class Serializer(Protocol):
    def dumps(self, obj: Any) -> bytes: ...
    def loads(self, data: bytes) -> Any: ...

# Example: MessagePack serializer
import msgpack

class MsgPackSerializer:
    def dumps(self, obj: Any) -> bytes:
        return msgpack.packb(obj, use_bin_type=True)

    def loads(self, data: bytes) -> Any:
        return msgpack.unpackb(data, raw=False)

# Example: Avro serializer (with schema registry)
class AvroSerializer:
    def __init__(self, schema_registry_url: str, schema: str):
        self._registry = SchemaRegistryClient(schema_registry_url)
        self._schema = parse_schema(schema)

    def dumps(self, obj: Any) -> bytes:
        return self._registry.encode(self._schema, obj)

    def loads(self, data: bytes) -> Any:
        return self._registry.decode(data)
```

---

## Middleware Pipeline

### Middleware Protocol

```python
from typing import Protocol, Optional

class PublishMiddleware(Protocol):
    """Publisher middleware interface."""

    def before_publish(
        self,
        topic: str,
        envelope: Envelope,
    ) -> Envelope:
        """Called before serialization and send."""
        return envelope

    def after_publish(
        self,
        topic: str,
        envelope: Envelope,
        result: PublishResult,
    ) -> None:
        """Called after successful publish."""
        pass

class ConsumeMiddleware(Protocol):
    """Consumer middleware interface."""

    def before_handle(
        self,
        topic: str,
        partition: int,
        offset: int,
        envelope: Envelope,
    ) -> Envelope:
        """Called before handler invocation."""
        return envelope

    def after_handle(
        self,
        topic: str,
        partition: int,
        offset: int,
        envelope: Envelope,
        result: HandleResult,
        exception: Optional[BaseException],
    ) -> None:
        """Called after handler completion."""
        pass
```

### Logging Middleware

```python
import structlog

logger = structlog.get_logger(__name__)

class LoggingMiddleware:
    """Structured logging for messaging operations."""

    def before_publish(self, topic: str, envelope: Envelope) -> Envelope:
        logger.debug(
            "publishing_message",
            topic=topic,
            key=envelope.key.hex() if envelope.key else None,
            headers=list(envelope.headers.keys()),
        )
        return envelope

    def after_publish(
        self,
        topic: str,
        envelope: Envelope,
        result: PublishResult,
    ) -> None:
        logger.info(
            "message_published",
            topic=topic,
            partition=result.partition,
            offset=result.offset,
        )

    def before_handle(
        self,
        topic: str,
        partition: int,
        offset: int,
        envelope: Envelope,
    ) -> Envelope:
        logger.debug(
            "handling_message",
            topic=topic,
            partition=partition,
            offset=offset,
        )
        return envelope

    def after_handle(
        self,
        topic: str,
        partition: int,
        offset: int,
        envelope: Envelope,
        result: HandleResult,
        exception: Optional[BaseException],
    ) -> None:
        if exception:
            logger.error(
                "message_handling_failed",
                topic=topic,
                partition=partition,
                offset=offset,
                error=str(exception),
            )
        else:
            logger.info(
                "message_handled",
                topic=topic,
                partition=partition,
                offset=offset,
                result=result.value,
            )
```

### Metrics Middleware

```python
from prometheus_client import Counter, Histogram
from contextvars import ContextVar

# Metrics
publish_counter = Counter(
    "messaging_publish_total",
    "Total published messages",
    ["topic", "result"],
)
consume_counter = Counter(
    "messaging_consume_total",
    "Total consumed messages",
    ["topic", "result"],
)
publish_latency = Histogram(
    "messaging_publish_latency_ms",
    "Publish latency in milliseconds",
    buckets=(1, 5, 10, 50, 100, 500, 1000),
)
handle_latency = Histogram(
    "messaging_handle_latency_ms",
    "Handle latency in milliseconds",
    buckets=(1, 5, 10, 50, 100, 500, 1000),
)

class MetricsMiddleware:
    """Prometheus metrics for messaging."""

    def __init__(self):
        self._pub_start: ContextVar[Optional[float]] = ContextVar("pub_start", default=None)
        self._con_start: ContextVar[Optional[float]] = ContextVar("con_start", default=None)

    def before_publish(self, topic: str, envelope: Envelope) -> Envelope:
        self._pub_start.set(time.perf_counter())
        return envelope

    def after_publish(
        self,
        topic: str,
        envelope: Envelope,
        result: PublishResult,
    ) -> None:
        start = self._pub_start.get()
        if start:
            elapsed_ms = (time.perf_counter() - start) * 1000
            publish_latency.observe(elapsed_ms)
        publish_counter.labels(topic=topic, result="success").inc()

    def before_handle(self, topic: str, partition: int, offset: int, envelope: Envelope) -> Envelope:
        self._con_start.set(time.perf_counter())
        return envelope

    def after_handle(
        self,
        topic: str,
        partition: int,
        offset: int,
        envelope: Envelope,
        result: HandleResult,
        exception: Optional[BaseException],
    ) -> None:
        start = self._con_start.get()
        if start:
            elapsed_ms = (time.perf_counter() - start) * 1000
            handle_latency.observe(elapsed_ms)
        status = "error" if exception else result.value.lower()
        consume_counter.labels(topic=topic, result=status).inc()
```

### Tracing Middleware

```python
from opentelemetry import trace
from opentelemetry.propagate import inject, extract

tracer = trace.get_tracer(__name__)

class HdrGetter:
    """Extract trace context from Kafka headers."""
    def get(self, carrier: Dict[str, bytes], key: str) -> List[str]:
        value = carrier.get(key)
        if isinstance(value, bytes):
            return [value.decode("utf-8")]
        return []

    def keys(self, carrier: Dict[str, bytes]) -> List[str]:
        return list(carrier.keys())

class HdrSetter:
    """Inject trace context into Kafka headers."""
    def set(self, carrier: Dict[str, bytes], key: str, value: str) -> None:
        carrier[key] = value.encode("utf-8")

class TracingMiddleware:
    """OpenTelemetry distributed tracing."""

    def before_publish(self, topic: str, envelope: Envelope) -> Envelope:
        with tracer.start_as_current_span(
            f"messaging.produce.{topic}",
            kind=trace.SpanKind.PRODUCER,
        ) as span:
            span.set_attribute("messaging.system", "kafka")
            span.set_attribute("messaging.destination", topic)
            # Inject trace context into headers
            inject(envelope.headers, setter=HdrSetter())
        return envelope

    def before_handle(
        self,
        topic: str,
        partition: int,
        offset: int,
        envelope: Envelope,
    ) -> Envelope:
        # Extract trace context from headers
        ctx = extract(envelope.headers, getter=HdrGetter())
        with tracer.start_as_current_span(
            f"messaging.consume.{topic}",
            context=ctx,
            kind=trace.SpanKind.CONSUMER,
        ) as span:
            span.set_attribute("messaging.system", "kafka")
            span.set_attribute("messaging.destination", topic)
            span.set_attribute("messaging.kafka.partition", partition)
            span.set_attribute("messaging.kafka.offset", offset)
        return envelope
```

---

## Retry & Dead Letter Queue

### Retry Topology

```
Original Topic: orders
     ↓ (failure)
orders.retry.5s   (5 second delay)
     ↓ (failure)
orders.retry.1m   (1 minute delay)
     ↓ (failure)
orders.retry.10m  (10 minute delay)
     ↓ (failure)
orders.dlq        (dead letter queue)
```

### Retry Decision Logic

```python
from dataclasses import dataclass
from typing import Optional, Tuple

@dataclass
class RetryDecision:
    """Result of retry analysis."""
    action: str  # "retry" or "dlq"
    topic: str
    delay_ms: int

def next_for_retry(
    current_topic: str,
    retry_config: RetryConfig,
) -> RetryDecision:
    """Determine next retry tier or DLQ."""
    # Parse current topic
    main_topic, layer_idx = _analyze_topic(current_topic, retry_config)

    if layer_idx is None:
        # Original topic - go to first retry layer
        layer = retry_config.layers[0]
        return RetryDecision(
            action="retry",
            topic=f"{main_topic}.{layer.suffix}",
            delay_ms=layer.delay_ms,
        )
    elif layer_idx < len(retry_config.layers) - 1:
        # Current retry layer - go to next
        layer = retry_config.layers[layer_idx + 1]
        return RetryDecision(
            action="retry",
            topic=f"{main_topic}.{layer.suffix}",
            delay_ms=layer.delay_ms,
        )
    else:
        # Exhausted all retries - go to DLQ
        return RetryDecision(
            action="dlq",
            topic=f"{main_topic}.{retry_config.dlq_suffix}",
            delay_ms=0,
        )

def _analyze_topic(
    topic: str,
    retry_config: RetryConfig,
) -> Tuple[str, Optional[int]]:
    """Extract main topic and current retry layer index."""
    for idx, layer in enumerate(retry_config.layers):
        suffix = f".{layer.suffix}"
        if topic.endswith(suffix):
            return topic[:-len(suffix)], idx
    return topic, None
```

### Consumer Retry Handling

```python
def _handle_retry(
    self,
    envelope: Envelope,
    original_topic: str,
    error: Exception,
) -> None:
    """Route message to appropriate retry topic."""
    decision = next_for_retry(original_topic, self._retry_config)

    # Update envelope headers
    attempts = int(envelope.headers.get(H_ATTEMPTS, b"0").decode()) + 1
    envelope.headers[H_ATTEMPTS] = str(attempts).encode()
    envelope.headers[H_ORIGINAL_TOPIC] = original_topic.encode()
    envelope.headers[H_RETRY_NOT_BEFORE] = str(
        int(time.time() * 1000) + decision.delay_ms
    ).encode()

    if decision.action == "dlq":
        envelope.headers[H_ERROR_CLASS] = type(error).__name__.encode()
        envelope.headers[H_ERROR_MESSAGE] = str(error)[:500].encode()

    # Publish to retry/DLQ topic
    self._retry_publisher.publish(decision.topic, envelope)

def _handle_drop(
    self,
    envelope: Envelope,
    original_topic: str,
    error: Exception,
) -> None:
    """Route message directly to DLQ."""
    dlq_topic = f"{original_topic}.{self._retry_config.dlq_suffix}"

    envelope.headers[H_ERROR_CLASS] = type(error).__name__.encode()
    envelope.headers[H_ERROR_MESSAGE] = str(error)[:500].encode()

    self._retry_publisher.publish(dlq_topic, envelope)
```

---

## Error Handling

### Exception Hierarchy

```python
class MessagingError(Exception):
    """Base exception for messaging operations."""
    pass

class SerializationError(MessagingError):
    """Failed to serialize/deserialize message."""
    pass

class PublishError(MessagingError):
    """Failed to publish message."""
    pass

class ConsumeError(MessagingError):
    """Failed to consume message."""
    pass

# Application-level exceptions for handler control flow
class RetryableError(Exception):
    """Error that should trigger message retry."""
    pass

class NonRetryableError(Exception):
    """Error that should send message to DLQ."""
    pass
```

### Handler Exception Mapping

```python
def _invoke_handler(
    self,
    envelope: Envelope,
    handler: Callable[[Envelope], HandleResult],
) -> HandleResult:
    """Invoke handler with exception mapping."""
    try:
        return handler(envelope)
    except RetryableError:
        return HandleResult.RETRY
    except NonRetryableError:
        return HandleResult.DROP
    except Exception as e:
        # Unknown exceptions default to retry (safe)
        logger.exception("Unexpected handler error", error=str(e))
        return HandleResult.RETRY
```

### Error Categories

| Error Type | Action | Example |
|------------|--------|---------|
| Serialization | DROP | Malformed JSON |
| Validation | DROP | Missing required field |
| External service timeout | RETRY | Database unavailable |
| Rate limit | RETRY | API rate limited |
| Business rule violation | DROP | Invalid state transition |
| Unknown | RETRY | Unexpected exception |

---

## Distributed Tracing

### Complete Trace Flow

```
[Producer Service]
       │
       │ ← Start span "messaging.produce.orders"
       │ ← Inject traceparent into headers
       │
       ▼
   ┌─────────┐
   │  Kafka  │
   └─────────┘
       │
       │ ← Extract traceparent from headers
       │ ← Start span "messaging.consume.orders" (child)
       │
       ▼
[Consumer Service]
       │
       │ ← Start span "process_order" (child)
       │
       ▼
[Database/External]
```

### Correlation ID Propagation

```python
# Publisher: Set correlation ID
correlation_id = str(uuid.uuid4())
envelope = Envelope(
    payload=data,
    headers={H_CORRELATION_ID: correlation_id.encode()},
)

# Consumer: Extract and propagate
def handle(envelope: Envelope) -> HandleResult:
    corr_id = envelope.headers.get(H_CORRELATION_ID, b"").decode()

    with structlog.contextvars.bind_contextvars(correlation_id=corr_id):
        # All logs in this scope include correlation_id
        process_message(envelope.payload)

    return HandleResult.ACK
```

---

## Testing Patterns

### Unit Testing Handlers

```python
import pytest
from unittest.mock import Mock, patch

@pytest.fixture
def sample_envelope():
    return Envelope(
        payload={"user_id": "123", "action": "created"},
        key=b"user-123",
    )

def test_handler_success(sample_envelope):
    """Test successful message handling."""
    handler = UserEventHandler(user_service=Mock())

    result = handler.handle(sample_envelope)

    assert result == HandleResult.ACK

def test_handler_retry_on_external_failure(sample_envelope):
    """Test retry on external service failure."""
    mock_service = Mock()
    mock_service.process.side_effect = ExternalServiceError("timeout")
    handler = UserEventHandler(user_service=mock_service)

    result = handler.handle(sample_envelope)

    assert result == HandleResult.RETRY

def test_handler_drop_on_validation_error(sample_envelope):
    """Test DLQ on validation failure."""
    sample_envelope.payload = {"invalid": "data"}
    handler = UserEventHandler(user_service=Mock())

    result = handler.handle(sample_envelope)

    assert result == HandleResult.DROP
```

### Integration Testing with Test Containers

```python
import pytest
from testcontainers.kafka import KafkaContainer

@pytest.fixture(scope="session")
def kafka_container():
    with KafkaContainer() as kafka:
        yield kafka

@pytest.fixture
def kafka_config(kafka_container):
    return KafkaConfig(
        bootstrap_servers=kafka_container.get_bootstrap_server(),
        client_id="test-client",
    )

@pytest.mark.integration
async def test_publish_and_consume(kafka_config):
    """Test end-to-end message flow."""
    publisher = create_publisher(kafka_config, JsonSerializer())
    consumer = create_consumer(kafka_config, JsonSerializer())

    received = []
    def handler(env):
        received.append(env.payload)
        return HandleResult.ACK

    consumer.subscribe(["test-topic"], group_id="test-group")
    # Start consumer in background
    consumer_task = asyncio.create_task(consumer.start(handler))

    # Publish message
    publisher.publish("test-topic", Envelope(payload={"test": "data"}))

    # Wait for consumption
    await asyncio.sleep(2)
    consumer.stop()

    assert len(received) == 1
    assert received[0] == {"test": "data"}
```

### Mock Publisher for Unit Tests

```python
from dataclasses import dataclass, field
from typing import List

@dataclass
class MockPublisher:
    """In-memory publisher for testing."""
    messages: List[tuple] = field(default_factory=list)

    def publish(self, topic: str, envelope: Envelope) -> PublishResult:
        self.messages.append((topic, envelope))
        return PublishResult(topic=topic, partition=0, offset=len(self.messages))

    def publish_many(self, topic: str, envelopes: List[Envelope]) -> List[PublishResult]:
        return [self.publish(topic, env) for env in envelopes]

    def close(self) -> None:
        pass

    def assert_published(self, topic: str, count: int = 1):
        actual = len([t for t, _ in self.messages if t == topic])
        assert actual == count, f"Expected {count} messages to {topic}, got {actual}"
```

---

## Anti-Patterns

### ❌ Synchronous Processing in Consumer

```python
# ❌ BAD: Blocking call in async consumer
def handle(envelope: Envelope) -> HandleResult:
    requests.post(url, json=envelope.payload)  # Blocks event loop!
    return HandleResult.ACK

# ✅ GOOD: Use async or thread pool
async def handle(envelope: Envelope) -> HandleResult:
    async with httpx.AsyncClient() as client:
        await client.post(url, json=envelope.payload)
    return HandleResult.ACK
```

### ❌ Ignoring Serialization Errors

```python
# ❌ BAD: Silent failure
def handle(envelope: Envelope) -> HandleResult:
    try:
        data = envelope.payload
    except:
        return HandleResult.ACK  # Message lost!

# ✅ GOOD: Route to DLQ
def handle(envelope: Envelope) -> HandleResult:
    try:
        data = validate_payload(envelope.payload)
    except ValidationError:
        return HandleResult.DROP  # Goes to DLQ for investigation
```

### ❌ Unbounded Retries

```python
# ❌ BAD: Infinite retry loop
def handle(envelope: Envelope) -> HandleResult:
    while True:
        try:
            process(envelope.payload)
            return HandleResult.ACK
        except:
            time.sleep(1)  # Infinite loop on persistent failure

# ✅ GOOD: Use retry tiers with DLQ
def handle(envelope: Envelope) -> HandleResult:
    try:
        process(envelope.payload)
        return HandleResult.ACK
    except RetryableError:
        return HandleResult.RETRY  # Consumer handles retry topology
```

### ❌ Auto-Commit Without Idempotency

```python
# ❌ BAD: Auto-commit can cause message loss
consumer_config = ConsumerTuning(enable_auto_commit=True)

# ✅ GOOD: Manual commit with idempotent processing
consumer_config = ConsumerTuning(
    enable_auto_commit=False,
    commit_every_n=100,
)
# Plus: Implement idempotency in handler
```

### ❌ Missing Key for Ordered Processing

```python
# ❌ BAD: No partition key - random partition
envelope = Envelope(payload={"user_id": 123, "action": "update"})

# ✅ GOOD: Key ensures ordering per entity
envelope = Envelope(
    payload={"user_id": 123, "action": "update"},
    key=b"user-123",  # All user-123 events go to same partition
)
```

### ❌ Large Messages

```python
# ❌ BAD: Embedding large data in message
envelope = Envelope(payload={"file_content": base64_encoded_10mb_file})

# ✅ GOOD: Store data externally, send reference
await s3.upload(file_content, key=file_key)
envelope = Envelope(payload={"file_key": file_key, "bucket": "files"})
```

---

## Quick Reference

### Common Configuration Values

| Setting | Development | Production |
|---------|-------------|------------|
| `acks` | `1` | `all` |
| `enable_idempotence` | `false` | `true` |
| `compression_type` | `none` | `zstd` |
| `enable_auto_commit` | `false` | `false` |
| `max_poll_interval_ms` | `60000` | `300000` |
| `session_timeout_ms` | `10000` | `45000` |

### Troubleshooting

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| Consumer lag increasing | Slow handler | Profile handler, use batch processing |
| Duplicate messages | Rebalance during processing | Implement idempotency |
| Message loss | Auto-commit before processing | Use manual commits |
| Producer timeouts | Backpressure | Increase batch size, add more partitions |
| Offset commit failures | Session timeout | Increase session timeout |

---

## Related Documentation

- [Architecture Overview](architecture-overview.md)
- [Async & Errors](async-and-errors.md)
- [Testing Guide](testing-guide.md)
- [Celery Patterns](celery-patterns.md)
