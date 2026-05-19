# 异步模式与错误处理 - FastAPI/Python 最佳实践

Python/FastAPI 落地方案，覆盖并发、超时/取消、全局异常映射、Sentry 集成、结构化日志与常见陷阱。

## 目录

- 异步最佳实践（数据库/HTTP/CPU 任务）
- 并发与集合操作（gather/all_settled）
- 超时与取消控制（asyncio/anyio）
- 后台任务与“fire-and-forget”安全姿势
- 自定义异常与全局异常处理器
- 请求校验错误与统一响应包
- 日志/追踪（request-id）与 Sentry 集成
- 常见陷阱与规避

---

## 异步最佳实践

总原则：端到端异步。数据库使用 Async SQLAlchemy，外部 HTTP 使用 httpx.AsyncClient，避免在事件循环中阻塞。

数据库与会话（异步）：

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

engine = create_async_engine("postgresql+asyncpg://...", future=True)
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

async def get_session() -> AsyncSession:
    return SessionLocal()
```

外部 HTTP 请求（httpx）：

```python
import httpx

async def fetch_json(url: str, *, timeout_s: float = 5.0) -> dict:
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()
```

CPU/阻塞任务迁移到线程池：

```python
import anyio

def cpu_heavy(x: int) -> int:
    # 纯 CPU 计算或阻塞库调用
    ...

async def compute(x: int) -> int:
    return await anyio.to_thread.run_sync(cpu_heavy, x)
```

---

## 并发与集合操作

并发聚合（全部成功或任一失败）：

```python
import asyncio

async def load_many():
    users_coro = user_repo.list(...)
    profiles_coro = profile_repo.list(...)
    settings_coro = settings_repo.get_all()
    users, profiles, settings = await asyncio.gather(
        users_coro, profiles_coro, settings_coro
    )
    return users, profiles, settings
```

部分成功（all_settled 等价）：

```python
import asyncio, sentry_sdk

async def load_all_settled():
    tasks = [op1(), op2(), op3()]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for idx, res in enumerate(results):
        if isinstance(res, Exception):
            sentry_sdk.capture_exception(res)
    return results
```

并发上限：使用 `asyncio.Semaphore` 或调度库（如 aiolimiter），避免过量并发压垮下游。

---

## 超时与取消控制

超时：

```python
import anyio

async def fetch_with_timeout(coro, timeout_s: float):
    with anyio.move_on_after(timeout_s) as scope:
        result = await coro
        return result
    # 超时
    raise TimeoutError("operation timed out")
```

或使用 `asyncio.wait_for(coro, timeout=...)`。

取消：优先让长耗时操作可被取消（不要捕获并吞掉 `CancelledError`）。

```python
import asyncio

async def worker():
    try:
        await asyncio.sleep(10)
    except asyncio.CancelledError:
        # 清理资源后再抛出
        raise
```

---

## 后台任务与 fire-and-forget

在请求返回后执行的任务，应使用 FastAPI BackgroundTasks 或显式捕获异常：

```python
from fastapi import APIRouter, BackgroundTasks

router = APIRouter()

async def send_email(user_email: str) -> None:
    try:
        ...  # 调用外部 SMTP/服务
    except Exception as e:
        sentry_sdk.capture_exception(e)

@router.post("/invite")
async def invite_user(email: str, bg: BackgroundTasks):
    # 业务逻辑...
    bg.add_task(send_email, email)
    return {"ok": True}
```

如需显式创建任务：

```python
import asyncio

async def handler():
    task = asyncio.create_task(send_email("a@b.com"))
    task.add_done_callback(lambda t: sentry_sdk.capture_exception(t.exception()) if t.exception() else None)
    return {"ok": True}
```

---

## 自定义异常与全局异常处理器

定义领域异常，并在全局异常处理器中映射为 HTTP 状态与统一响应。参考 fastapi-forge 的 `core/exceptions.py`：

```python
# errors.py
class AppError(Exception):
    code: str = "APP_ERROR"
    status_code: int = 400

    def __init__(self, message: str = "Error", *, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details

class NotFoundError(AppError):
    code = "NOT_FOUND"; status_code = 404

class ConflictError(AppError):
    code = "CONFLICT"; status_code = 409

class UnauthorizedError(AppError):
    code = "UNAUTHORIZED"; status_code = 401
```

注册异常处理器：

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import sentry_sdk

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "error": {"type": type(exc).__name__, "details": exc.details},
            },
        )

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception):
        sentry_sdk.capture_exception(exc)
        return JSONResponse(status_code=500, content={"code": "INTERNAL", "message": "Internal server error"})
```

在 `main.py` 中调用 `register_exception_handlers(app)`。

---

## 请求校验错误与统一响应包

FastAPI 默认将 Pydantic 校验失败返回 422。若需要统一响应格式，可覆盖 `RequestValidationError` 处理：

```python
from fastapi.exceptions import RequestValidationError
from starlette import status as http_status

@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError):
    errors = exc.errors()
    first = errors[0] if errors else {}
    field = ".".join(str(x) for x in first.get("loc", [])[1:])
    return JSONResponse(
        status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": "VALIDATION_ERROR",
            "message": first.get("msg", "validation failed"),
            "error": {"type": "ValidationError", "field": field, "details": errors},
        },
    )
```

如需完整的响应包与业务码/i18n，请参照 fastapi-forge 的 `core/response.py` 与 `core/exceptions.py`。

---

## 日志/追踪与 Sentry 集成

请求追踪（request-id）：

```python
# 中间件设置/透传 X-Request-ID，绑定到日志上下文（参考 fastapi-forge/api/middleware/request_id.py）
app.add_middleware(RequestIDMiddleware)
```

Sentry 初始化与使用：

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    integrations=[FastApiIntegration(), SqlalchemyIntegration()],
    traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
)

try:
    ...
except Exception as e:
    sentry_sdk.capture_exception(e)
    raise
```

结构化访问/请求日志：参考 `fastapi-forge/api/middleware/logging.py`，按状态码分级记录，脱敏敏感字段并统计耗时。

---

## 常见陷阱与规避

- 同步阻塞调用：在协程中调用阻塞库（如同步 ORM、requests、boto3）会阻塞事件循环 → 使用异步版本或 `anyio.to_thread.run_sync`
- 未设置超时：外部 HTTP/DB 操作未指定超时 → 为 httpx/数据库操作设置超时，提供上限保护
- 未控制并发：大量 `gather` 对下游造成洪峰 → 使用信号量/限流器限制并发
- 吞掉取消：捕获 `CancelledError` 不再抛出 → 清理后重新抛出，保持取消语义
- 静默后台异常：fire-and-forget 任务异常未记录 → 使用 BackgroundTasks 或 done_callback 记录异常
- 混用异常语义：服务层抛 `HTTPException` → 服务层仅抛领域异常，控制器/全局处理器映射为 HTTP



