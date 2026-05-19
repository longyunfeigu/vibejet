# 路由与控制器 - FastAPI 最佳实践

面向生产的 FastAPI 路由与控制器模式，等价映射自 TypeScript 指南并结合 fastapi-forge 的落地经验。

## 目录

- 路由层只做“路由”
- 控制器模式（为何以及如何）
- 两种返回风格：数据模型 vs 统一响应包
- 依赖注入与中间件顺序
- 错误处理与 Sentry 集成
- 良好示例（可直接使用）
- 反模式与重构步骤
- HTTP 状态与文档设置

---

## 路由层只做“路由”

黄金法则：
- 路由层只应负责：定义路径/方法、注册依赖/中间件、委派到控制器
- 路由层不应包含：业务逻辑、数据库访问、复杂响应装配、权限/事务编排

清洁路由示例：

```python
# api/routes/user.py
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from typing import Annotated

from api.dependencies import get_user_service
from application.dtos.users import UserCreate, UserRead
from application.services.user_service import UserService
from controllers.user_controller import UserController

router = APIRouter(prefix="/users", tags=["Users"])


def get_user_controller(
    service: Annotated[UserService, Depends(get_user_service)]
) -> UserController:
    return UserController(service)


@router.get(
    "/{user_id}",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Get user by id",
)
async def get_user(
    user_id: int,
    controller: Annotated[UserController, Depends(get_user_controller)],
):
    return await controller.get(user_id)


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
)
async def create_user(
    payload: UserCreate,
    controller: Annotated[UserController, Depends(get_user_controller)],
):
    return await controller.create(payload)
```

关键点：
- 每个路由仅定义方法/路径/依赖和委派；不出现 try/except、数据库调用、业务判断
- `response_model` 由 Pydantic 定义，自动生成文档并保证输出类型
- 依赖注入通过 `Depends` 装配 Service/Controller，便于测试与替换

---

## 控制器模式（为何以及如何）

在 FastAPI 中，路由函数已足够精简；但对于中大型项目，控制器能提供：
- 统一的 HTTP 语义（状态码、响应结构、错误映射）
- 更可测：Controller 与 Service 可独立单测
- 易于复用：同一 Controller 可服务于 HTTP、WebSocket、CLI、任务处理等场景

薄控制器（推荐，返回数据模型）：

```python
# controllers/user_controller.py
from fastapi import HTTPException, status
from application.dtos.users import UserCreate, UserRead
from application.services.user_service import UserService, ConflictError


class NotFoundError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message


class UserController:
    def __init__(self, service: UserService) -> None:
        self._service = service

    async def get(self, user_id: int) -> UserRead:
        user = await self._service.get(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    async def create(self, payload: UserCreate) -> UserRead:
        try:
            return await self._service.create(payload)
        except ConflictError as exc:
            # 将领域冲突映射为 409
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
```

厚控制器（可选，返回统一响应包）：

```python
from fastapi.responses import JSONResponse


class BaseController:
    def ok(self, data, message: str | None = None, status_code: int = 200) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"success": True, "message": message, "data": data})

    def fail(self, message: str, status_code: int = 400) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"success": False, "error": {"message": message}})
```

选择建议：
- 若团队偏好“裸数据 + response_model” → 薄控制器（更 Pythonic，直接复用 Pydantic 模型）
- 若团队需要统一响应包（success/data/message） → 厚控制器 + `core/response.py`（参考 fastapi-forge）

---

## 两种返回风格：数据模型 vs 统一响应包

- 数据模型：
  - 路由设置 `response_model=UserRead`，控制器返回 `UserRead`
  - FastAPI 自动序列化/文档生成
  - 简洁、测试友好

- 统一响应包：
  - 路由设置 `response_model=ApiResponse[UserRead]`（泛型响应）
  - 控制器使用 `success_response()/paginated_response()`（参考 fastapi-forge 的 `core/response.py`）
  - 易于前后端对齐响应结构与错误语义

两者请择一贯穿项目，避免混用。

---

## 依赖注入与中间件顺序

- `Depends` 在路由/控制器/服务边界装配依赖（鉴权、配置、Service、UoW、外部适配器）
- 路由级依赖：`APIRouter(..., dependencies=[Depends(get_current_user)])` 用于强制鉴权
- 全局中间件添加顺序即请求进入顺序（响应回卷逆序）；错误处理器应在路由完成后生效

示例（强制鉴权与分页参数校验）：

```python
# 强制所有 /files 接口鉴权
router = APIRouter(prefix="/files", tags=["Files"], dependencies=[Depends(get_current_user)])

@router.get("", summary="List files")
async def list_files(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100)):
    ...
```

---

## 错误处理与 Sentry 集成

将领域异常映射为 HTTP 语义，并统一上报：

```python
# main.py（节选）
import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from core.config import settings

app = FastAPI(title=settings.PROJECT_NAME, debug=settings.DEBUG)

sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE)


class ConflictError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message


@app.exception_handler(ConflictError)
async def conflict_handler(_: Request, exc: ConflictError):
    sentry_sdk.capture_exception(exc)
    return JSONResponse(status_code=409, content={"detail": exc.message})

# 其他异常（如 ValidationError）由 FastAPI/Starlette 内置处理
```

要点：
- 业务层抛出领域异常（如 `ConflictError`、`NotFoundError`），由异常处理器统一转换
- 控制器尽量不直接 `JSONResponse`，除非采用统一响应包策略

---

## 良好示例（可直接使用）

示例 1：用户路由（薄控制器 + 数据模型风格）

```python
# application/dtos/users.py
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

```python
# application/services/user_service.py（节选）
from application.dtos.users import UserCreate, UserRead


class ConflictError(Exception):
    pass


class UserService:
    async def get(self, user_id: int) -> UserRead | None:
        ...  # 访问仓储

    async def create(self, payload: UserCreate) -> UserRead:
        ...  # 冲突检测 + 持久化
```

```python
# controllers/user_controller.py（节选）
from fastapi import HTTPException, status
from application.dtos.users import UserCreate, UserRead
from application.services.user_service import UserService, ConflictError


class UserController:
    def __init__(self, service: UserService) -> None:
        self._service = service

    async def get(self, user_id: int) -> UserRead:
        user = await self._service.get(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    async def create(self, payload: UserCreate) -> UserRead:
        try:
            return await self._service.create(payload)
        except ConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
```

```python
# api/routes/user.py（路由层）
from fastapi import APIRouter, Depends, status
from typing import Annotated

from api.dependencies import get_user_service
from application.dtos.users import UserCreate, UserRead
from application.services.user_service import UserService
from controllers.user_controller import UserController

router = APIRouter(prefix="/users", tags=["Users"])


def get_user_controller(service: Annotated[UserService, Depends(get_user_service)]) -> UserController:
    return UserController(service)


@router.get("/{user_id}", response_model=UserRead, status_code=status.HTTP_200_OK)
async def get_user(user_id: int, controller: Annotated[UserController, Depends(get_user_controller)]):
    return await controller.get(user_id)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, controller: Annotated[UserController, Depends(get_user_controller)]):
    return await controller.create(payload)
```

示例 2：文件列表（统一响应包 + 分页，参考 fastapi-forge）

```python
# api/routes/files.py（思路）
@router.get(
    "",
    summary="文件列表",
    response_model=ApiResponse[PaginatedData[FileAssetDTO]],
)
async def list_files(
    page: int = Query(1, ge=1),
    size: int = Query(default=settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE),
    current_user: UserResponseDTO = Depends(get_current_active_user),
    service: FileAssetApplicationService = Depends(get_file_asset_service),
):
    # 路由层：仅参数与委派
    assets, total = await service.list_assets(owner_id=current_user.id, skip=(page-1)*size, limit=size)
    return paginated_response(items=assets, total=total, page=page, size=size)
```

---

## 反模式与重构步骤

反模式（应避免）：
- 在路由中堆积业务逻辑（>50 行、多个条件/循环/权限/事务）
- 直接在路由中访问数据库/Session
- 路由中 try/except 大量分支处理错误
- 控制器返回裸 ORM 实体（无 DTO/Schema）

重构步骤：
1) 从路由抽出控制器方法；路由变为简单委派
2) 从控制器抽出业务到 Service；控制器只做装配/错误映射
3) 引入 Repository；Service 不再直接操作 ORM
4) 若需要统一响应包，引入 `BaseController` 或 `core/response.py`
5) 引入全局异常处理器，映射领域异常到 HTTP 状态

---

## HTTP 状态与文档设置

- 常用状态：200 OK、201 Created、204 No Content、400 Bad Request、401/403、404、409、422、500
- 文档设置：`summary`、`description`、`tags`、`responses`、`deprecated`、`operation_id`

示例：

```python
@router.put(
    "/{user_id}",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Update user",
    description="Update basic user profile fields.",
    responses={404: {"description": "User not found"}},
)
async def update_user(...):
    ...
```

---

## 实践建议：
- 统一采用“薄控制器 + Pydantic 模型”的默认风格；在确有需要时再引入统一响应包
- 以 Service 为事务/业务边界；路由/控制器不直接感知数据库/缓存
- 使用 `Depends` 显式装配依赖，提升可测试性与可替换性

