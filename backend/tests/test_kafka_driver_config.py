from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, cast

import pytest
from pydantic import ValidationError

from core.config import KafkaSettings, Settings
from infrastructure.external.messaging.config import KafkaConfig, MessagingConfig
from infrastructure.external.messaging.config_builder import messaging_config_from_settings
from infrastructure.external.messaging.factory import create_consumer, create_publisher
from infrastructure.external.messaging.providers.aiokafka.consumer import AiokafkaConsumer
from infrastructure.external.messaging.providers.aiokafka.publisher import AiokafkaPublisher
from infrastructure.external.messaging.serializers.json import JsonSerializer

# 通过弱值/长度校验的合法测试密钥
VALID_SECRET = "unit-test-only-secret-key-0123456789abcdef"


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", VALID_SECRET)
    monkeypatch.delenv("KAFKA__DRIVER", raising=False)


def test_driver_defaults_to_aiokafka() -> None:
    assert Settings(_env_file=None).kafka.driver == "aiokafka"


def test_env_file_with_aiokafka_driver_still_starts(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(f"SECRET_KEY={VALID_SECRET}\nKAFKA__DRIVER=aiokafka\n", encoding="utf-8")

    assert Settings(_env_file=str(env_file)).kafka.driver == "aiokafka"


@pytest.mark.parametrize("value", ["confluent", "Confluent", " confluent "])
def test_confluent_driver_is_rejected_with_migration_hint(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("KAFKA__DRIVER", value)

    with pytest.raises(ValidationError) as excinfo:
        Settings(_env_file=None)

    message = str(excinfo.value)
    assert "kafka.driver" in message
    assert f"KAFKA__DRIVER={value!r} 不受支持" in message
    assert "confluent-kafka 驱动已移除" in message
    assert "请改为 KAFKA__DRIVER=aiokafka" in message


def test_confluent_driver_in_env_file_fails_at_startup(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(f"SECRET_KEY={VALID_SECRET}\nKAFKA__DRIVER=confluent\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="confluent-kafka 驱动已移除"):
        Settings(_env_file=str(env_file))


# 以前这些值都会落到 confluent 驱动；现在只认精确的 "aiokafka"，不新增大小写/空格变体
@pytest.mark.parametrize("value", ["AIOKAFKA", " aiokafka ", "kafka", "kafka-python", ""])
def test_every_other_driver_value_gets_the_same_migration_hint(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("KAFKA__DRIVER", value)

    with pytest.raises(ValidationError) as excinfo:
        Settings(_env_file=None)

    message = str(excinfo.value)
    assert f"KAFKA__DRIVER={value!r} 不受支持" in message
    assert "请改为 KAFKA__DRIVER=aiokafka" in message
    assert "Input should be" not in message  # 不是裸的 Literal 报错


def test_builder_produces_aiokafka_config() -> None:
    cfg = messaging_config_from_settings(KafkaSettings(bootstrap_servers="kafka:9092"))

    assert cfg.provider == "kafka"
    assert cfg.kafka.driver == "aiokafka"
    assert cfg.kafka.bootstrap_servers == "kafka:9092"


def test_builder_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="Unsupported provider: rabbitmq"):
        messaging_config_from_settings(KafkaSettings(provider="rabbitmq"))


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "retry.1s:1000,broken,retry.x:abc, retry.2s:2000 ",
            [("retry.1s", 1000), ("retry.2s", 2000)],
        ),
        ("broken,also-broken", [("retry.5s", 5000), ("retry.1m", 60000), ("retry.10m", 600000)]),
        (None, [("retry.5s", 5000), ("retry.1m", 60000), ("retry.10m", 600000)]),
    ],
)
def test_builder_skips_malformed_retry_layers(
    raw: str | None, expected: list[tuple[str, int]]
) -> None:
    cfg = messaging_config_from_settings(KafkaSettings(retry_layers=raw))

    assert [(layer.suffix, layer.delay_ms) for layer in cfg.retry.layers] == expected


def test_create_consumer_returns_aiokafka_consumer() -> None:
    pytest.importorskip("aiokafka")

    assert isinstance(create_consumer(MessagingConfig(), JsonSerializer()), AiokafkaConsumer)


def test_create_publisher_returns_aiokafka_publisher(monkeypatch: pytest.MonkeyPatch) -> None:
    aiokafka = pytest.importorskip("aiokafka")

    class _FakeProducer:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

        async def start(self) -> None:
            return None

        async def stop(self) -> None:
            return None

    monkeypatch.setattr(aiokafka, "AIOKafkaProducer", _FakeProducer)

    publisher = create_publisher(MessagingConfig(), JsonSerializer())
    try:
        assert isinstance(publisher, AiokafkaPublisher)
    finally:
        publisher.close()


@pytest.mark.parametrize("factory", [create_publisher, create_consumer])
def test_factory_rejects_non_aiokafka_driver(factory: Callable[..., Any]) -> None:
    cfg = MessagingConfig(kafka=KafkaConfig(driver=cast(Any, "confluent")))

    with pytest.raises(ValueError, match="only 'aiokafka' is supported"):
        factory(cfg, JsonSerializer())


@pytest.mark.parametrize("factory", [create_publisher, create_consumer])
def test_factory_rejects_unknown_provider(factory: Callable[..., Any]) -> None:
    cfg = MessagingConfig(provider=cast(Any, "rabbitmq"))

    with pytest.raises(ValueError, match="Unsupported provider: rabbitmq"):
        factory(cfg, JsonSerializer())
