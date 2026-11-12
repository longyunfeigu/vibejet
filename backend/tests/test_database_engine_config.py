"""Engine kwargs tests: pool settings apply to network databases, not SQLite."""

from __future__ import annotations

from core.config import settings
from infrastructure.database import _build_async_url, _engine_kwargs


def test_network_database_gets_pool_configuration() -> None:
    kwargs = _engine_kwargs("postgresql+asyncpg://u:p@localhost/db")
    assert kwargs["pool_pre_ping"] is settings.database.pool_pre_ping
    assert kwargs["pool_recycle"] == settings.database.pool_recycle
    assert kwargs["pool_size"] == settings.database.pool_size
    assert kwargs["max_overflow"] == settings.database.max_overflow
    assert kwargs["pool_timeout"] == settings.database.pool_timeout


def test_sqlite_keeps_default_pool_behaviour() -> None:
    kwargs = _engine_kwargs("sqlite+aiosqlite:///./app.db")
    for key in ("pool_pre_ping", "pool_recycle", "pool_size", "max_overflow", "pool_timeout"):
        assert key not in kwargs


def test_build_async_url_upgrades_sync_drivers() -> None:
    assert _build_async_url("postgresql://u:p@h/db").startswith("postgresql+asyncpg://")
    assert _build_async_url("sqlite:///./app.db").startswith("sqlite+aiosqlite://")
