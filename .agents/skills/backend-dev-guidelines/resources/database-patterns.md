# 数据库模式 - SQLAlchemy/FastAPI 最佳实践

Python/SQLAlchemy（异步）实现，提供事务、查询优化、N+1 预防、错误处理、迁移与会话管理的完整指南。

## 目录

- SQLAlchemy 引擎与会话（异步）
- 仓储模式（Repository）
- 事务模式（Unit of Work/显式事务）
- 查询优化与分页
- N+1 查询预防
- 并发与锁（悲观/乐观）
- 错误处理与映射
- 迁移（Alembic）
- 会话生命周期与测试

---

## SQLAlchemy 引擎与会话（异步）

推荐配置（参考 fastapi-forge/infrastructure/database.py）：

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from core.config import settings

engine = create_async_engine(
    settings.database.url,
    echo=settings.DEBUG,
    future=True,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=1800,
)

AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

async def get_session() -> AsyncSession:
    return AsyncSessionLocal()
```

要点：
- 使用异步驱动（postgresql+asyncpg/mysql+aiomysql/sqlite+aiosqlite）。fastapi-forge 提供 URL 异步化辅助函数。
- expire_on_commit=False 便于提交后继续访问实例属性（由应用管理刷新时机）。
- 生产环境开启 pool_pre_ping 与 pool_recycle，降低连接失效风险。

---

## 仓储模式（Repository）

何时使用仓储：复杂查询、复用查询、需要缓存或测试可替换。示例：

```python
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from infrastructure.models import User as UserModel


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: int) -> Optional[UserModel]:
        res = await self.session.execute(select(UserModel).where(UserModel.id == user_id))
        return res.scalar_one_or_none()

    async def find_by_email(self, email: str) -> Optional[UserModel]:
        res = await self.session.execute(select(UserModel).where(UserModel.email == email))
        return res.scalar_one_or_none()

    async def exists_by_email(self, email: str) -> bool:
        res = await self.session.execute(select(func.count()).select_from(UserModel).where(UserModel.email == email))
        return bool(res.scalar() or 0)

    async def create(self, *, email: str, hashed_password: str) -> UserModel:
        try:
            user = UserModel(email=email, hashed_password=hashed_password)
            self.session.add(user)
            await self.session.flush()
            await self.session.refresh(user)
            return user
        except IntegrityError as e:
            await self.session.rollback()
            raise

    async def list(self, *, skip: int, limit: int) -> List[UserModel]:
        res = await self.session.execute(
            select(UserModel).order_by(UserModel.id.desc()).offset(skip).limit(limit)
        )
        return list(res.scalars())
```

要点：仓储独立负责 ORM/SQL，服务层只面向仓储接口；将数据库异常转换为领域异常（见“错误处理与映射”）。

---

## 事务模式（Unit of Work/显式事务）

以 Unit of Work 作为事务边界（参考 fastapi-forge/infrastructure/unit_of_work.py）：

```python
from typing import Callable, Optional
from sqlalchemy.ext.asyncio import AsyncSession

class SQLAlchemyUnitOfWork:
    def __init__(self, session_factory: Callable[[], AsyncSession], *, readonly: bool = False) -> None:
        self._session_factory = session_factory
        self._readonly = readonly
        self.session: Optional[AsyncSession] = None
        self.user_repository = None

    async def __aenter__(self):
        self.session = self._session_factory()
        self.user_repository = UserRepository(self.session)
        if not self._readonly:
            self._tx = await self.session.begin()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        try:
            if exc:
                await self.rollback()
            else:
                await self.commit()
        finally:
            if self.session is not None:
                await self.session.close()

    async def commit(self):
        if self._readonly:
            return
        if self.session and self.session.in_transaction():
            await self.session.commit()

    async def rollback(self):
        if self.session and self.session.in_transaction():
            await self.session.rollback()
```

服务中使用：

```python
class UserService:
    def __init__(self, uow_factory: Callable[..., SQLAlchemyUnitOfWork]):
        self._uow_factory = uow_factory

    async def register(self, email: str, password: str) -> UserRead:
        async with self._uow_factory() as uow:
            if await uow.user_repository.exists_by_email(email):
                raise ConflictError("Email already exists")
            user = await uow.user_repository.create(email=email, hashed_password=hash_password(password))
            return UserRead.model_validate(user)

    async def get(self, user_id: int) -> UserRead | None:
        async with self._uow_factory(readonly=True) as uow:
            user = await uow.user_repository.get_by_id(user_id)
            return UserRead.model_validate(user) if user else None
```

显式事务（跨多个仓储/步骤）：

```python
async with AsyncSessionLocal() as session:
    async with session.begin():
        user = await user_repo.create(...)
        profile = await profile_repo.create(...)
```

---

## 查询优化与分页

常用优化：
- 仅选择必要列：load_only()/select 指定列
- 延迟/排除加载：defer()/undefer()
- 合理使用 joinedload/selectinload，避免过度 include
- 为常用过滤/排序字段添加索引

示例：

```python
from sqlalchemy.orm import load_only, selectinload
from sqlalchemy import select

stmt = (
    select(UserModel)
    .options(load_only(UserModel.id, UserModel.email))
    .options(selectinload(UserModel.profile))
    .order_by(UserModel.created_at.desc())
    .offset(skip)
    .limit(limit)
)
rows = (await session.execute(stmt)).scalars().all()
```

分页：
- 偏移分页（offset/limit）：易实现
- 游标分页（基于主键/时间戳）：高并发推荐

---

## N+1 查询预防

使用 selectinload 或 joinedload 预加载关联，避免循环中逐条加载：

```python
from sqlalchemy.orm import selectinload
users = (await session.execute(select(UserModel).options(selectinload(UserModel.profile)))).scalars().all()
```

选择建议：selectinload 更通用；joinedload 结果集较大时需谨慎。

---

## 并发与锁（悲观/乐观）

悲观锁（行级锁）：

```python
stmt = select(UserModel).where(UserModel.id == user_id).with_for_update()
user = (await session.execute(stmt)).scalar_one()
```

乐观锁（版本列）：

```python
class UserModel(Base):
    __tablename__ = "users"
    id = mapped_column(primary_key=True)
    version = mapped_column(Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": version}
```

---

## 错误处理与映射

常见异常：
- IntegrityError：唯一约束/外键约束失败 → 409/422
- NoResultFound/scalar_one 抛错：记录不存在 → 404
- DBAPIError：底层数据库错误 → 捕获并上报 Sentry

示例：

```python
import sentry_sdk
from sqlalchemy.exc import IntegrityError, DBAPIError

try:
    user = await repo.create(...)
except IntegrityError as e:
    raise ConflictError("Email already exists") from e
except DBAPIError as e:
    sentry_sdk.capture_exception(e)
    raise
```

---

## 迁移（Alembic）

基本流程：

```bash
alembic revision --autogenerate -m "add user table"
alembic upgrade head
alembic downgrade -1
```

要点：在 env.py 设置 target_metadata = Base.metadata；严格审阅自动生成的迁移（索引/外键/约束命名）。

---

## 会话生命周期与测试

会话生命周期：请求内使用 1 个 AsyncSession，请求结束关闭；后台任务需显式管理会话。

测试：
- 独立测试数据库或 SQLite 内存库
- 每个测试在事务中运行并回滚
- 覆盖 FastAPI 依赖注入，注入测试会话/仓储



