# input: application services, infrastructure 实现（composition root 豁免）, HTTP Bearer 凭证
# output: get_*_service 依赖工厂, get_current_user 认证依赖
# owner: wanhua.gu
# pos: 表示层 - FastAPI 依赖注入装配点（具体实现→端口的唯一绑定处）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""API 依赖项（composition root）。"""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from application.dto import UserDTO
from application.ports.document_parser import DocumentParserPort
from application.ports.llm import LLMPort
from application.ports.security import PasswordHasher, TokenProvider
from application.ports.storage import StoragePort
from application.services.auth_service import AuthApplicationService
from application.services.chat_service import ChatApplicationService
from application.services.conversation_service import ConversationApplicationService
from application.services.document_service import DocumentApplicationService
from application.services.file_asset_service import FileAssetApplicationService
from application.services.idempotency_service import IdempotencyService
from core.config import settings
from domain.common.exceptions import UnauthorizedException
from infrastructure.adapters.idempotency_store import RedisIdempotencyStore
from infrastructure.adapters.storage_port import StorageProviderPortAdapter
from infrastructure.external.llm import get_llm_client
from infrastructure.external.parsing import get_parser
from infrastructure.external.storage import get_storage
from infrastructure.external.google import GoogleAuthCodeExchanger, GoogleIdTokenVerifier
from infrastructure.external.lark import LARK_OPEN_HOSTS, LarkAuthCodeExchanger
from infrastructure.security import JwtTokenProvider, PwdlibPasswordHasher
from infrastructure.unit_of_work import SQLAlchemyUnitOfWork


class _NoopIdempotencyStore:
    """Redis 未配置时的直通实现：不加锁、不缓存结果。"""

    async def get(self, *, scope: str, key: str):
        return None

    async def try_start(self, *, scope: str, key: str, request_hash: str, ttl_seconds: int) -> bool:
        return True

    async def set_result(
        self, *, scope: str, key: str, request_hash: str, payload: dict, ttl_seconds: int
    ) -> None:
        return None

    async def release(self, *, scope: str, key: str) -> None:
        return None


_noop_idempotency_store = _NoopIdempotencyStore()

# 进程级单例：密码哈希与令牌签发是无状态纯计算
_password_hasher = PwdlibPasswordHasher()
_bearer_scheme = HTTPBearer(auto_error=False)
_token_provider: JwtTokenProvider | None = None
_google_exchanger: GoogleAuthCodeExchanger | None = None
_oauth_exchangers: dict[str, LarkAuthCodeExchanger] | None = None


def _get_token_provider() -> JwtTokenProvider:
    global _token_provider
    if _token_provider is None:
        _token_provider = JwtTokenProvider(
            secret_key=settings.SECRET_KEY or "",
            algorithm=settings.auth.algorithm,
            access_ttl_seconds=settings.auth.access_token_ttl_seconds,
            refresh_ttl_seconds=settings.auth.refresh_token_ttl_seconds,
        )
    return _token_provider


def _get_google_exchanger() -> GoogleAuthCodeExchanger | None:
    """授权码流：需 GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET 同时配置才组装交换器；
    缺任一则返回 None → service 拒绝（fail-closed）。client_secret 仅后端持有。"""
    global _google_exchanger
    if _google_exchanger is None and settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
        _google_exchanger = GoogleAuthCodeExchanger(
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            redirect_uri=settings.GOOGLE_OAUTH_REDIRECT_URI,
            verifier=GoogleIdTokenVerifier(client_id=settings.GOOGLE_CLIENT_ID),
        )
    return _google_exchanger


def _get_oauth_exchangers() -> dict[str, LarkAuthCodeExchanger]:
    """飞书/Lark 授权码交换器：按各自 APP_ID+SECRET 配置懒装配；
    缺任一则该 provider 不入表 → service 拒绝（fail-closed）。app_secret 仅后端持有。"""
    global _oauth_exchangers
    if _oauth_exchangers is None:
        exchangers: dict[str, LarkAuthCodeExchanger] = {}
        if settings.FEISHU_APP_ID and settings.FEISHU_APP_SECRET:
            exchangers["feishu"] = LarkAuthCodeExchanger(
                host=LARK_OPEN_HOSTS["feishu"],
                app_id=settings.FEISHU_APP_ID,
                app_secret=settings.FEISHU_APP_SECRET,
                redirect_uri=settings.FEISHU_OAUTH_REDIRECT_URI or "",
            )
        if settings.LARK_APP_ID and settings.LARK_APP_SECRET:
            exchangers["lark"] = LarkAuthCodeExchanger(
                host=LARK_OPEN_HOSTS["lark"],
                app_id=settings.LARK_APP_ID,
                app_secret=settings.LARK_APP_SECRET,
                redirect_uri=settings.LARK_OAUTH_REDIRECT_URI or "",
            )
        _oauth_exchangers = exchangers
    return _oauth_exchangers


async def get_password_hasher() -> PasswordHasher:
    return _password_hasher


async def get_token_provider() -> TokenProvider:
    return _get_token_provider()


async def get_auth_service(
    hasher: PasswordHasher = Depends(get_password_hasher),
    tokens: TokenProvider = Depends(get_token_provider),
) -> AuthApplicationService:
    return AuthApplicationService(
        uow_factory=SQLAlchemyUnitOfWork,
        password_hasher=hasher,
        token_provider=tokens,
        google_exchanger=_get_google_exchanger(),
        oauth_exchangers=_get_oauth_exchangers(),
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    service: AuthApplicationService = Depends(get_auth_service),
) -> UserDTO:
    """Resolve the authenticated user from the Bearer token (401 otherwise)."""
    if credentials is None or not credentials.credentials:
        raise UnauthorizedException()
    return await service.get_current_user(credentials.credentials)


async def get_storage_port(provider=Depends(get_storage)) -> StoragePort:
    return StorageProviderPortAdapter(provider)


async def get_file_asset_service(
    storage: StoragePort = Depends(get_storage_port),
) -> FileAssetApplicationService:
    return FileAssetApplicationService(uow_factory=SQLAlchemyUnitOfWork, storage=storage)


async def get_document_parser() -> DocumentParserPort:
    return get_parser()


async def get_document_service(
    storage: StoragePort = Depends(get_storage_port),
    parser: DocumentParserPort = Depends(get_document_parser),
) -> DocumentApplicationService:
    return DocumentApplicationService(
        uow_factory=SQLAlchemyUnitOfWork,
        parser=parser,
        storage=storage,
    )


async def get_idempotency_service() -> IdempotencyService:
    store = RedisIdempotencyStore() if settings.redis.url else _noop_idempotency_store
    return IdempotencyService(
        store=store,
        lock_ttl_seconds=settings.idempotency.lock_ttl_seconds,
        result_ttl_seconds=settings.idempotency.result_ttl_seconds,
    )


async def get_conversation_service() -> ConversationApplicationService:
    return ConversationApplicationService(uow_factory=SQLAlchemyUnitOfWork)


async def get_llm_port() -> LLMPort:
    client = get_llm_client()
    if client is None:
        raise RuntimeError(
            "LLM client not initialized. Set LLM__API_KEY in environment or .env and restart."
        )
    return client


async def get_chat_service(
    llm: LLMPort = Depends(get_llm_port),
) -> ChatApplicationService:
    return ChatApplicationService(uow_factory=SQLAlchemyUnitOfWork, llm=llm)
