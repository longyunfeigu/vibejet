"""
数据传输对象（DTO）- 应用层与表现层之间的数据传输
"""

from pydantic import BaseModel, Field, field_validator, model_serializer, ConfigDict
from shared.codes import BusinessCode
from typing import Optional, Any, Literal
from datetime import datetime, timezone
from pydantic import model_validator


class DTOBase(BaseModel):
    """Base DTO: unify datetime serialization to UTC-Z for all subclasses."""

    @model_serializer(mode="wrap")
    def _serialize_model(self, handler):  # type: ignore[override]
        data = handler(self)

        def convert(value):
            if isinstance(value, datetime):
                ts = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
                s = ts.astimezone(timezone.utc).isoformat()
                return s.replace("+00:00", "Z")
            if isinstance(value, list):
                return [convert(v) for v in value]
            if isinstance(value, tuple):
                return tuple(convert(v) for v in value)
            if isinstance(value, dict):
                return {k: convert(v) for k, v in value.items()}
            return value

        return convert(data)


class PaginationParams(DTOBase):
    """分页参数（页码/每页大小），自动派生 skip/limit。

    注意：默认值在实例化时从应用设置读取，避免在类定义阶段
    导入并实例化全局配置导致的副作用。
    """

    page: int = Field(1, ge=1, description="页码，从1开始")
    size: Optional[int] = Field(
        default=None,
        ge=1,
        description="每页大小（默认取应用配置 DEFAULT_PAGE_SIZE）",
    )

    @model_validator(mode="after")
    def _apply_runtime_defaults(self):  # type: ignore[override]
        # 延迟导入设置，只有在实例化 DTO 时才读取
        try:
            from core.config import settings  # local import to avoid import-time side effects

            default_size = int(getattr(settings, "DEFAULT_PAGE_SIZE", 20))
            max_size = int(getattr(settings, "MAX_PAGE_SIZE", 100))
        except Exception:
            default_size = 20
            max_size = 100
        if self.size is None:
            self.size = default_size
        # 运行时再约束最大页大小
        if self.size > max_size:
            self.size = max_size
        return self

    @property
    def skip(self) -> int:
        return (self.page - 1) * int(self.size or 0)

    @property
    def limit(self) -> int:
        return int(self.size or 0)


class MessageDTO(DTOBase):
    """消息响应DTO"""

    message: str
    code: int = BusinessCode.SUCCESS


class ErrorDTO(DTOBase):
    """错误响应DTO"""

    error: str
    code: int
    detail: Optional[str] = None


class FileAssetDTO(DTOBase):
    """File asset detail DTO."""

    id: int
    owner_id: Optional[int]
    storage_type: str
    bucket: Optional[str]
    region: Optional[str]
    key: str
    size: int
    etag: Optional[str]
    content_type: Optional[str]
    original_filename: Optional[str]
    kind: Optional[str]
    is_public: bool
    metadata: dict[str, Any] = Field(default_factory=dict)
    url: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class FileAssetSummaryDTO(DTOBase):
    """Reduced file asset payload for lightweight responses."""

    id: int
    key: str
    status: str
    original_filename: Optional[str]
    content_type: Optional[str]
    etag: Optional[str]
    size: int
    url: Optional[str]


class PresignUploadRequestDTO(DTOBase):
    """Input payload for requesting a presigned upload."""

    filename: str
    mime_type: Optional[str] = Field(default=None, alias="mime_type")
    size_bytes: int = Field(ge=0, alias="size_bytes")
    kind: str = Field(default="uploads")
    method: Literal["PUT", "POST"] = Field(default="PUT")
    expires_in: int = Field(default=600, ge=60, le=3600)


class CompleteUploadRequestDTO(DTOBase):
    """Payload for confirming a presigned upload."""

    id: Optional[int] = None
    key: Optional[str] = None

    @field_validator("id", "key")
    def _strip_empty(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("key")
    def _normalize_key(cls, value):
        if value:
            return value.lstrip("/")
        return value

    def ensure_identifier(self) -> None:
        if self.id is None and not self.key:
            raise ValueError("id 或 key 必须提供一个")


class FileAccessURLRequestDTO(DTOBase):
    """Payload for generating access URLs."""

    expires_in: int = Field(default=600, ge=60, le=3600)
    filename: Optional[str] = None


class PresignUploadDetailDTO(DTOBase):
    """Presigned request information returned to clients."""

    url: str
    method: str
    headers: dict[str, str] = Field(default_factory=dict)
    fields: dict[str, str] = Field(default_factory=dict)
    expires_in: int


class PresignUploadResponseDTO(DTOBase):
    """Response payload for presigned upload preparation."""

    file: FileAssetSummaryDTO
    upload: PresignUploadDetailDTO


class StorageUploadResponseDTO(DTOBase):
    """Response payload after direct upload completes via API relay."""

    key: str
    etag: Optional[str]
    size: int
    content_type: Optional[str]
    url: Optional[str]
    file_id: int
    file_status: str


# ── Auth / User DTOs ────────────────────────────────────────────────


class RegisterRequestDTO(DTOBase):
    """Input for user registration."""

    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$")
    email: str = Field(max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=100)


class LoginRequestDTO(DTOBase):
    """Input for login. `username` accepts username or email."""

    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class GoogleLoginRequestDTO(DTOBase):
    """Input for Google login: the OAuth authorization code from the popup auth-code flow."""

    code: str = Field(min_length=1, max_length=8192)


class RefreshRequestDTO(DTOBase):
    """Input for refreshing an access token."""

    refresh_token: str = Field(min_length=1)


class TokenPairDTO(DTOBase):
    """Issued token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 0


class UserDTO(DTOBase):
    """Public user payload (never exposes the password hash)."""

    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ── Agent / Conversation DTOs ────────────────────────────────────────


class CreateConversationDTO(DTOBase):
    """Input for creating a new conversation."""

    title: str = Field(max_length=255)
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpdateConversationDTO(DTOBase):
    """Input for updating a conversation."""

    title: Optional[str] = Field(default=None, max_length=255)
    system_prompt: Optional[str] = None
    model: Optional[str] = None


class ConversationDTO(DTOBase):
    """Conversation detail DTO."""

    id: int
    title: str
    system_prompt: Optional[str]
    model: Optional[str]
    status: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MessageDTO_Agent(DTOBase):
    """Message DTO for conversation history."""

    id: int
    conversation_id: int
    role: str
    content: str
    run_id: Optional[int] = None
    token_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RunDTO(DTOBase):
    """Run tracking DTO."""

    id: int
    conversation_id: int
    status: str
    model: Optional[str]
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatRequestDTO(DTOBase):
    """Input for sending a chat message."""

    message: str = Field(min_length=1)
    model: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    stream: bool = True


class CreateAgentConfigDTO(DTOBase):
    """Input for creating an agent configuration."""

    name: str = Field(max_length=100)
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpdateAgentConfigDTO(DTOBase):
    """Input for updating an agent configuration."""

    name: Optional[str] = Field(default=None, max_length=100)
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    metadata: Optional[dict[str, Any]] = None


class AgentConfigDTO(DTOBase):
    """Agent configuration DTO."""

    id: int
    name: str
    system_prompt: Optional[str]
    model: Optional[str]
    temperature: Optional[float]
    max_tokens: Optional[int]
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Document DTOs ──────────────────────────────────────────────────


class CreateDocumentDTO(DTOBase):
    """Input for creating a document from an uploaded file asset."""

    file_asset_id: int = Field(ge=1)
    title: Optional[str] = Field(default=None, max_length=255)


class DocumentDTO(DTOBase):
    """Document detail DTO（不含 Markdown 正文，正文走 content 端点）。"""

    id: int
    owner_id: Optional[int]
    file_asset_id: int
    title: Optional[str]
    source_filename: Optional[str]
    content_type: Optional[str]
    parser: Optional[str]
    status: str
    error_code: Optional[str]
    error_message: Optional[str]
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentContentDTO(DTOBase):
    """Parsed document content (canonical Markdown)."""

    id: int
    status: str
    parser: Optional[str]
    markdown: str
