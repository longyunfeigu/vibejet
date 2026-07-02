# input: core.config.Settings + monkeypatch 环境变量
# output: Settings 校验行为测试（别名/未知键/SECRET_KEY 弱值与长度/DEBUG 默认与生产互斥）
# pos: 后端测试 - 配置启动期 fail-fast 校验验证；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from core.config import Settings

# 通过弱值/长度校验的合法测试密钥
VALID_SECRET = "unit-test-only-secret-key-0123456789abcdef"


def test_settings_accepts_app_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", VALID_SECRET)
    monkeypatch.setenv("APP_NAME", "kit-service")
    monkeypatch.setenv("APP_VERSION", "9.9.9")

    settings = Settings(_env_file=None)

    assert settings.PROJECT_NAME == "kit-service"
    assert settings.VERSION == "9.9.9"


def test_settings_rejects_unknown_env_keys(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("APP_VERSION", raising=False)
    monkeypatch.setenv("SECRET_KEY", VALID_SECRET)

    env_file = tmp_path / ".env"
    env_file.write_text(f"SECRET_KEY={VALID_SECRET}\nUNKNOWN_KEY=oops\n", encoding="utf-8")

    with pytest.raises(ValidationError):
        Settings(_env_file=str(env_file))


def test_settings_rejects_missing_secret_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(_env_file=None)


@pytest.mark.parametrize(
    "weak_value",
    [
        "your-secret-key-here",
        "your-secret-key-here-change-in-production",
        "CHANGEME",  # 大小写不敏感
    ],
)
def test_settings_rejects_known_weak_secret_key(
    monkeypatch: pytest.MonkeyPatch, weak_value: str
) -> None:
    monkeypatch.setenv("SECRET_KEY", weak_value)

    with pytest.raises(ValidationError, match="弱默认值|长度不足"):
        Settings(_env_file=None)


def test_settings_rejects_short_secret_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "a" * 31)

    with pytest.raises(ValidationError, match="长度不足"):
        Settings(_env_file=None)


def test_settings_debug_defaults_to_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", VALID_SECRET)
    monkeypatch.delenv("DEBUG", raising=False)

    settings = Settings(_env_file=None)

    assert settings.DEBUG is False


def test_settings_rejects_debug_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", VALID_SECRET)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEBUG", "true")

    with pytest.raises(ValidationError, match="production"):
        Settings(_env_file=None)


def test_settings_allows_debug_in_development(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", VALID_SECRET)
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DEBUG", "true")

    settings = Settings(_env_file=None)

    assert settings.DEBUG is True
