"""
数据库配置和连接管理
"""

import asyncio
import os
from pathlib import Path
from typing import Any, AsyncGenerator

from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from alembic import command
from alembic.config import Config
from core.config import settings
from core.logging_config import get_logger
from infrastructure.models import Base

_pool_logger = get_logger("infrastructure.database.pool")


# 创建异步引擎
def _build_async_url(database_url: str) -> str:
    """确保数据库URL使用异步驱动"""
    url = make_url(database_url)
    drivername = url.drivername

    if "+" in drivername:
        return database_url

    driver_map = {
        "postgresql": "postgresql+asyncpg",
        "postgres": "postgresql+asyncpg",
        "mysql": "mysql+aiomysql",
        "sqlite": "sqlite+aiosqlite",
    }

    if drivername not in driver_map:
        raise ValueError(
            f"不支持的数据库驱动: {drivername}. 请使用 async 驱动或更新数据库连接字符串"
        )

    async_driver = driver_map[drivername]
    return str(url.set(drivername=async_driver))


def _engine_kwargs(async_url: str) -> dict[str, Any]:
    """构造引擎参数：池配置只对网络型数据库下发。

    SQLite（本地文件/内存，dev/test 路径）保持 SQLAlchemy 默认池行为——
    pre_ping/recycle/池容量对本地文件库没有意义。
    """
    kwargs: dict[str, Any] = {"echo": settings.DEBUG, "future": True}
    if not make_url(async_url).drivername.startswith("sqlite"):
        db = settings.database
        kwargs.update(
            pool_pre_ping=db.pool_pre_ping,
            pool_recycle=db.pool_recycle,
            pool_size=db.pool_size,
            max_overflow=db.max_overflow,
            pool_timeout=db.pool_timeout,
        )
    return kwargs


_async_url = _build_async_url(settings.database.url)
engine = create_async_engine(_async_url, **_engine_kwargs(_async_url))


# 池健康可观测分工：利用率/容量走既有 Prometheus gauges
# （core/observability/metrics.collect_db_pool_metrics，经 /metrics 拉取），
# 这里只补事件型信号——invalidate 意味着连接被判死（服务端掐断/故障切换），
# 属 WARNING 级异常事件。不挂 checkout/checkin 监听：那是每请求两次的最热路径，
# 任何 eager 求值的日志参数都会变成常态开销。
@event.listens_for(engine.sync_engine, "invalidate")
def _on_pool_invalidate(dbapi_connection, connection_record, exception) -> None:
    _pool_logger.warning(
        "db_connection_invalidated",
        error=str(exception) if exception else None,
    )


# 创建异步会话工厂 (SQLAlchemy 1.4 兼容)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话（不自动提交，由调用方控制事务）

    使用异步上下文管理器自动关闭会话，无需显式 close。
    """
    async with AsyncSessionLocal() as session:
        yield session


async def create_tables():
    """
    创建所有表（仅供测试使用）

    生产/开发启动路径只走 Alembic 迁移（见 main.py lifespan）。
    这里直接 create_all 会绕过迁移版本管理，导致 schema 双轨漂移。
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables():
    """
    删除所有表

    警告：仅用于测试环境，会删除所有数据！
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def _run_alembic_upgrade_to_head() -> None:
    """同步执行 Alembic 迁移到最新版本。"""
    project_root = Path(__file__).resolve().parent.parent
    alembic_ini_path = project_root / "alembic.ini"
    alembic_script_path = project_root / "alembic"

    alembic_config = Config(str(alembic_ini_path))
    alembic_config.set_main_option("script_location", str(alembic_script_path))

    # 确保 env.py 能读取到当前进程的数据库配置
    os.environ["DATABASE__URL"] = settings.database.url
    command.upgrade(alembic_config, "head")


async def upgrade_schema_to_head() -> None:
    """在线程池中执行 Alembic，避免阻塞事件循环。"""
    await asyncio.to_thread(_run_alembic_upgrade_to_head)
