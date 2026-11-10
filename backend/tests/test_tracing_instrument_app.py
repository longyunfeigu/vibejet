# input: core.observability.tracing.instrument_app + sys.modules 中替换的假 instrumentor / 数据库模块
# output: instrument_app 特征测试：无 OTel 返回 False、幂等、四个 instrumentor 按序执行、单个失败只记 warning 不中断
# pos: 后端测试 - 可观测性 tracing 装配行为基线（重构前后行为一致的保护网）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Characterization tests for core.observability.tracing.instrument_app."""

from __future__ import annotations

import sys
import types
from typing import Any, Callable, Iterator

import pytest
import structlog
from fastapi import FastAPI
from structlog.testing import capture_logs

from core.observability import tracing

FASTAPI_MOD = "opentelemetry.instrumentation.fastapi"
HTTPX_MOD = "opentelemetry.instrumentation.httpx"
REDIS_MOD = "opentelemetry.instrumentation.redis"
SQLALCHEMY_MOD = "opentelemetry.instrumentation.sqlalchemy"
DATABASE_MOD = "infrastructure.database"

STEPS = ["fastapi", "httpx", "redis", "sqlalchemy"]

Calls = list[tuple[str, Any]]


@pytest.fixture
def logs(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[dict[str, Any]]]:
    """捕获 tracing 日志；换成新的 lazy logger，避免 cache_logger_on_first_use 绕过捕获。"""
    with capture_logs() as captured:
        monkeypatch.setattr(tracing, "logger", structlog.get_logger(tracing.__name__))
        yield captured


def _module(name: str, **attrs: Any) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__dict__.update(attrs)
    return module


@pytest.fixture
def install(monkeypatch: pytest.MonkeyPatch) -> Callable[..., tuple[Calls, Any]]:
    """把四个 instrumentor 和数据库模块换成记录调用的假模块；`failing` 中的步骤在 instrument 时抛错。"""
    monkeypatch.setattr(tracing, "HAS_OTEL", True)
    monkeypatch.setattr(tracing, "_instrumented", False)

    def _install(failing: frozenset[str] = frozenset()) -> tuple[Calls, Any]:
        calls: Calls = []
        engine = types.SimpleNamespace(sync_engine=object())

        def record(step: str, value: Any) -> None:
            if step in failing:
                raise RuntimeError(f"{step} broke")
            calls.append((step, value))

        class FastAPIInstrumentor:
            @staticmethod
            def instrument_app(app: Any) -> None:
                record("fastapi", app)

        class HTTPXClientInstrumentor:
            def instrument(self, **kwargs: Any) -> None:
                record("httpx", kwargs)

        class RedisInstrumentor:
            def instrument(self, **kwargs: Any) -> None:
                record("redis", kwargs)

        class SQLAlchemyInstrumentor:
            def instrument(self, **kwargs: Any) -> None:
                record("sqlalchemy", kwargs)

        fakes = {
            FASTAPI_MOD: _module(FASTAPI_MOD, FastAPIInstrumentor=FastAPIInstrumentor),
            HTTPX_MOD: _module(HTTPX_MOD, HTTPXClientInstrumentor=HTTPXClientInstrumentor),
            REDIS_MOD: _module(REDIS_MOD, RedisInstrumentor=RedisInstrumentor),
            SQLALCHEMY_MOD: _module(SQLALCHEMY_MOD, SQLAlchemyInstrumentor=SQLAlchemyInstrumentor),
            DATABASE_MOD: _module(DATABASE_MOD, engine=engine),
        }
        for name, module in fakes.items():
            monkeypatch.setitem(sys.modules, name, module)
        return calls, engine

    return _install


def test_returns_false_without_opentelemetry(
    install: Callable[..., tuple[Calls, Any]],
    monkeypatch: pytest.MonkeyPatch,
    logs: list[dict[str, Any]],
) -> None:
    calls, _ = install()
    monkeypatch.setattr(tracing, "HAS_OTEL", False)

    assert tracing.instrument_app(FastAPI()) is False
    assert calls == []
    assert tracing._instrumented is False
    assert logs == []


def test_returns_true_without_reinstrumenting_when_already_done(
    install: Callable[..., tuple[Calls, Any]],
    monkeypatch: pytest.MonkeyPatch,
    logs: list[dict[str, Any]],
) -> None:
    calls, _ = install()
    monkeypatch.setattr(tracing, "_instrumented", True)

    assert tracing.instrument_app(FastAPI()) is True
    assert calls == []
    assert logs == []


def test_instruments_everything_in_order_once(
    install: Callable[..., tuple[Calls, Any]], logs: list[dict[str, Any]]
) -> None:
    calls, engine = install()
    app = FastAPI()

    assert tracing.instrument_app(app) is True
    assert tracing.instrument_app(app) is True

    assert calls == [
        ("fastapi", app),
        ("httpx", {}),
        ("redis", {}),
        ("sqlalchemy", {"engine": engine.sync_engine}),
    ]
    assert tracing._instrumented is True
    assert logs == []


@pytest.mark.parametrize("broken", STEPS)
def test_single_instrumentor_failure_is_logged_and_skipped(
    broken: str, install: Callable[..., tuple[Calls, Any]], logs: list[dict[str, Any]]
) -> None:
    calls, _ = install(failing=frozenset({broken}))

    assert tracing.instrument_app(FastAPI()) is True

    assert [step for step, _ in calls] == [step for step in STEPS if step != broken]
    assert logs == [
        {
            "event": f"{broken}_instrumentation_failed",
            "log_level": "warning",
            "error": f"{broken} broke",
        }
    ]
    assert tracing._instrumented is True


@pytest.mark.parametrize(
    "missing_module, broken",
    [
        (FASTAPI_MOD, "fastapi"),
        (HTTPX_MOD, "httpx"),
        (REDIS_MOD, "redis"),
        (SQLALCHEMY_MOD, "sqlalchemy"),
        (DATABASE_MOD, "sqlalchemy"),
    ],
)
def test_missing_module_is_logged_and_skipped(
    missing_module: str,
    broken: str,
    install: Callable[..., tuple[Calls, Any]],
    monkeypatch: pytest.MonkeyPatch,
    logs: list[dict[str, Any]],
) -> None:
    calls, _ = install()
    monkeypatch.setitem(sys.modules, missing_module, None)

    assert tracing.instrument_app(FastAPI()) is True

    assert [step for step, _ in calls] == [step for step in STEPS if step != broken]
    assert len(logs) == 1
    assert logs[0]["event"] == f"{broken}_instrumentation_failed"
    assert logs[0]["log_level"] == "warning"
    assert missing_module in logs[0]["error"]


def test_all_failures_still_mark_app_instrumented(
    install: Callable[..., tuple[Calls, Any]], logs: list[dict[str, Any]]
) -> None:
    calls, _ = install(failing=frozenset(STEPS))

    assert tracing.instrument_app(FastAPI()) is True

    assert calls == []
    assert [entry["event"] for entry in logs] == [
        f"{step}_instrumentation_failed" for step in STEPS
    ]
    # 现状：即便全部失败也标记为已装配，之后的调用不会重试
    assert tracing._instrumented is True
