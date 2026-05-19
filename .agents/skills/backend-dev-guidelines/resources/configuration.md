# 配置管理 - pydantic-settings 统一配置

Python 的 pydantic-settings, 目标：类型安全、单一来源、启动时校验、可测试/可覆盖

## 目录

- 原则与反模式
- Settings 结构设计（分组与嵌套）
- 加载与校验（.env/环境变量/默认值）
- 列表/复杂类型解析（CORS/嵌套 env）
- 依赖注入与测试覆盖
- 运行时配置与安全（Secrets/Sentry/密钥）
- 数据库 URL 与异步驱动转换
- 日志与观测性配置
- 生产部署与 K8s/Docker 示例

---

## 原则与反模式

- 统一入口：使用 `Settings` 作为全局配置，不在业务中直接 `os.getenv`。
- 类型与校验：字段使用类型注解与 `Field` 约束；关键配置在启动时校验。
- 可覆盖：测试/本地通过 .env 或依赖覆盖方式注入。

反模式（避免）：
- ❌ 在各处直接 `os.getenv('X')`
- ❌ 运行时才发现变量拼写错误/类型转换错误
- ❌ 在库文件导入时副作用加载大量环境变量

---

## Settings 结构设计（分组与嵌套）


```python
# core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional

class DatabaseSettings(BaseModel):
    url: str = "postgresql+asyncpg://user:password@localhost/app"

class RedisSettings(BaseModel):
    url: Optional[str] = None
    max_connections: int = 10
    default_ttl: int = 300
    namespace: str = "fastapi-app"

class StorageSettings(BaseModel):
    type: str = "local"
    bucket: Optional[str] = None
    region: Optional[str] = None
    endpoint: Optional[str] = None
    local_base_path: str = "/tmp/storage"

class GrpcSettings(BaseModel):
    enabled: bool = False
    host: str = "0.0.0.0"
    port: int = 50051

class Settings(BaseSettings):
    PROJECT_NAME: str = Field(default="FastAPI DDD App", env=["PROJECT_NAME", "APP_NAME"]) 
    VERSION: str = Field(default="1.0.0", env=["VERSION", "APP_VERSION"]) 
    DEBUG: bool = Field(default=True, env="DEBUG")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")

    SECRET_KEY: str = Field(..., description="JWT/签名密钥")

    CORS_ORIGINS: list[str] = Field(default=["http://localhost:3000"], env="CORS_ORIGINS")

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    grpc: GrpcSettings = Field(default_factory=GrpcSettings)

    DEFAULT_PAGE_SIZE: int = Field(default=20, env="DEFAULT_PAGE_SIZE")
    MAX_PAGE_SIZE: int = Field(default=100, env="MAX_PAGE_SIZE")

    SENTRY_DSN: Optional[str] = None
    SENTRY_TRACES_SAMPLE_RATE: float = 0.0

    LOG_REQUEST_BODY_ENABLE_BY_DEFAULT: bool = Field(default=True)
    LOG_REQUEST_BODY_MAX_BYTES: int = Field(default=2048)
    LOG_REQUEST_BODY_ALLOW_MULTIPART: bool = Field(default=False)

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="allow",
        env_nested_delimiter="__",
    )

    @model_validator(mode="after")
    def _validate_secret_key(self):
        if not self.SECRET_KEY:
            raise ValueError("SECRET_KEY 未配置。请设置 SECRET_KEY 或 JWT_SECRET_KEY")
        return self

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v):
        # 支持 JSON 字符串或逗号分隔字符串
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            s = v.strip()
            if s.startswith("[") and s.endswith("]"):
                import json
                try:
                    arr = json.loads(s)
                    if isinstance(arr, list):
                        return arr
                except Exception:
                    pass
            if "," in s:
                return [item.strip() for item in s.split(",") if item.strip()]
            return [s] if s else []
        return v

settings = Settings()
```

嵌套结构可通过 `ENV_NESTED__FIELD=value` 写入：

```
DATABASE__URL=postgresql+asyncpg://user:pass@db/app
REDIS__URL=redis://localhost:6379/0
```

---

## 加载与校验（.env/环境变量/默认值）

加载顺序：环境变量 > `.env` > 默认值。对关键项（如 `SECRET_KEY`）在启动时强制校验；对允许缺省的项提供安全默认（如日志开关）。

`.env` 示例：

```
PROJECT_NAME="FastAPI DDD App"
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=please-change-me
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
DATABASE__URL=postgresql+asyncpg://user:password@localhost/app
SENTRY_DSN=
SENTRY_TRACES_SAMPLE_RATE=0.1
DEFAULT_PAGE_SIZE=20
MAX_PAGE_SIZE=100
```

---

## 列表/复杂类型解析（CORS/嵌套 env）

- 列表：支持 JSON 数组或逗号分隔字符串（见 `CORS_ORIGINS` 解析器）。
- 嵌套：通过 `env_nested_delimiter="__"` 设置，从环境变量注入子模型字段。
- Secret：敏感值不应出现在仓库，生产通过平台 Secret 管理或环境注入。

---

## 依赖注入与测试覆盖

注入配置：

```python
from functools import lru_cache

@lru_cache
def get_settings() -> Settings:
    return Settings()

# 路由/依赖中按需获取
def get_page_size(settings: Settings = Depends(get_settings)) -> int:
    return settings.DEFAULT_PAGE_SIZE
```

测试覆盖：

```python
def test_overrides(app):
    from backend.core.config import Settings
    def _test_settings():
        s = Settings()
        s.SECRET_KEY = "test-secret"
        s.DEFAULT_PAGE_SIZE = 5
        return s
    app.dependency_overrides[get_settings] = _test_settings
```

提示：fastapi-forge 直接实例化 `settings = Settings()`，如需懒加载/隔离测试，采用 `get_settings()` 工厂并在测试中覆盖。

---

## 运行时配置与安全（Secrets/Sentry/密钥）

- 关键密钥（`SECRET_KEY`、数据库凭据、云存储密钥）通过环境变量注入；不要提交到代码库。
- Sentry 相关采样率/DSN 放在 Settings 中，按环境覆盖。
- 生产环境使用平台 Secret：Kubernetes Secret、Docker Swarm Secret、AWS SSM/Secrets Manager、Vault。

---

## 数据库 URL 与异步驱动转换

确保数据库 URL 使用异步驱动，参考 fastapi-forge：

```python
# infrastructure/database.py（节选）
from sqlalchemy.engine import make_url

def _build_async_url(database_url: str) -> str:
    url = make_url(database_url)
    if "+" in url.drivername:
        return database_url
    driver_map = {
        "postgresql": "postgresql+asyncpg",
        "postgres": "postgresql+asyncpg",
        "mysql": "mysql+aiomysql",
        "sqlite": "sqlite+aiosqlite",
    }
    if url.drivername not in driver_map:
        raise ValueError(f"不支持的数据库驱动: {url.drivername}")
    return str(url.set(drivername=driver_map[url.drivername]))
```

---

## 日志与观测性配置

- 在 Settings 中集中配置日志相关开关（是否记录请求体、截断大小、是否允许 multipart）。
- 结构化日志输出（建议 structlog/loguru 或标准 logging + JSONFormatter）。
- Sentry/OTel 采样率、服务标签等也纳入配置，便于环境切换。

---

## 生产部署与 K8s/Docker 示例

Docker Compose：

```yaml
services:
  api:
    image: your/app:latest
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE__URL=${DATABASE_URL}
      - CORS_ORIGINS=["https://your.app"]
      - SENTRY_DSN=${SENTRY_DSN}
    ports: ["8000:8000"]
```

Kubernetes（片段）：

```yaml
env:
  - name: ENVIRONMENT
    value: production
  - name: SECRET_KEY
    valueFrom:
      secretKeyRef:
        name: api-secrets
        key: secret_key
  - name: DATABASE__URL
    valueFrom:
      secretKeyRef:
        name: api-secrets
        key: database_url
```


