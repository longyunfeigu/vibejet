# 架构总览 - FastAPI 后端服务

完整阐述在 FastAPI 中落地分层架构（Routes → Controllers → Services → Repositories → Database）的生产级实践，并给出可直接使用的代码示例与配置建议。

## 目录

- 分层架构模式
- 请求生命周期
- 中间件与异常处理顺序
- 目录结构与命名约定
- 模块组织方式
- 职责分离（What goes where）
- 实战示例：用户创建流程
- 配置与环境变量（pydantic-settings）

---

## 分层架构模式

### 四层模型（FastAPI 等价实现）

```
┌─────────────────────────────────────┐
│            HTTP Request             │
└───────────────┬─────────────────────┘
                ↓
┌─────────────────────────────────────┐
│  Layer 1: ROUTES (APIRouter)        │
│  - 仅注册路由/依赖                   │
│  - 绑定中间件/异常处理               │
│  - 委派给 Controllers                │
│  - 不含业务逻辑                      │
└───────────────┬─────────────────────┘
                ↓
┌─────────────────────────────────────┐
│  Layer 2: CONTROLLERS               │
│  - 请求/响应协调（HTTP 语义）        │
│  - Pydantic 校验（或在路由层）       │
│  - 调用 Services                     │
│  - 统一格式化响应/错误               │
└───────────────┬─────────────────────┘
                ↓
┌─────────────────────────────────────┐
│  Layer 3: SERVICES                  │
│  - 业务规则/编排                     │
│  - 事务边界（UoW）                   │
│  - 依赖 Repositories                 │
│  - 不感知 HTTP                       │
└───────────────┬─────────────────────┘
                ↓
┌─────────────────────────────────────┐
│  Layer 4: REPOSITORIES              │
│  - 数据访问抽象（SQLAlchemy）        │
│  - 查询优化/缓存                     │
│  - 隐藏 ORM/驱动细节                 │
└───────────────┬─────────────────────┘
                ↓
┌─────────────────────────────────────┐
│             Database                │
└─────────────────────────────────────┘
```

为什么采用该架构：
- 可测试性：各层独立测试，依赖易 mock；边界清晰
- 可维护性：HTTP 与业务解耦；定位问题简单
- 可复用性：Service 可被定时任务、脚本、GRPC 等复用
- 可扩展性：快速新增端点，遵循一致的工程骨架

---

## 请求生命周期

以“创建用户”为例：

```
1. HTTP POST /api/v1/users
   ↓
2. FastAPI 根据 APIRouter 匹配路由（api/routes/user.py）
   ↓
3. 全局/路由级中间件与依赖执行
   - 鉴权依赖（如 get_current_user）
   - 追踪/审计中间件（request id、日志）
   ↓
4. 路由处理函数将调用委派给 Controller（依赖注入获取实例）
   ↓
5. Controller 完成入参校验/装配并调用 Service
   - Pydantic 模型（请求体/查询参数）
   - 错误转换为 HTTP 响应语义
   ↓
6. Service 执行业务逻辑与编排
   - 通过仓储访问数据库（可用 UoW 管理事务）
   ↓
7. Repository 使用 SQLAlchemy 执行查询/持久化
   ↓
8. 响应回传：Repository → Service → Controller → FastAPI → Client
```

### 中间件执行顺序（Starlette/FastAPI）

- 请求阶段：按 `app.add_middleware()` 的添加顺序自外向内执行
- 响应阶段：按相反顺序（后进先出）回卷
- 异常处理：统一由注册的异常处理器捕获（详见下节）

示例（添加顺序即为请求进入顺序）：

```python
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # 生成/传递 request-id，记录日志上下文
        response = await call_next(request)
        return response

app.add_middleware(RequestIDMiddleware)  # 在 CORS 之后、业务前
```

规则：错误处理器和监控应在路由注册完成后生效，便于捕获业务异常并附加上下文。

---

## 中间件与异常处理顺序

结合监控/追踪的生产做法：

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from starlette.responses import JSONResponse

from fastapi import FastAPI, Request

app = FastAPI()

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    integrations=[FastApiIntegration(), SqlalchemyIntegration()],
    traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
)

class ConflictError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message

@app.exception_handler(ConflictError)
async def conflict_handler(_: Request, exc: ConflictError):
    return JSONResponse(status_code=409, content={"detail": exc.message})

# 其他异常（如 ValidationError）FastAPI 已内置转换
```

要点：
- 业务域错误 → 自定义异常 + 统一异常处理器 → 一致化 HTTP 响应
- 第三方 SDK（Sentry/OTel）在应用启动时初始化
- 日志/追踪 ID 通过中间件注入，贯穿请求全链路

---

## 目录结构与命名约定

推荐（结合 fastapi-forge 的成熟实践）：

```
app/
├── api/
│   ├── routes/                # 仅路由注册与依赖装配
│   │   └── user.py
│   ├── dependencies.py        # 依赖注入工厂（Service/UoW/Storage 等）
│   └── middleware/            # 中间件实现
├── controllers/               # 控制器（HTTP 语义、装配、错误转换）
├── application/
│   ├── services/              # 业务服务（不感知 HTTP）
│   └── dtos/                  # DTO/Pydantic 模型
├── domain/                    # 领域模型/领域服务/事件
├── infrastructure/
│   ├── repositories/          # 数据访问实现（SQLAlchemy）
│   ├── database.py            # 会话/引擎/依赖
│   └── models/                # ORM 实体（SQLAlchemy Declarative）
├── core/
│   ├── config.py              # pydantic-settings 配置中心
│   ├── logging_config.py      # 日志配置
│   └── response.py            # 统一响应封装（可选）
└── main.py                    # 应用入口（挂载路由/中间件/异常处理）
```

命名：
- Controllers：`{Feature}Controller`（PascalCase + Controller）
- Services：`{feature}_service.py` 或 `{Feature}Service`
- Repositories：`{Entity}Repository`
- Routes：`{feature}.py`（一个 APIRouter 一个文件）

职责划分：
- routes：注册路径/依赖 → 委派 controller；不包含业务逻辑
- controllers：HTTP 语义与装配；不直接访问 DB
- services：业务规则与事务边界；不关注 HTTP
- repositories：面向会话的持久化操作；不包含业务规则

---

## 模块组织方式

当功能复杂度较高，采用特性（feature）分包：

```
app/user/
├── controllers/
├── services/
├── repositories/
├── models/
└── dtos/
```

当功能简单时，保持平铺，避免过度抽象。

---

## 职责分离（What goes where）

Routes 层：
- 注册路由/依赖、应用中间件（路由级）
- 将调用委派到 Controller
- 不包含业务逻辑或 DB 操作

Controllers 层：
- 请求参数装配、必要的请求级校验
- 调用 Service，统一响应格式与错误语义
- 不包含业务规则、不直接操作 DB

Services 层：
- 领域规则、编排多个仓储/外部服务
- 事务边界（结合 UoW/Session）
- 不感知 HTTP，不返回 Response/StatusCode

Repositories 层：
- 面向 AsyncSession 的查询/持久化
- 查询优化、缓存策略、错误转换
- 不包含业务规则

---

## 实战示例：用户创建流程

以下示例可直接作为生产代码骨架（Python 3.11+，FastAPI，SQLAlchemy 2.x）。

### 1) 基础配置与数据库会话（core/config.py, infrastructure/database.py）

```python
# core/config.py
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI App"
    DEBUG: bool = True
    DATABASE_URL: str = Field(default="postgresql+asyncpg://user:pass@localhost/app")
    SENTRY_DSN: str | None = None
    SENTRY_TRACES_SAMPLE_RATE: float = 0.0

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "allow",
    }

settings = Settings()
```

```python
# infrastructure/database.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import String, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from typing import AsyncGenerator

from core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG, future=True)
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
```

### 2) DTO 与请求模型（application/dtos/users.py）

```python
from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)

class UserRead(BaseModel):
    id: int
    email: EmailStr
    is_active: bool = True
    is_superuser: bool = False

    model_config = {"from_attributes": True}
```

### 3) Repository（infrastructure/repositories/user_repository.py）

```python
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from infrastructure.database import User

class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, email: str, hashed_password: str) -> User:
        user = User(email=email, hashed_password=hashed_password)
        self.session.add(user)
        await self.session.flush()  # 提前获取 ID
        return user
```

### 4) Unit of Work（infrastructure/unit_of_work.py）

```python
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncIterator, Callable

from infrastructure.database import get_session

class SQLAlchemyUnitOfWork:
    def __init__(self, session_factory: Callable[[], AsyncIterator[AsyncSession]] = get_session) -> None:
        self._session_factory = session_factory
        self.session: AsyncSession | None = None

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        gen = self._session_factory()
        self.session = await gen.__anext__()  # 取得 session
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        assert self.session is not None
        if exc:
            await self.session.rollback()
        else:
            await self.session.commit()
        await self.session.close()
```

### 5) Service（application/services/user_service.py）

```python
from pydantic import EmailStr
from passlib.context import CryptContext

from application.dtos.users import UserCreate, UserRead
from infrastructure.repositories.user_repository import UserRepository
from infrastructure.unit_of_work import SQLAlchemyUnitOfWork

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class ConflictError(Exception):
    pass

class UserService:
    def __init__(self, uow_factory=SQLAlchemyUnitOfWork) -> None:
        self._uow_factory = uow_factory

    async def create(self, payload: UserCreate) -> UserRead:
        async with self._uow_factory() as uow:
            repo = UserRepository(uow.session)
            existing = await repo.find_by_email(payload.email)
            if existing:
                raise ConflictError("Email already exists")
            hashed = pwd_context.hash(payload.password)
            user = await repo.create(email=payload.email, hashed_password=hashed)
            return UserRead.model_validate(user)
```

### 6) Controller（controllers/user_controller.py）

```python
from fastapi import status
from fastapi.responses import JSONResponse

from application.dtos.users import UserCreate, UserRead
from application.services.user_service import UserService, ConflictError

class UserController:
    def __init__(self, service: UserService) -> None:
        self._service = service

    async def create(self, payload: UserCreate) -> JSONResponse:
        try:
            user = await self._service.create(payload)
            return JSONResponse(status_code=status.HTTP_201_CREATED, content=user.model_dump())
        except ConflictError as e:
            return JSONResponse(status_code=409, content={"detail": str(e)})
```

说明：在 FastAPI 中，也可直接在路由层返回 `UserRead`，由框架自动序列化。此处 Controller 提供更清晰的 HTTP 语义控制与错误统一处理，适合中大型项目。

### 7) 路由与依赖（api/routes/user.py, api/dependencies.py）

```python
# api/dependencies.py
from fastapi import Depends
from application.services.user_service import UserService

def get_user_service() -> UserService:
    return UserService()
```

```python
# api/routes/user.py
from fastapi import APIRouter, Depends

from api.dependencies import get_user_service
from application.dtos.users import UserCreate
from application.services.user_service import UserService
from controllers.user_controller import UserController

router = APIRouter(prefix="/users", tags=["Users"])

def get_user_controller(service: UserService = Depends(get_user_service)) -> UserController:
    return UserController(service)

@router.post("", summary="Create user")
async def create_user(payload: UserCreate, controller: UserController = Depends(get_user_controller)):
    return await controller.create(payload)
```

### 8) 应用入口（main.py）

```python
from fastapi import FastAPI
from api.routes.user import router as user_router

app = FastAPI(title=settings.PROJECT_NAME, debug=settings.DEBUG)

app.include_router(user_router, prefix="/api/v1")

# 自动文档：/docs (Swagger) 与 /redoc
```

---

## 配置与环境变量（pydantic-settings）

核心建议：
- 使用 `pydantic-settings` 管理配置，支持 `.env` 与环境变量覆盖
- 使用嵌套模型组织子系统（database/redis/storage/grpc 等）
- 关键密钥（如 `SECRET_KEY`）在所有环境显式设置，避免热更新导致状态不一致

示例（与 fastapi-forge 一致的思路）：

```python
# core/config.py（节选）
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class DatabaseSettings(BaseSettings):
    url: str = Field(default="postgresql+asyncpg://user:pass@localhost/app")

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI DDD App"
    DEBUG: bool = True
    SECRET_KEY: str = Field(..., description="JWT/签名密钥")
    database: DatabaseSettings = DatabaseSettings()

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, env_nested_delimiter="__")

settings = Settings()
```

`.env` 示例：

```
PROJECT_NAME="FastAPI DDD App"
DEBUG=true
SECRET_KEY=please-change-me
DATABASE__URL=postgresql+asyncpg://user:pass@localhost/app
```

---

## 生产最佳实践（要点）

- 类型提示：为函数/方法/属性提供完整类型注解，启用 `mypy`/`pyright`
- 异步优先：数据库/HTTP 客户端使用异步驱动（`asyncpg`/`httpx`）
- 事务管理：以 Service 为边界，使用 UoW 或显式事务控制
- 配置中心：集中化配置，避免散落 `os.getenv`；区分环境和可观测性
- 监控与追踪：集成 Sentry/OTel，注入 request-id，结构化日志
- 自动文档：使用响应模型（`response_model=`）与描述完善 API 文档
- 测试：API 层使用 `httpx.AsyncClient`/`pytest-asyncio`；Service 层用内存 DB 或事务回滚



