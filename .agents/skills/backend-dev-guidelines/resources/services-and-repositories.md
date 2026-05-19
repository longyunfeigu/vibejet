# 服务与仓储 - 业务逻辑层（FastAPI/SQLAlchemy）

将 TypeScript 后端模式等价映射到 Python/FastAPI：用 Service 承载业务规则，用 Repository 封装数据访问，并通过 Unit of Work 管理事务与一致性。示例均可直接用于生产项目。

## 目录

- 服务层概览（职责与边界）
- 依赖注入模式（Depends/构造注入/UoW 工厂）
- Unit of Work（事务边界与只读会话）
- 仓储模式（SQLAlchemy async 数据访问）
- 服务设计原则（命名/返回/异常）
- 缓存策略（内存/Redis/失效）
- 测试服务（pytest + pytest-asyncio）
- 参考实现与实践要点

---

## 服务层概览（职责与边界）

服务负责应用的业务规则与编排：

- ✅ 执行业务规则与校验
- ✅ 编排多个仓储/外部系统
- ✅ 定义事务边界（结合 UoW）
- ✅ 复杂计算/聚合
- ✅ 与外部服务交互（邮件、支付、消息）

服务不应：

- ❌ 了解 HTTP（不返回 Response/状态码，不抛 HTTPException）
- ❌ 直接操作 ORM（通过仓储）
- ❌ 格式化 HTTP 响应或拼装文案

心智模型：

```
Controller 问：这个操作能不能做？
Service 答：能/不能，为什么，并执行相应的业务流程
Repository 执行：按要求读取/写入数据
```

---

## 依赖注入模式（Depends/构造注入/UoW 工厂）

FastAPI 使用 `Depends` 提供轻量 DI，但服务对象本身建议通过构造函数注入其依赖，方便测试与替换。

### 控制器/路由装配服务

```python
# api/dependencies.py
from application.services.user_service import UserApplicationService
from infrastructure.unit_of_work import SQLAlchemyUnitOfWork


def get_user_service() -> UserApplicationService:
    # 通过工厂传递 UoW，使服务拥有事务能力
    return UserApplicationService(uow_factory=SQLAlchemyUnitOfWork)
```

```python
# api/routes/user.py
from fastapi import APIRouter, Depends
from typing import Annotated

from api.dependencies import get_user_service
from application.services.user_service import UserApplicationService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/{user_id}")
async def get_user(user_id: int, service: Annotated[UserApplicationService, Depends(get_user_service)]):
    return await service.get_user(user_id)
```

### 服务构造注入（可测试/可替换）

```python
# application/services/notification_service.py
from typing import Protocol, Optional


class EmailClient(Protocol):
    async def send(self, to: str, subject: str, body: str) -> None: ...


class NotificationService:
    def __init__(self, *, email: EmailClient, template_engine, preference_repo):
        self._email = email
        self._tpl = template_engine
        self._prefs = preference_repo

    async def notify_user(self, user_id: int, template: str, ctx: dict) -> None:
        prefs = await self._prefs.get_by_user_id(user_id)
        if not prefs.email_enabled:
            return
        subject, body = self._tpl.render(template, ctx)
        await self._email.send(prefs.email, subject, body)
```

- 依赖通过构造函数注入，便于在测试中替换为假对象或内存实现。
- 服务内部不依赖 FastAPI/Request/Response 类型。

---

## Unit of Work（事务边界与只读会话）

结合 fastapi-forge 实践，推荐以 UoW 作为服务方法的事务边界：

```python
# domain/common/unit_of_work.py（抽象）
from abc import ABC, abstractmethod

class AbstractUnitOfWork(ABC):
    user_repository: "UserRepository"

    async def __aenter__(self) -> "AbstractUnitOfWork":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if exc:
            await self.rollback()
        else:
            await self.commit()

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...
```

```python
# infrastructure/unit_of_work.py（实现，参考 fastapi-forge）
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Callable, Optional

from infrastructure.database import AsyncSessionLocal
from infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from domain.common.unit_of_work import AbstractUnitOfWork


class SQLAlchemyUnitOfWork(AbstractUnitOfWork):
    def __init__(self, session_factory: Callable[[], AsyncSession] = AsyncSessionLocal, *, readonly: bool = False):
        self._session_factory = session_factory
        self._readonly = readonly
        self.session: Optional[AsyncSession] = None
        self.user_repository = None  # type: ignore

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        self.session = self._session_factory()
        self.user_repository = SQLAlchemyUserRepository(self.session)
        if not self._readonly:
            self._tx = await self.session.begin()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        try:
            await super().__aexit__(exc_type, exc, tb)
        finally:
            if self.session is not None:
                await self.session.close()
                self.session = None
            self.user_repository = None  # type: ignore

    async def commit(self) -> None:
        if self._readonly:
            return
        if self.session and self.session.in_transaction():
            await self.session.commit()

    async def rollback(self) -> None:
        if self.session and self.session.in_transaction():
            await self.session.rollback()
```

在服务中使用（读写分离/只读优化）：

```python
# application/services/user_service.py（节选）
from typing import Callable
from domain.common.unit_of_work import AbstractUnitOfWork
from application.dtos.users import UserCreate, UserRead


class ConflictError(Exception): ...


class UserApplicationService:
    def __init__(self, uow_factory: Callable[..., AbstractUnitOfWork]):
        self._uow_factory = uow_factory

    async def create(self, payload: UserCreate) -> UserRead:
        async with self._uow_factory() as uow:
            # 检查冲突
            if await uow.user_repository.exists_by_email(payload.email):
                raise ConflictError("Email already exists")
            user = await uow.user_repository.create(email=payload.email, hashed_password=hash_password(payload.password))
            return UserRead.model_validate(user)

    async def get(self, user_id: int) -> UserRead | None:
        async with self._uow_factory(readonly=True) as uow:
            user = await uow.user_repository.get_by_id(user_id)
            return UserRead.model_validate(user) if user else None
```

---

## 仓储模式（SQLAlchemy async 数据访问）

仓储隐藏 ORM 与数据库细节，让服务面向抽象接口编程。

### 抽象接口

```python
# domain/user/repository.py
from abc import ABC, abstractmethod
from typing import Optional, List

class UserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: int): ...

    @abstractmethod
    async def find_by_email(self, email: str): ...

    @abstractmethod
    async def create(self, email: str, hashed_password: str): ...

    @abstractmethod
    async def update_password(self, user_id: int, hashed_password: str): ...

    @abstractmethod
    async def delete(self, user_id: int) -> bool: ...

    @abstractmethod
    async def exists_by_email(self, email: str) -> bool: ...

    @abstractmethod
    async def list(self, skip: int, limit: int) -> List[object]: ...
```

### SQLAlchemy 实现（生产示例）

```python
# infrastructure/repositories/user_repository.py
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from infrastructure.models import User as UserModel


class SQLAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: int) -> Optional[UserModel]:
        result = await self.session.execute(select(UserModel).where(UserModel.id == user_id))
        return result.scalar_one_or_none()

    async def find_by_email(self, email: str) -> Optional[UserModel]:
        result = await self.session.execute(select(UserModel).where(UserModel.email == email))
        return result.scalar_one_or_none()

    async def exists_by_email(self, email: str) -> bool:
        result = await self.session.execute(select(func.count()).select_from(UserModel).where(UserModel.email == email))
        return (result.scalar() or 0) > 0

    async def create(self, *, email: str, hashed_password: str) -> UserModel:
        try:
            user = UserModel(email=email, hashed_password=hashed_password)
            self.session.add(user)
            await self.session.flush()
            await self.session.refresh(user)
            return user
        except IntegrityError:
            await self.session.rollback()
            # 建议转换为领域层异常（EmailAlreadyExists 等）
            raise

    async def update_password(self, user_id: int, hashed_password: str) -> UserModel:
        result = await self.session.execute(select(UserModel).where(UserModel.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            # 转换为领域异常（UserNotFound）
            raise KeyError(user_id)
        user.hashed_password = hashed_password
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def delete(self, user_id: int) -> bool:
        result = await self.session.execute(select(UserModel).where(UserModel.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return False
        await self.session.delete(user)
        await self.session.flush()
        return True

    async def list(self, *, skip: int, limit: int) -> List[UserModel]:
        result = await self.session.execute(select(UserModel).order_by(UserModel.id.desc()).offset(skip).limit(limit))
        return list(result.scalars())
```

要点：
- 仅仓储直接接触 ORM/SQL；服务不感知数据层细节
- 使用 `flush()` 在未提交前拿到自增主键；需要实体最新值时 `refresh()`
- 将数据库错误（IntegrityError 等）转换为领域异常，便于控制器统一映射到 HTTP 状态

---

## 服务设计原则（命名/返回/异常）

1) 单一职责：服务围绕一个限界上下文或资源展开，不要形成「上帝服务」
2) 命名清晰：`create_user`/`get_preferences`/`should_batch_email` 描述「做什么」
3) 返回显式：使用类型注解与 Pydantic DTO；不要返回裸 ORM 模型到 API 层
4) 异常语义：抛出领域异常（`ConflictError`/`NotFoundError`/`PermissionDenied`），交由异常处理器映射为 HTTP
5) 事务一致：以服务方法为事务边界，读写分离（`readonly=True`）提升并发与性能

---

## 缓存策略（内存/Redis/失效）

### 1. 进程内 TTL 缓存

```python
# 简单 TTL 缓存（线程/协程安全策略视规模采用锁/单线程 loop）
import time

class PermissionService:
    def __init__(self, repo, ttl_s: int = 300) -> None:
        self._repo = repo
        self._ttl = ttl_s
        self._cache: dict[str, tuple[bool, float]] = {}

    def _now(self) -> float:
        return time.monotonic()

    def _get_cache(self, key: str) -> bool | None:
        hit = self._cache.get(key)
        if not hit:
            return None
        value, ts = hit
        if self._now() - ts < self._ttl:
            return value
        self._cache.pop(key, None)
        return None

    async def can_complete_step(self, user_id: int, step_id: int) -> bool:
        key = f"{user_id}:{step_id}"
        cached = self._get_cache(key)
        if cached is not None:
            return cached
        # 真实检查
        allowed = await self._repo.check_step_permission(user_id, step_id)
        self._cache[key] = (allowed, self._now())
        return allowed

    def invalidate_user(self, user_id: int) -> None:
        prefix = f"{user_id}:"
        for k in list(self._cache.keys()):
            if k.startswith(prefix):
                self._cache.pop(k, None)
```

注意：多实例部署需使用分布式缓存（Redis）或事件驱动（发布失效事件）。

### 2. Redis 缓存（推荐分布式）

- key 设计：`service:entity:id`，带版本号/区域（namespace）避免污染
- TTL 控制：与业务一致；重要数据按事件主动失效
- 防穿透：空值也缓存短 TTL

---

## 测试服务（pytest + pytest-asyncio）

### 单元测试：仓储替身 + 断言业务规则

```python
# tests/test_user_service.py
import pytest
from types import SimpleNamespace
from application.services.user_service import UserApplicationService, ConflictError


class InMemoryUserRepo:
    def __init__(self):
        self._by_email: dict[str, object] = {}
        self._by_id: dict[int, object] = {}
        self._auto = 0

    async def exists_by_email(self, email: str) -> bool:
        return email in self._by_email

    async def create(self, *, email: str, hashed_password: str):
        self._auto += 1
        user = SimpleNamespace(id=self._auto, email=email, hashed_password=hashed_password)
        self._by_email[email] = user
        self._by_id[user.id] = user
        return user

    async def get_by_id(self, user_id: int):
        return self._by_id.get(user_id)


class FakeUoW:
    def __init__(self):
        self.user_repository = InMemoryUserRepo()
        self._committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def commit(self):
        self._committed = True

    async def rollback(self):
        self._committed = False


@pytest.mark.asyncio
async def test_create_user_happy_path():
    svc = UserApplicationService(lambda: FakeUoW())
    user = await svc.create(payload=SimpleNamespace(email="a@b.com", password="12345678"))
    assert user.email == "a@b.com"


@pytest.mark.asyncio
async def test_create_user_conflict():
    svc = UserApplicationService(lambda: FakeUoW())
    await svc.create(payload=SimpleNamespace(email="dup@b.com", password="12345678"))
    with pytest.raises(ConflictError):
        await svc.create(payload=SimpleNamespace(email="dup@b.com", password="12345678"))
```

### 集成测试：真实会话 + 事务回滚

- 建立测试用数据库（或 SQLite 内存库）
- 每个测试开启事务并回滚，保持环境整洁
- 使用 `httpx.AsyncClient` 测试 API 层，或直接测试服务层方法

---

## 实践要点

实践要点：
- 服务不返回 HTTP 语义（状态/Response），只返回 DTO 或领域对象
- 将数据库异常转换为领域异常，由全局异常处理器统一映射到 HTTP
- 以服务方法为事务边界；读多写少的查询使用只读 UoW 降低锁竞争
- 依赖通过构造函数显式注入；在 `api/dependencies.py` 中集中装配，便于测试与替换
- 避免「上帝服务」；按子域拆分服务，方法命名清晰且具备业务语义



