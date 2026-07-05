# input: 环境变量 / backend/.env（SECRET_KEY 必填且须为强随机值，嵌套键如 DATABASE__URL）
# output: settings 全局配置对象, Settings 及各分组配置类, MIN_SECRET_KEY_LENGTH
# pos: 核心配置 - 配置管理与启动期 fail-fast 校验（弱 SECRET_KEY/生产 DEBUG 拒绝启动）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""
配置文件 - 项目配置管理
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import AliasChoices, BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class GrpcTlsSettings(BaseModel):
    enabled: bool = False
    cert: Optional[str] = None
    key: Optional[str] = None
    ca: Optional[str] = None


class GrpcSettings(BaseModel):
    enabled: bool = False
    host: str = "0.0.0.0"  # nosec B104
    port: int = 50051
    # This maps to GRPC option grpc.max_concurrent_streams
    max_concurrent_streams: int = 100
    # SIGTERM/SIGINT 后等待在途 RPC 完成的宽限期；须小于编排器的
    # 强杀等待（docker stop 默认 10s）
    shutdown_grace_seconds: float = 5.0
    tls: GrpcTlsSettings = Field(default_factory=GrpcTlsSettings)


class KafkaSettings(BaseModel):
    # Provider/driver
    provider: str = Field(default="kafka")
    driver: str = Field(default="confluent")  # confluent or aiokafka

    # Core Kafka
    bootstrap_servers: str = Field(default="localhost:9092")
    client_id: str = Field(default="app-messaging")
    transactional_id: Optional[str] = None

    # TLS
    tls_enable: bool = False
    tls_ca_location: Optional[str] = None
    tls_certificate: Optional[str] = None
    tls_key: Optional[str] = None
    tls_verify: bool = True

    # SASL
    sasl_mechanism: Optional[str] = None
    sasl_username: Optional[str] = None
    sasl_password: Optional[str] = None

    # Producer tuning
    producer_acks: str = "all"
    producer_enable_idempotence: bool = True
    producer_compression_type: str = "zstd"
    producer_linger_ms: int = 5
    producer_batch_size: int = 64 * 1024
    producer_max_in_flight: int = 5
    producer_message_timeout_ms: int = 120_000
    producer_send_wait_s: float = 5.0
    producer_delivery_wait_s: float = 30.0

    # Consumer tuning
    consumer_enable_auto_commit: bool = False
    consumer_auto_offset_reset: str = "latest"
    consumer_max_poll_interval_ms: int = 300000
    consumer_session_timeout_ms: int = 45000
    consumer_fetch_min_bytes: int = 1
    consumer_fetch_max_bytes: int = 50 * 1024 * 1024
    consumer_commit_every_n: int = 100
    consumer_commit_interval_ms: int = 2000
    consumer_max_concurrency: int = 1
    consumer_inflight_max: int = 1000

    # Retry policy
    retry_layers: Optional[str] = "retry.5s:5000,retry.1m:60000,retry.10m:600000"
    retry_dlq_suffix: str = "dlq"


class RedisSettings(BaseModel):
    url: Optional[str] = None
    max_connections: int = 10
    default_ttl: int = 300
    namespace: str = "vibejet"
    # 初始化失败时 fail-fast（True）还是降级继续启动（False）
    required: bool = False


class IdempotencySettings(BaseModel):
    lock_ttl_seconds: int = 30
    result_ttl_seconds: int = 24 * 60 * 60


class DatabaseSettings(BaseModel):
    url: str = "postgresql+asyncpg://user:password@localhost/userdb"
    # 连接池（仅网络型数据库生效，SQLite 忽略；见 infrastructure/database.py）。
    # 容量公式：WORKERS × (pool_size + max_overflow) 必须小于数据库 max_connections。
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: float = 30.0
    # pre_ping 在取出连接时探活（代价极小），配合 recycle 兜住服务端空闲超时/
    # 故障切换后的死连接；recycle 需低于服务端/代理的空闲断链阈值
    pool_pre_ping: bool = True
    pool_recycle: int = 1800


class LLMSettings(BaseModel):
    provider: str = "openai"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    default_model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 60
    max_retries: int = 2
    # 初始化失败时 fail-fast（True）还是降级继续启动（False）
    required: bool = False


class StorageSettings(BaseModel):
    type: str = "local"  # local, s3, oss
    bucket: Optional[str] = None
    region: Optional[str] = None
    endpoint: Optional[str] = None
    public_base_url: Optional[str] = None
    # S3 specific
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    s3_sse: Optional[str] = None
    s3_acl: str = "private"
    # OSS specific
    oss_access_key_id: Optional[str] = None
    oss_access_key_secret: Optional[str] = None
    # Local storage specific
    local_base_path: str = "/tmp/storage"  # nosec B108
    # Advanced settings
    max_retry_attempts: int = 3
    timeout: int = 30
    enable_ssl: bool = True
    # 上传校验分两套：presign_*（客户端直传，签名即授权，故始终生效）；
    # validation_enabled + max_file_size/allowed_types（服务端中转，请求体已在网关/服务器
    # 层受限，默认关闭按需开启）。两套阈值独立，不共用。
    presign_max_size: int = 100 * 1024 * 1024  # 100MB
    presign_content_types: Optional[list[str]] = None
    validation_enabled: bool = False
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    allowed_types: Optional[list[str]] = None
    # 初始化失败时 fail-fast（True）还是降级继续启动（False）
    required: bool = False


class DocumentSettings(BaseModel):
    """文档解析配置：解析器二选一（环境变量 DOCUMENT__PARSER），不混用、不静默降级。"""

    parser: str = "markitdown"  # markitdown | textin
    # 单文件解析输入上限（防止超大文件拖垮 worker / 烧穿按页计费额度）
    max_parse_bytes: int = 50 * 1024 * 1024  # 50MB
    # parsing 状态超过该秒数视为孤儿任务（如进程重启丢失 BackgroundTasks），
    # 允许 reparse 强制恢复
    parsing_stale_seconds: int = 900
    # markitdown 本地转换超时（应明显小于 parsing_stale_seconds）
    markitdown_timeout: int = 600
    # 初始化失败时 fail-fast（True）还是降级继续启动（False）
    required: bool = False
    # TextIn 凭证（仅 parser=textin 时必填；长期有效，无刷新逻辑）
    textin_app_id: Optional[str] = None
    textin_secret_code: Optional[str] = None
    textin_base_url: str = "https://api.textin.com"
    textin_timeout: int = 120

    @model_validator(mode="after")
    def _validate_parser(self):
        allowed = {"markitdown", "textin"}
        if self.parser not in allowed:
            raise ValueError(f"DOCUMENT__PARSER 必须是 {sorted(allowed)} 之一，当前: {self.parser}")
        if self.parser == "textin" and not (self.textin_app_id and self.textin_secret_code):
            raise ValueError(
                "DOCUMENT__PARSER=textin 需要同时配置 "
                "DOCUMENT__TEXTIN_APP_ID 和 DOCUMENT__TEXTIN_SECRET_CODE"
            )
        return self


class AuthSettings(BaseModel):
    # JWT 签名使用顶层 SECRET_KEY
    algorithm: str = "HS256"
    access_token_ttl_seconds: int = 30 * 60
    refresh_token_ttl_seconds: int = 7 * 24 * 60 * 60


class MetricsSettings(BaseModel):
    enabled: bool = False
    access_token: Optional[str] = None


class TracingSettings(BaseModel):
    enabled: bool = False
    exporter: str = "console"
    otlp_endpoint: Optional[str] = None
    sample_rate: float = 1.0
    expose_trace_id: bool = False


class HealthSettings(BaseModel):
    db_timeout_seconds: float = 5.0
    redis_timeout_seconds: float = 3.0
    storage_timeout_seconds: float = 5.0
    include_details: bool = False
    access_token: Optional[str] = None


# SECRET_KEY 硬门槛：HS256 需要足够熵，32 字符起步（openssl rand -hex 32 → 64 字符）
MIN_SECRET_KEY_LENGTH = 32
# 公开模板/文档里出现过的默认值与常见占位词，出现即拒绝启动（小写比较）
_KNOWN_WEAK_SECRET_KEYS = frozenset(
    {
        "your-secret-key-here",
        "your-secret-key-here-change-in-production",
        "your-secret-key",
        "change-me",
        "changeme",
        "secret",
        "secret-key",
        "password",
        "dev-secret",
        "test-secret",
        "test-secret-key",
    }
)


class Settings(BaseSettings):
    """项目配置"""

    # 基础配置
    PROJECT_NAME: str = Field(
        default="FastAPI DDD Framework",
        validation_alias=AliasChoices("PROJECT_NAME", "APP_NAME"),
    )
    VERSION: str = Field(default="1.0.0", validation_alias=AliasChoices("VERSION", "APP_VERSION"))
    # 缺省关闭：debug 响应体会携带 traceback，绝不能靠"忘了配"就在生产开着
    DEBUG: bool = Field(default=False, validation_alias=AliasChoices("DEBUG"))
    ENVIRONMENT: str = Field(default="development", validation_alias=AliasChoices("ENVIRONMENT"))
    AUTO_RUN_MIGRATIONS: bool = Field(
        default=False, validation_alias=AliasChoices("AUTO_RUN_MIGRATIONS")
    )

    # Server（用于 uvicorn / 部署脚本）
    HOST: str = Field(default="0.0.0.0", validation_alias=AliasChoices("HOST"))  # nosec B104
    PORT: int = Field(default=8000, validation_alias=AliasChoices("PORT"))
    RELOAD: bool = Field(default=False, validation_alias=AliasChoices("RELOAD"))
    WORKERS: int = Field(default=1, validation_alias=AliasChoices("WORKERS"))

    # 分组配置（方案A）：Kafka/Redis/Database/Storage 采用嵌套模型（外部类）
    kafka: KafkaSettings = Field(default_factory=KafkaSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    idempotency: IdempotencySettings = Field(default_factory=IdempotencySettings)

    # 安全配置
    SECRET_KEY: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("SECRET_KEY"),
        description="应用密钥，生产环境必须设置",
    )

    # Google 登录（OAuth 授权码流）：Web 类型 OAuth Client。
    # 前端拿 authorization code，后端用 id+secret 去 Google token 端点换 id_token 后验签。
    # 需 GOOGLE_CLIENT_ID 与 GOOGLE_CLIENT_SECRET 同时配置，缺任一则 Google 登录不可用。
    GOOGLE_CLIENT_ID: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("GOOGLE_CLIENT_ID"),
        description="Google OAuth Web Client ID，用于校验 ID Token 的 aud",
    )
    GOOGLE_CLIENT_SECRET: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("GOOGLE_CLIENT_SECRET"),
        description="Google OAuth Web Client Secret，用于授权码换 token（仅后端持有）",
    )
    GOOGLE_OAUTH_REDIRECT_URI: str = Field(
        default="postmessage",
        validation_alias=AliasChoices("GOOGLE_OAUTH_REDIRECT_URI"),
        description="授权码换 token 的 redirect_uri；@react-oauth/google popup 模式固定为 'postmessage'",
    )

    # 飞书登录（OAuth 授权码流，open.feishu.cn）：自建应用 App ID/Secret。
    # 前端整页跳转授权页拿 code，后端用 id+secret 去 v2 token 端点换 access_token 后调 user_info。
    # 需 FEISHU_APP_ID 与 FEISHU_APP_SECRET 同时配置，缺任一则飞书登录不可用。
    FEISHU_APP_ID: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("FEISHU_APP_ID"),
        description="飞书自建应用 App ID",
    )
    FEISHU_APP_SECRET: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("FEISHU_APP_SECRET"),
        description="飞书自建应用 App Secret（仅后端持有）",
    )
    FEISHU_OAUTH_REDIRECT_URI: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("FEISHU_OAUTH_REDIRECT_URI"),
        description="授权码换 token 的 redirect_uri，须与飞书开放平台控制台注册的回调地址一致",
    )

    # Lark 国际登录（OAuth 授权码流，open.larksuite.com）：与飞书同形，独立 app 注册。
    LARK_APP_ID: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("LARK_APP_ID"),
        description="Lark 自建应用 App ID",
    )
    LARK_APP_SECRET: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("LARK_APP_SECRET"),
        description="Lark 自建应用 App Secret（仅后端持有）",
    )
    LARK_OAUTH_REDIRECT_URI: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("LARK_OAUTH_REDIRECT_URI"),
        description="授权码换 token 的 redirect_uri，须与 Lark 开放平台控制台注册的回调地址一致",
    )

    # CORS配置
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        validation_alias=AliasChoices("CORS_ORIGINS"),
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(
        default=True, validation_alias=AliasChoices("CORS_ALLOW_CREDENTIALS")
    )
    CORS_ALLOW_METHODS: list[str] = Field(
        default=["*"], validation_alias=AliasChoices("CORS_ALLOW_METHODS")
    )
    CORS_ALLOW_HEADERS: list[str] = Field(
        default=["*"], validation_alias=AliasChoices("CORS_ALLOW_HEADERS")
    )

    auth: AuthSettings = Field(default_factory=AuthSettings)
    document: DocumentSettings = Field(default_factory=DocumentSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    metrics: MetricsSettings = Field(default_factory=MetricsSettings)
    tracing: TracingSettings = Field(default_factory=TracingSettings)
    health: HealthSettings = Field(default_factory=HealthSettings)

    # gRPC settings
    grpc: GrpcSettings = Field(default_factory=GrpcSettings)

    # Realtime / WebSocket（预留：仅配置层，具体实现可在业务服务中按需启用）
    REALTIME_WS_SEND_QUEUE_MAX: int = Field(
        default=100, validation_alias=AliasChoices("REALTIME_WS_SEND_QUEUE_MAX")
    )
    REALTIME_WS_SEND_OVERFLOW_POLICY: str = Field(
        default="drop_oldest",
        validation_alias=AliasChoices("REALTIME_WS_SEND_OVERFLOW_POLICY"),
    )

    # 分页配置（支持环境变量覆盖）
    DEFAULT_PAGE_SIZE: int = Field(default=20, validation_alias=AliasChoices("DEFAULT_PAGE_SIZE"))
    MAX_PAGE_SIZE: int = Field(default=100, validation_alias=AliasChoices("MAX_PAGE_SIZE"))

    # Upload（通用上限；具体接口可再做细分）
    MAX_UPLOAD_SIZE: int = Field(
        default=10 * 1024 * 1024, validation_alias=AliasChoices("MAX_UPLOAD_SIZE")
    )
    UPLOAD_DIR: str = Field(default="./uploads", validation_alias=AliasChoices("UPLOAD_DIR"))

    # 日志/请求体记录配置
    LOG_REQUEST_BODY_ENABLE_BY_DEFAULT: bool = Field(
        default=True, validation_alias=AliasChoices("LOG_REQUEST_BODY_ENABLE_BY_DEFAULT")
    )
    LOG_REQUEST_BODY_MAX_BYTES: int = Field(
        default=2048, validation_alias=AliasChoices("LOG_REQUEST_BODY_MAX_BYTES")
    )
    LOG_REQUEST_BODY_ALLOW_MULTIPART: bool = Field(
        default=False, validation_alias=AliasChoices("LOG_REQUEST_BODY_ALLOW_MULTIPART")
    )

    # 文件日志配置
    LOG_FILE: Optional[str] = Field(default=None, validation_alias=AliasChoices("LOG_FILE"))
    LOG_LEVEL: str = Field(default="INFO", validation_alias=AliasChoices("LOG_LEVEL"))
    LOG_MAX_BYTES: int = Field(
        default=100 * 1024 * 1024, validation_alias=AliasChoices("LOG_MAX_BYTES")
    )  # 100MB
    LOG_BACKUP_COUNT: int = Field(default=5, validation_alias=AliasChoices("LOG_BACKUP_COUNT"))

    # Email / 外部集成（可选）
    SMTP_HOST: Optional[str] = Field(default=None, validation_alias=AliasChoices("SMTP_HOST"))
    SMTP_PORT: int = Field(default=587, validation_alias=AliasChoices("SMTP_PORT"))
    SMTP_USER: Optional[str] = Field(default=None, validation_alias=AliasChoices("SMTP_USER"))
    SMTP_PASSWORD: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("SMTP_PASSWORD")
    )
    EMAIL_FROM: Optional[str] = Field(default=None, validation_alias=AliasChoices("EMAIL_FROM"))

    STRIPE_API_KEY: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("STRIPE_API_KEY")
    )

    # Error Tracking (Sentry)
    SENTRY_DSN: Optional[str] = Field(default=None, validation_alias=AliasChoices("SENTRY_DSN"))

    # Rate limiting（预留：具体实现可选 Redis/本地）
    RATE_LIMIT_PER_MINUTE: int = Field(
        default=60, validation_alias=AliasChoices("RATE_LIMIT_PER_MINUTE")
    )

    # Redis 锁自动续租配置（全局默认值）
    REDIS_LOCK_AUTO_RENEW_DEFAULT: bool = Field(
        default=False, validation_alias=AliasChoices("REDIS_LOCK_AUTO_RENEW_DEFAULT")
    )
    REDIS_LOCK_AUTO_RENEW_INTERVAL_RATIO: float = Field(
        default=0.6, validation_alias=AliasChoices("REDIS_LOCK_AUTO_RENEW_INTERVAL_RATIO")
    )
    REDIS_LOCK_AUTO_RENEW_JITTER_RATIO: float = Field(
        default=0.1, validation_alias=AliasChoices("REDIS_LOCK_AUTO_RENEW_JITTER_RATIO")
    )

    # Kafka grouped settings (builder below)

    # pydantic-settings v2 configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        # Fail fast for unknown keys in `.env` to avoid "configured but not used" footguns.
        extra="forbid",
        env_nested_delimiter="__",
    )

    @model_validator(mode="after")
    def _validate_secret_key(self):
        # 所有环境均要求显式配置 SECRET_KEY
        if not self.SECRET_KEY:
            raise ValueError("SECRET_KEY 未配置。请在环境变量或 .env 中设置 SECRET_KEY")
        # JWT 用 HS256 + 该值签名：模板/常见弱值等于把签名密钥公开，任何人可伪造令牌
        if self.SECRET_KEY.strip().lower() in _KNOWN_WEAK_SECRET_KEYS:
            raise ValueError(
                "SECRET_KEY 是公开的模板/弱默认值，禁止使用。"
                "请生成随机密钥，例如：openssl rand -hex 32"
            )
        if len(self.SECRET_KEY) < MIN_SECRET_KEY_LENGTH:
            raise ValueError(
                f"SECRET_KEY 长度不足 {MIN_SECRET_KEY_LENGTH} 字符，签名强度不够。"
                "请生成随机密钥，例如：openssl rand -hex 32"
            )
        return self

    @model_validator(mode="after")
    def _validate_debug_environment(self):
        # 生产环境禁止 DEBUG：debug 响应体会泄露 traceback（core/exceptions.py）
        if self.ENVIRONMENT.strip().lower() == "production" and self.DEBUG:
            raise ValueError("ENVIRONMENT=production 时禁止 DEBUG=true，请关闭 DEBUG")
        return self

    @field_validator("CORS_ORIGINS", "CORS_ALLOW_METHODS", "CORS_ALLOW_HEADERS", mode="before")
    @classmethod
    def _parse_str_list(cls, v: Any):
        """允许 JSON 字符串或逗号分隔字符串两种格式。"""
        if isinstance(v, list):
            return [str(item) for item in v]
        if isinstance(v, str):
            s = v.strip()
            if s.startswith("[") and s.endswith("]"):
                import json

                arr = None
                try:
                    arr = json.loads(s)
                except ValueError:
                    arr = None
                if isinstance(arr, list):
                    return [str(item) for item in arr]
            if "," in s:
                return [item.strip() for item in s.split(",") if item.strip()]
            return [s]
        return v


settings = Settings()
