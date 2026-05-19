# 完整示例 - FastAPI 生产级实现

提供端到端的可运行示例：DTO/仓储/服务/UoW/控制器/路由/异常处理与测试，展示如何在 FastAPI 中落实分层架构与工程化模式。

## 目录

- 用户管理端到端（推荐模板）
- 从“路由塞满业务”到“分层架构”的重构示例
- 文件域（分页 + 统一响应包）示例

---

## 用户管理端到端

### 1) DTO（application/dtos/users.py）

```python
from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: Optional[str] = Field(None, max_length=100)


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, pattern=r"^1[3-9]\d{9}$")


class UserRead(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str]
    is_active: bool = True

    model_config = {"from_attributes": True}
```

### 2) 模型与会话（infrastructure/models/base.py, infrastructure/database.py）

```python
# infrastructure/models/base.py
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

```python
# infrastructure/database.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from core.config import settings

engine = create_async_engine(settings.database.url, echo=settings.DEBUG, future=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

async def get_session() -> AsyncSession:
    return AsyncSessionLocal()
```

```python
# infrastructure/models/user.py
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, Integer
from .base import Base


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None]
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
```

### 3) 仓储（infrastructure/repositories/user_repository.py）

```python
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from infrastructure.models.user import UserModel


class SQLAlchemyUserRepository:
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

    async def create(self, *, email: str, hashed_password: str, full_name: str | None = None) -> UserModel:
        try:
            user = UserModel(email=email, hashed_password=hashed_password, full_name=full_name)
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

    async def update_full_name(self, user_id: int, full_name: str | None) -> UserModel | None:
        res = await self.session.execute(select(UserModel).where(UserModel.id == user_id))
        user = res.scalar_one_or_none()
        if not user:
            return None
        user.full_name = full_name
        await self.session.flush()
        await self.session.refresh(user)
        return user
```

### 4) UoW（infrastructure/unit_of_work.py）

```python
from typing import Callable, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from infrastructure.database import AsyncSessionLocal
from infrastructure.repositories.user_repository import SQLAlchemyUserRepository


class SQLAlchemyUnitOfWork:
    def __init__(self, session_factory: Callable[[], AsyncSession] = AsyncSessionLocal, *, readonly: bool = False) -> None:
        self._session_factory = session_factory
        self._readonly = readonly
        self.session: Optional[AsyncSession] = None
        self.user_repository: SQLAlchemyUserRepository | None = None

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        self.session = self._session_factory()
        self.user_repository = SQLAlchemyUserRepository(self.session)
        if not self._readonly:
            self._tx = await self.session.begin()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        try:
            if exc:
                await self.rollback()
            else:
                await self.commit()
        finally:
            if self.session is not None:
                await self.session.close()
            self.session = None
            self.user_repository = None

    async def commit(self) -> None:
        if self._readonly:
            return
        if self.session and self.session.in_transaction():
            await self.session.commit()

    async def rollback(self) -> None:
        if self.session and self.session.in_transaction():
            await self.session.rollback()
```

### 5) 服务（application/services/user_service.py）

```python
from typing import Callable
from passlib.context import CryptContext
from application.dtos.users import UserCreate, UserUpdate, UserRead


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class ConflictError(Exception):
    pass


class UserApplicationService:
    def __init__(self, uow_factory: Callable[..., "SQLAlchemyUnitOfWork"]):
        self._uow_factory = uow_factory

    async def create(self, payload: UserCreate) -> UserRead:
        async with self._uow_factory() as uow:
            assert uow.user_repository is not None
            if await uow.user_repository.exists_by_email(payload.email):
                raise ConflictError("Email already exists")
            hashed = pwd_context.hash(payload.password)
            user = await uow.user_repository.create(
                email=payload.email,
                hashed_password=hashed,
                full_name=payload.full_name,
            )
            return UserRead.model_validate(user)

    async def get(self, user_id: int) -> UserRead | None:
        async with self._uow_factory(readonly=True) as uow:
            assert uow.user_repository is not None
            user = await uow.user_repository.get_by_id(user_id)
            return UserRead.model_validate(user) if user else None

    async def update(self, user_id: int, payload: UserUpdate) -> UserRead | None:
        async with self._uow_factory() as uow:
            assert uow.user_repository is not None
            data = payload.model_dump(exclude_unset=True)
            user = await uow.user_repository.update_full_name(user_id, data.get("full_name"))
            return UserRead.model_validate(user) if user else None
```

### 6) 控制器（controllers/user_controller.py）

```python
from fastapi import HTTPException, status
from application.dtos.users import UserCreate, UserUpdate, UserRead
from application.services.user_service import UserApplicationService, ConflictError


class UserController:
    def __init__(self, service: UserApplicationService) -> None:
        self._service = service

    async def create(self, payload: UserCreate) -> UserRead:
        try:
            return await self._service.create(payload)
        except ConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    async def get(self, user_id: int) -> UserRead:
        user = await self._service.get(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    async def update(self, user_id: int, payload: UserUpdate) -> UserRead:
        user = await self._service.update(user_id, payload)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user
```

### 7) 路由（api/routes/user.py）

```python
from fastapi import APIRouter, Depends, status
from typing import Annotated
from application.dtos.users import UserCreate, UserUpdate, UserRead
from application.services.user_service import UserApplicationService
from controllers.user_controller import UserController
from infrastructure.unit_of_work import SQLAlchemyUnitOfWork


router = APIRouter(prefix="/users", tags=["Users"])


def get_user_service() -> UserApplicationService:
    return UserApplicationService(uow_factory=SQLAlchemyUnitOfWork)


def get_user_controller(service: Annotated[UserApplicationService, Depends(get_user_service)]) -> UserController:
    return UserController(service)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, controller: Annotated[UserController, Depends(get_user_controller)]):
    return await controller.create(payload)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: int, controller: Annotated[UserController, Depends(get_user_controller)]):
    return await controller.get(user_id)


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(user_id: int, payload: UserUpdate, controller: Annotated[UserController, Depends(get_user_controller)]):
    return await controller.update(user_id, payload)
```

---

## 从“路由塞满业务”到“分层架构”的重构

### BEFORE（反例，路由塞满业务）

```python
@router.post("/users")
async def create_user(payload: dict):
    # 直接访问数据库/密码散列/校验/错误处理都在路由里
    ...  # 200+ 行
```

### AFTER（清晰分层）

```python
@router.post("/users")
async def create_user(payload: UserCreate, controller: Annotated[UserController, Depends(get_user_controller)]):
    return await controller.create(payload)
```

收益：
- 可测试：Service/Repository 独立单测，路由仅做薄委派
- 可维护：HTTP 语义与业务逻辑解耦
- 可扩展：Service 可复用至 CLI/cron/WebSocket/GRPC 等

---

## 文件域（分页 + 统一响应包）示例

参考 fastapi-forge 的 `core/response.py`，使用统一响应包与分页：

```python
from fastapi import APIRouter, Depends, Query
from core.response import Response as ApiResponse, PaginatedData, paginated_response
from application.dto import FileAssetDTO

router = APIRouter(prefix="/files", tags=["Files"])


@router.get("", response_model=ApiResponse[PaginatedData[FileAssetDTO]])
async def list_files(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100), service: FileAssetApplicationService = Depends(get_file_asset_service)):
    assets, total = await service.list_assets(skip=(page - 1) * size, limit=size)
    return paginated_response(assets, total, page, size)
```

