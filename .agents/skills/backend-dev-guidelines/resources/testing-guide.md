# 测试指南 - FastAPI/pytest 实战

面向生产的 FastAPI 测试策略：单元/集成/接口测试、依赖覆盖、异步会话/事务回滚、鉴权模拟与外部依赖mock。示例基于 `pytest` + `pytest-asyncio` + `httpx.AsyncClient` + SQLAlchemy async。

## 目录

- 测试分层与目录结构
- 单元测试（服务/仓储）
- 集成测试（数据库/事务回滚）
- API 测试（依赖覆盖/鉴权模拟）
- 外部依赖 Mock（HTTP/存储/队列）
- 测试数据与工厂
- 覆盖率与运行命令

---

## 测试分层与目录结构

建议结构：

```
tests/
├── unit/                    # 纯业务逻辑（Service/Domain）
├── integration/             # DB/仓储/会话、UoW
├── api/                     # FastAPI 路由/控制器（httpx）
├── factories/               # 测试数据工厂（可选：factory_boy/faker）
└── conftest.py              # 公共fixture（事件循环、应用、测试会话）
```

---

## 单元测试（服务/仓储）

服务层单元测试：替换仓储为内存/假对象，断言业务规则而非 HTTP 语义。

```python
# tests/unit/test_user_service.py
import pytest
from types import SimpleNamespace
from application.services.user_service import UserApplicationService, ConflictError


class InMemoryUserRepo:
    def __init__(self):
        self.by_email = {}
        self.auto = 0

    async def exists_by_email(self, email: str) -> bool:
        return email in self.by_email

    async def create(self, *, email: str, hashed_password: str):
        self.auto += 1
        user = SimpleNamespace(id=self.auto, email=email, hashed_password=hashed_password)
        self.by_email[email] = user
        return user


class FakeUoW:
    def __init__(self):
        self.user_repository = InMemoryUserRepo()
    async def __aenter__(self): return self
    async def __aexit__(self, *a): return None
    async def commit(self): pass
    async def rollback(self): pass


@pytest.mark.asyncio
async def test_create_user_ok():
    svc = UserApplicationService(lambda: FakeUoW())
    u = await svc.create(payload=SimpleNamespace(email="a@b.com", password="12345678"))
    assert u.email == "a@b.com"


@pytest.mark.asyncio
async def test_create_user_conflict():
    svc = UserApplicationService(lambda: FakeUoW())
    await svc.create(payload=SimpleNamespace(email="dup@b.com", password="12345678"))
    with pytest.raises(ConflictError):
        await svc.create(payload=SimpleNamespace(email="dup@b.com", password="12345678"))
```

仓储层单元测试（可选）：针对 SQL 生成/过滤逻辑较多时，用 SQLite 内存库跑快速校验。

---

## 集成测试（数据库/事务回滚）

两种模式：
- 轻量模式：SQLite 内存库 + 自动建表 → 速度快、行为与生产略有差异
- 真实模式：测试专用 Postgres/MySQL → 使用事务回滚模式保证隔离

SQLite 示例（推荐起步）：

```python
# tests/conftest.py（片段）
import pytest, asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from infrastructure.models.base import Base


@pytest.fixture(scope="session")
def event_loop():  # pytest-asyncio 需要自定义 loop 范围
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture()
async def session(async_engine):
    SessionLocal = async_sessionmaker(bind=async_engine, expire_on_commit=False, class_=AsyncSession)
    async with SessionLocal() as s:
        yield s  # 测试中手动清理数据或使用回滚策略
```

Postgres 事务回滚（高级）：建立一次连接，测试级 nested transaction（SAVEPOINT）并在 teardown 回滚重置（详见 SQLAlchemy 文档）。

---

## API 测试（依赖覆盖/鉴权模拟）

使用 `httpx.AsyncClient` 与 FastAPI 的依赖覆盖机制。

```python
# tests/api/test_users.py
import pytest
from httpx import AsyncClient
from main import app


@pytest.fixture(autouse=True)
def _override_auth():
    from api.dependencies import get_current_user
    class _User:
        id = 1; is_active = True; is_superuser = True; email = "test@demo"
    app.dependency_overrides[get_current_user] = lambda: _User()
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_create_user_api():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        res = await ac.post("/api/v1/users", json={"email": "a@b.com", "password": "12345678"})
        assert res.status_code in (200, 201)
        payload = res.json()
        assert payload.get("email") == "a@b.com" or payload.get("data", {}).get("email") == "a@b.com"
```

覆盖数据层依赖：

```python
# 覆盖 get_user_service 以注入测试 UoW/会话
from api.dependencies import get_user_service
from application.services.user_service import UserApplicationService
from infrastructure.unit_of_work import SQLAlchemyUnitOfWork

def _test_user_service_factory(session):
    def factory():
        return SQLAlchemyUnitOfWork(session_factory=lambda: session)
    return UserApplicationService(uow_factory=factory)

app.dependency_overrides[get_user_service] = lambda: _test_user_service_factory(session)
```

---

## 外部依赖 Mock（HTTP/存储/队列）

- HTTP：使用 `respx` 或 `pytest-httpx` 拦截 httpx 请求
- 对象存储：实现 `StoragePort` 的内存版本，注入 `FileAssetApplicationService`
- 消息/队列：用“直连内存实现”或 `asyncio.Queue` 替代，断言发送次数与负载

```python
import respx, httpx, pytest

@pytest.mark.asyncio
async def test_external_call():
    with respx.mock() as router:
        route = router.get("https://api.example.com/user").mock(return_value=httpx.Response(200, json={"id": 1}))
        data = await fetch_json("https://api.example.com/user")
        assert route.called
        assert data["id"] == 1
```

---

## 测试数据与工厂

- Faker：`faker` 生成随机但合理的数据
- 工厂：`factory_boy` 定义 ORM/DTO 工厂，结合会话批量插入
- 固定基线数据：在 `session` fixture 层创建，测试按需扩展

---

## 覆盖率与运行命令

推荐覆盖率：
- 单元测试：70%+
- 集成测试：关键路径覆盖
- API/E2E：主流程覆盖

运行命令：

```bash
pytest -q
pytest -q --cov=fastapi-forge --cov-report=term-missing
```

CI 建议：
- 为数据库测试提供 `TEST_DATABASE_URL`
- 并发执行（pytest -n auto）时注意数据库隔离（使用独立 schema/库）


