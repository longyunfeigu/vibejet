# input: core.config.settings, api 路由/中间件, infrastructure 外部客户端生命周期
# output: FastAPI app（REST 入口，composition root）
# owner: wanhua.gu
# pos: 应用入口 - 中间件/路由/异常处理装配 + lifespan 资源生命周期；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""FastAPI应用主入口（composition root）。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.docs import register_docs
from api.middleware import LoggingMiddleware, PrometheusMiddleware, RequestIDMiddleware
from api.middleware.locale import LocaleMiddleware
from api.routes import auth as auth_routes
from api.routes import chat as chat_routes
from api.routes import conversations as conversations_routes
from api.routes import documents as documents_routes
from api.routes import files as files_routes
from api.routes import health as health_routes
from api.routes import metrics as metrics_routes
from api.routes import storage as storage_routes
from core.config import settings
from core.exceptions import register_exception_handlers
from core.i18n import t
from core.logging_config import configure_logging, get_logger
from core.observability import tracing as tracing_obs
from core.response import success_response
from infrastructure.database import upgrade_schema_to_head
from infrastructure.external.cache import init_redis_client, shutdown_redis_client
from infrastructure.external.llm import get_llm_client, init_llm_client, shutdown_llm_client
from infrastructure.external.parsing import init_parser
from infrastructure.external.storage import (
    get_storage_client,
    get_storage_config,
    init_storage_client,
    shutdown_storage_client,
)

# 初始化日志：在入口处显式配置，避免模块导入时的副作用
configure_logging()
logger = get_logger(__name__)


async def _init_optional(name: str, *, required: bool, initializer) -> None:
    """初始化一个可选外部依赖。

    required=True 时初始化失败直接抛出（fail-fast），
    否则降级为 error 日志并继续启动。
    """
    try:
        await initializer()
    except Exception as exc:
        if required:
            logger.error(f"{name}_init_failed", error=str(exc), required=True)
            raise
        logger.error(f"{name}_init_failed", error=str(exc), required=False)


def _setup_tracing(app: FastAPI) -> None:
    try:
        tracing_obs.setup_tracing(
            service_name=settings.PROJECT_NAME,
            exporter=settings.tracing.exporter,
            otlp_endpoint=settings.tracing.otlp_endpoint,
            sample_rate=settings.tracing.sample_rate,
        )
        tracing_obs.instrument_app(app)
        logger.info("tracing_initialized", exporter=settings.tracing.exporter)
    except Exception as exc:
        logger.warning("tracing_init_failed", error=str(exc))


async def _migrate_schema() -> None:
    # 数据库 schema 单轨制：只认 Alembic 迁移（开发环境可设 AUTO_RUN_MIGRATIONS=true）
    if settings.AUTO_RUN_MIGRATIONS:
        await upgrade_schema_to_head()
        logger.info("database_migrated", message="Alembic upgraded to head at startup")
    else:
        logger.info(
            "database_migrations_required",
            message="Auto migration disabled; run `alembic upgrade head` before startup",
        )


async def _init_storage() -> None:
    await init_storage_client()
    config = get_storage_config()
    logger.info(
        "storage_initialized",
        message="Storage service initialized",
        provider=config.type,
        bucket=config.bucket,
    )
    storage = get_storage_client()
    if storage and await storage.health_check():
        logger.info("storage_health_check_passed", message="Storage health check passed")


async def _init_llm() -> None:
    await init_llm_client()
    if settings.llm.required and get_llm_client() is None:
        raise RuntimeError("LLM__REQUIRED=true but LLM client not configured (LLM__API_KEY)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    if settings.tracing.enabled:
        _setup_tracing(app)

    await _migrate_schema()

    if settings.redis.url:
        await _init_optional(
            "redis_cache", required=settings.redis.required, initializer=init_redis_client
        )
    await _init_optional("storage", required=settings.storage.required, initializer=_init_storage)
    await _init_optional("llm", required=settings.llm.required, initializer=_init_llm)
    await _init_optional(
        "document_parser", required=settings.document.required, initializer=init_parser
    )

    yield
    # 关闭时的清理工作
    await shutdown_llm_client()
    logger.info("llm_shutdown", message="LLM client shutdown")
    if settings.redis.url:
        await shutdown_redis_client()
        logger.info("redis_cache_shutdown", message="Redis cache shutdown")

    # 关闭存储服务
    await shutdown_storage_client()
    logger.info("storage_shutdown", message="Storage service shutdown")
    if settings.tracing.enabled:
        tracing_obs.shutdown_tracing()
    logger.info("application_shutdown", message="Application shutdown")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
    description="基于DDD架构的FastAPI模板",
    docs_url=None,  # 使用自定义 Swagger UI 以支持国际化（见 api/docs.py）
    redoc_url="/redoc",
)

# 添加中间件（注意顺序：从下往上执行）
# 1. Request ID中间件（最先执行，为后续中间件提供request_id）
app.add_middleware(RequestIDMiddleware)

# 2. 日志中间件（依赖request_id）
app.add_middleware(LoggingMiddleware)

# 2.5 语言中间件（解析 locale）
app.add_middleware(LocaleMiddleware)

# 3. CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# 4. Prometheus metrics middleware (optional)
if settings.metrics.enabled:
    app.add_middleware(PrometheusMiddleware)

# 注册全局异常处理器
register_exception_handlers(app)

# 注册自定义 Swagger UI（/docs）
register_docs(app)

# 注册路由
app.include_router(auth_routes.router, prefix="/api/v1")
app.include_router(storage_routes.router, prefix="/api/v1")
app.include_router(files_routes.router, prefix="/api/v1")
app.include_router(conversations_routes.router, prefix="/api/v1")
app.include_router(documents_routes.router, prefix="/api/v1")
app.include_router(chat_routes.router, prefix="/api/v1")
app.include_router(health_routes.router)
app.include_router(metrics_routes.router)


# 根路径
@app.get("/", tags=["Root"])
async def root():
    """API根路径"""
    return success_response(
        data={
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "docs": "/docs",
            "redoc": "/redoc",
        },
        message=t("welcome"),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        workers=1 if settings.RELOAD else settings.WORKERS,
        log_level="debug" if settings.DEBUG else "info",
    )
