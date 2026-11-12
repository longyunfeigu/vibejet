"""Pytest bootstrap and shared fixtures.

- Sets mandatory environment variables before collection (SECRET_KEY must pass the
  weak-value / length checks in Settings).
- Skips collecting test modules whose optional extra isn't installed.
- Provides in-memory SQLite engine/session fixtures shared by repository tests.
"""

import importlib.util
import os
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

import pytest
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

# Mandatory secret key for settings validation (must pass weak-value + min-length checks)
os.environ.setdefault("SECRET_KEY", "unit-test-only-secret-key-0123456789abcdef")

# Modules that need an optional extra at import time (via grpc_app / the provider under test),
# so pytest.importorskip can't guard them; skip collecting them when the extra isn't installed.
_OPTIONAL_EXTRA_MODULES = {
    "test_grpc_interceptors.py": "grpc",
    "test_s3_provider_upload.py": "botocore",
}
collect_ignore = [
    path
    for path, module in _OPTIONAL_EXTRA_MODULES.items()
    if importlib.util.find_spec(module) is None
]


# ---------------------------------------------------------------------------
# In-memory SQLite (aiosqlite + StaticPool) for repository / UoW tests
#
# The fixtures return async context managers (rather than being async fixtures) so a test can
# open several independent databases, or pass its own metadata, inside one test body.
# ---------------------------------------------------------------------------


@pytest.fixture
def sqlite_engine() -> Callable[..., AbstractAsyncContextManager[AsyncEngine]]:
    """``async with sqlite_engine(metadata=None) as engine`` -> fresh in-memory SQLite.

    Tables are created from ``metadata`` (default: the app's ``Base.metadata``);
    the engine is disposed when the block exits.
    """

    @asynccontextmanager
    async def _engine(metadata: MetaData | None = None) -> AsyncIterator[AsyncEngine]:
        if metadata is None:
            # Lazy import: app modules read settings, which need SECRET_KEY set above.
            from infrastructure.models import Base

            metadata = Base.metadata
        engine = create_async_engine(
            "sqlite+aiosqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        try:
            async with engine.begin() as conn:
                await conn.run_sync(metadata.create_all)
            yield engine
        finally:
            await engine.dispose()

    return _engine


@pytest.fixture
def sqlite_session(sqlite_engine) -> Callable[..., AbstractAsyncContextManager[AsyncSession]]:
    """``async with sqlite_session(metadata=None) as session`` -> AsyncSession
    (expire_on_commit=False) on a fresh in-memory SQLite; engine disposed on exit."""

    @asynccontextmanager
    async def _session(metadata: MetaData | None = None) -> AsyncIterator[AsyncSession]:
        async with sqlite_engine(metadata) as engine:
            async with async_sessionmaker(engine, expire_on_commit=False)() as session:
                yield session

    return _session
