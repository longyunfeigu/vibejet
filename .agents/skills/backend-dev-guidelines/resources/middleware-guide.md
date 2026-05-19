# 中间件指南 - FastAPI/Starlette 模式

面向生产的 FastAPI 中间件与依赖组合实践，等价映射自 Express 指南并结合 fastapi-forge 的成熟实现（请求追踪、日志、i18n、鉴权、错误边界）。

## 目录

- 中间件 vs 依赖（何时用哪一个）
- 鉴权中间件（推荐依赖方式）
- 审计/上下文传播（contextvars + request.state）
- 错误边界（全局异常处理器 + Sentry）
- 校验/限流/请求体记录（可复用依赖与中间件）
- 组合式依赖与路由级依赖
- 中间件顺序与集成清单

---

## 中间件 vs 依赖（何时用哪一个）

- 使用中间件（app.add_middleware）：跨切面、与 HTTP 请求生命周期强相关且与路由无关的能力，例如：
  - Request ID/Trace 绑定
  - 访问/请求日志
  - 语言/区域解析
- 使用依赖（Depends）：需要访问应用上下文、用户态或与路由强绑定的校验/鉴权/装配，例如：
  - Bearer/OAuth2 鉴权与用户加载
  - 参数复用（分页、过滤、租户）
  - 业务域的审计上下文绑定

经验法则：用户/权限/租户等语义使用依赖，平台级横切关注使用中间件。

---

## 鉴权中间件（推荐依赖方式）

在 FastAPI 中，鉴权优先使用依赖（更易组合、可复用、可测试）。参考 fastapi-forge/api/dependencies.py：

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login", auto_error=False)
http_bearer = HTTPBearer(auto_error=False)

async def get_token(
    oauth2_token: Optional[str] = Depends(oauth2_scheme),
    bearer_token: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer)
) -> str:
    if oauth2_token:
        return oauth2_token
    if bearer_token and bearer_token.credentials:
        return bearer_token.credentials
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing credentials")

async def get_current_user(token: str = Depends(get_token)) -> UserDTO:
    user_id = await token_service.verify_access_token(token)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return await user_service.get_user(user_id)
```

路由级强制鉴权：

```python
router = APIRouter(prefix="/files", tags=["Files"], dependencies=[Depends(get_current_user)])
```

注：如必须由中间件读取 Cookie 并写入 `request.state.claims`，仍建议在依赖中消费该状态，避免在中间件做业务决策。

---

## 审计/上下文传播（contextvars + request.state）

推荐模式：使用 `contextvars` 将 request-id、client-ip、user-id 注入结构化日志与服务层，无需层层传参。参考 fastapi-forge：

```python
# api/middleware/request_id.py（节选）
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
client_ip_var: ContextVar[Optional[str]] = ContextVar("client_ip", default=None)

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = req_id
        request_id_var.set(req_id)
        # ... 省略绑定 structlog 上下文
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response
```

业务审计上下文（示例）：

```python
from contextvars import ContextVar
from typing import Optional

class AuditContext:
    def __init__(self, user_id: Optional[int], request_id: str):
        self.user_id = user_id
        self.request_id = request_id

audit_ctx: ContextVar[Optional[AuditContext]] = ContextVar("audit_ctx", default=None)

async def bind_audit_context(user: UserDTO = Depends(get_current_user), request: Request = None):
    ctx = AuditContext(user_id=user.id, request_id=getattr(request.state, "request_id", ""))
    audit_ctx.set(ctx)

def get_audit_context() -> Optional[AuditContext]:
    return audit_ctx.get()
```

在服务层使用：

```python
def record_business_metric(event: str):
    ctx = get_audit_context()
    logger.info("biz_event", event=event, user_id=ctx.user_id if ctx else None, request_id=ctx.request_id if ctx else None)
```

---

## 错误边界（全局异常处理器 + Sentry）

在 FastAPI 中，错误边界使用 `@app.exception_handler` 实现；中间件负责记录和透传 request-id。参考 fastapi-forge/core/exceptions.py：

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import sentry_sdk

def register_exception_handlers(app: FastAPI):
    @app.exception_handler(BusinessException)
    async def business_handler(_: Request, exc: BusinessException):
        return JSONResponse(status_code=map_code(exc.code), content=error_response(...).model_dump())

    @app.exception_handler(Exception)
    async def global_handler(_: Request, exc: Exception):
        sentry_sdk.capture_exception(exc)
        return JSONResponse(status_code=500, content=error_response(...).model_dump())
```

Sentry 初始化建议在应用启动处执行，并启用 FastAPI/SQLAlchemy 集成：

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

sentry_sdk.init(dsn=settings.SENTRY_DSN, integrations=[FastApiIntegration(), SqlalchemyIntegration()], traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE)
```

---

## 校验/限流/请求体记录（可复用依赖与中间件）

请求体/访问日志：参考 fastapi-forge/api/middleware/logging.py（脱敏敏感字段、限制记录大小、记录耗时与状态）：

```python
app.add_middleware(LoggingMiddleware)
```

限流（示例思路）：

```python
# 依赖实现租户/用户级令牌桶（伪码）
async def rate_limiter(user: UserDTO = Depends(get_current_user)):
    allowed = await redis_token_bucket("rl:user", user.id, capacity=100, refill_rate=10)
    if not allowed:
        raise HTTPException(status_code=429, detail="Too many requests")

router = APIRouter(dependencies=[Depends(rate_limiter)])
```

内容校验（MIME/大小）可在依赖中完成，避免中间件反复解析请求体：

```python
def ensure_json(content_type: str = Header(...)):
    if "application/json" not in content_type.lower():
        raise HTTPException(415, "Unsupported Media Type")
```

---

## 组合式依赖与路由级依赖

等价于 Express 的“可组合中间件”，FastAPI 使用依赖组合：

```python
from fastapi import Depends

def with_auth_and_audit():
    return [Depends(get_current_user), Depends(bind_audit_context)]

router = APIRouter(prefix="/secure", dependencies=with_auth_and_audit())

@router.post("/submit", dependencies=[Depends(rate_limiter)])
async def submit(...):
    ...
```

也可在 `include_router` 时统一添加：

```python
app.include_router(user_router, prefix="/api/v1", dependencies=with_auth_and_audit())
```

---

## 中间件顺序与集成清单

Starlette 中间件按添加顺序包裹请求（请求阶段自外向内，响应阶段反向）。推荐顺序：

```python
from starlette.middleware.cors import CORSMiddleware

app = FastAPI(...)

# 1) CORS（尽早）
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# 2) Request ID（追踪）
app.add_middleware(RequestIDMiddleware)

# 3) Locale（语言/i18n）
app.add_middleware(LocaleMiddleware)

# 4) Logging（请求/响应日志与耗时）
app.add_middleware(LoggingMiddleware)

# 5) 其他横切（Sentry ASGI 中间件、CSRF、压缩等）

# 6) 路由注册
app.include_router(user_router, prefix="/api/v1")

# 7) 注册异常处理器（非中间件，作用于全局）
register_exception_handlers(app)
```

注意事项：
- 读取请求体的中间件应限制大小并避免对 `multipart` 进行重解析；Starlette 的 `Request` 会缓存已读主体，避免重复读取冲突，但仍需审慎。
- 对性能敏感的路径（健康检查/OpenAPI）可在日志中间件中跳过（见 fastapi-forge 的 `SKIP_PATHS`）。
- 在生产环境配置 `pool_pre_ping/pool_recycle`（数据库）、`timeout`（外部 HTTP）并添加结构化日志维度（request-id、user-id、client-ip）。

