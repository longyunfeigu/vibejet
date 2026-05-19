# 校验模式 - Pydantic/FastAPI 最佳实践

将基于 Zod 的 TypeScript 校验模式等价映射为 Python/Pydantic（v2）与 FastAPI 实现。聚焦生产可用的 DTO 设计、请求参数约束、部分更新、判别联合类型、自定义校验与序列化，以及与 fastapi-forge 的对齐方式。

## 目录

- 为什么选 Pydantic（v2）
- 基础模式：字段类型与约束
- DTO 分层：Create/Update/Read
- 路由级校验 vs 控制器/服务模式
- 查询/路径参数校验（Query/Path/Body/Depends）
- 错误处理与消息定制
- 高级模式：判别联合/转换/序列化/部分更新
- 分页与通用泛型响应
- 与 fastapi-forge 对齐要点

---

## 为什么选 Pydantic（v2）

优势：
- 类型安全：Python 类型提示 + 运行时校验
- 生态融合：FastAPI 深度集成，自动文档与 422 错误
- 体验友好：`Field` 约束、`field_validator`/`model_validator`、`Annotated` 支持
- 性能优化：v2 内核更快，序列化/校验更高效

---

## 基础模式：字段类型与约束

常用类型：

```python
from pydantic import BaseModel, Field, EmailStr, AnyUrl, HttpUrl, SecretStr
from typing import Optional, Literal
from uuid import UUID

class UserCreate(BaseModel):
    email: EmailStr
    password: SecretStr = Field(min_length=8)
    nickname: Optional[str] = Field(None, min_length=2, max_length=50)
    role: Literal["admin", "operations", "user"] = "user"
    homepage: Optional[HttpUrl] = None
    ref_id: Optional[UUID] = None
```

数值/字符串约束与正则：

```python
class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    price_cents: int = Field(ge=0, le=10_000_000)
    currency: Literal["USD", "CNY", "EUR"]
    sku: str = Field(pattern=r"^[A-Z0-9\-]{8,32}$")
```

时间类型与时区序列化（统一 ISO8601）：

```python
from pydantic import BaseModel
from pydantic import field_validator, model_serializer
from datetime import datetime, timezone

class DTOBase(BaseModel):
    @model_serializer(mode="wrap")
    def _serialize_model(self, handler):  # 统一转换为 UTC Z 后缀
        data = handler(self)
        def to_utc_z(v):
            if isinstance(v, datetime):
                ts = v if v.tzinfo else v.replace(tzinfo=timezone.utc)
                s = ts.astimezone(timezone.utc).isoformat()
                return s.replace("+00:00", "Z")
            if isinstance(v, list):
                return [to_utc_z(i) for i in v]
            if isinstance(v, dict):
                return {k: to_utc_z(i) for k, i in v.items()}
            return v
        return to_utc_z(data)
```

模型配置：

```python
from pydantic import ConfigDict

class StrictDTO(DTOBase):
    model_config = ConfigDict(
        extra="forbid",            # 禁止未知字段
        populate_by_name=True,      # 支持别名反序列化
        str_strip_whitespace=True,  # 默认裁剪字符串首尾空白
    )
```

---

## DTO 分层：Create/Update/Read

拆分输入输出，防止敏感信息泄漏并简化部分更新：

```python
from pydantic import BaseModel, Field, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: Optional[str] = Field(None, max_length=100)

class UserUpdate(BaseModel):  # 部分更新，字段可选
    full_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, pattern=r"^1[3-9]\d{9}$")

class UserRead(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str]
    is_active: bool = True
    model_config = {"from_attributes": True}  # ORM 模式
```

服务层处理部分更新：

```python
data = update_dto.model_dump(exclude_unset=True)
# 仅包含用户提交的字段，安全合并到实体/仓储层
```

---

## 路由级校验 vs 控制器/服务模式

FastAPI 默认对请求体/查询/路径参数进行 Pydantic 校验：

```python
from fastapi import APIRouter, Query, Path

router = APIRouter()

@router.get("/items/{item_id}")
async def get_item(
    item_id: int = Path(ge=1),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    ...
```

推荐：
- 路由层：定义参数与基本约束、委派控制器/服务
- 控制器：做 HTTP 语义映射（404/409 等）
- 服务：承载业务规则与事务

---

## 查询/路径参数校验（Query/Path/Body/Depends）

组合 DTO 与 Depends 提升复用性：

```python
from fastapi import Depends, Query
from pydantic import BaseModel, Field

class Pagination(BaseModel):
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)

def get_pagination(
    page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100)
) -> Pagination:
    return Pagination(page=page, size=size)

@router.get("/users")
async def list_users(p: Pagination = Depends(get_pagination)):
    skip = (p.page - 1) * p.size
    limit = p.size
    ...
```

---

## 错误处理与消息定制

FastAPI 对校验失败返回 422。可自定义 Pydantic 校验消息：

```python
from pydantic import BaseModel, Field, field_validator

class ChangePassword(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)

    @field_validator("new_password")
    def strong(cls, v: str):
        if not any(c.isupper() for c in v):
            raise ValueError("需包含大写字母")
        if not any(c.islower() for c in v):
            raise ValueError("需包含小写字母")
        if not any(c.isdigit() for c in v):
            raise ValueError("需包含数字")
        return v
```

全局异常处理建议：将领域异常（Conflict/NotFound 等）映射为 HTTP 状态；校验异常通常维持默认 422，或统一包裹为响应结构（参考 fastapi-forge 的 `core/response.py`）。

---

## 高级模式：判别联合/转换/序列化/部分更新

判别联合（discriminated union）：

```python
from typing import Annotated, Union
from pydantic import BaseModel, Field

class EmailNotification(BaseModel):
    type: Literal["email"]
    recipient: EmailStr
    subject: str

class SMSNotification(BaseModel):
    type: Literal["sms"]
    phone_number: str
    message: str

Notification = Annotated[Union[EmailNotification, SMSNotification], Field(discriminator="type")]
```

数据转换（pre/post）：

```python
from pydantic import BaseModel, field_validator, model_validator

class TrimmedUser(BaseModel):
    email: EmailStr
    name: str

    @field_validator("name", mode="before")
    def trim_name(cls, v):
        return v.strip() if isinstance(v, str) else v

    @model_validator(mode="after")
    def ensure_business_rules(self):
        # 复杂跨字段校验
        return self
```

序列化：统一时间/别名/排除敏感字段：

```python
user_read = UserRead.model_validate(user_orm)
payload = user_read.model_dump(by_alias=True, exclude={"internal_note"})
```

部分更新（PATCH）：

```python
class UserPatch(BaseModel):
    full_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, pattern=r"^1[3-9]\d{9}$")

changes = UserPatch(**incoming).model_dump(exclude_unset=True)
# 仅提交的字段将被应用
```

---

## 分页与通用泛型响应

分页 DTO（运行时默认值来自应用配置，参考 fastapi-forge）：

```python
from pydantic import BaseModel, Field, ConfigDict, model_validator

class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1)

    @model_validator(mode="after")
    def clamp(self):
        try:
            from core.config import settings
            if self.size > settings.MAX_PAGE_SIZE:
                self.size = settings.MAX_PAGE_SIZE
        except Exception:
            pass
        return self
```

泛型响应包（与 fastapi-forge `core/response.py` 思路一致）：

```python
from typing import Generic, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    message: Optional[str] = None
```



实践建议：
- 默认 `extra="forbid"` 禁止未知字段；前端 schema 变更需显式跟进
- 输入/输出 DTO 分离；敏感字段仅在输入中出现，输出严格白名单
- PATCH/UPDATE 分离：PATCH 采用 `exclude_unset=True`，UPDATE 采用完整字段替换
- 判别联合用于多渠道/多类型输入；保持 `type` 字段稳定
- 使用 `EmailStr/HttpUrl/UUID/SecretStr` 等强类型，减少手写正则

