# input: AuthApplicationService 依赖注入, get_current_user
# output: /auth 路由（register, login, google, oauth/{provider}, refresh, me）
# owner: wanhua.gu
# pos: 表示层路由 - 认证 API（JWT Bearer + Google / 飞书·Lark 联合登录）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Authentication routes (register / login / google / oauth / refresh / me)."""

from __future__ import annotations

from enum import Enum

from fastapi import APIRouter, Depends

from api.dependencies import get_auth_service, get_current_user
from api.utils.rate_limit import rate_limit
from application.dto import (
    GoogleLoginRequestDTO,
    LoginRequestDTO,
    OAuthLoginRequestDTO,
    RefreshRequestDTO,
    RegisterRequestDTO,
    TokenPairDTO,
    UserDTO,
)
from application.services.auth_service import AuthApplicationService
from core.i18n import t
from core.response import Response as ApiResponse
from core.response import success_response

router = APIRouter(prefix="/auth", tags=["认证"])


class OAuthProvider(str, Enum):
    """支持的联合登录 provider（路径参数，非法值由 FastAPI 自动返回 422）。"""

    feishu = "feishu"
    lark = "lark"


@router.post(
    "/register",
    summary="注册",
    response_model=ApiResponse[UserDTO],
    dependencies=[Depends(rate_limit("auth:register"))],
)
async def register(
    payload: RegisterRequestDTO,
    service: AuthApplicationService = Depends(get_auth_service),
):
    user = await service.register(payload)
    return success_response(user, message=t("ok"))


@router.post(
    "/login",
    summary="登录（用户名或邮箱 + 密码）",
    response_model=ApiResponse[TokenPairDTO],
    dependencies=[Depends(rate_limit("auth:login"))],
)
async def login(
    payload: LoginRequestDTO,
    service: AuthApplicationService = Depends(get_auth_service),
):
    tokens = await service.login(payload)
    return success_response(tokens, message=t("ok"))


@router.post(
    "/google",
    summary="Google 登录（授权码）",
    response_model=ApiResponse[TokenPairDTO],
    dependencies=[Depends(rate_limit("auth:google"))],
)
async def login_google(
    payload: GoogleLoginRequestDTO,
    service: AuthApplicationService = Depends(get_auth_service),
):
    tokens = await service.login_with_google(payload.code)
    return success_response(tokens, message=t("ok"))


@router.post(
    "/oauth/{provider}",
    summary="飞书 / Lark 登录（授权码）",
    response_model=ApiResponse[TokenPairDTO],
    dependencies=[Depends(rate_limit("auth:oauth"))],
)
async def login_oauth(
    provider: OAuthProvider,
    payload: OAuthLoginRequestDTO,
    service: AuthApplicationService = Depends(get_auth_service),
):
    tokens = await service.login_with_oauth(provider.value, payload.code)
    return success_response(tokens, message=t("ok"))


@router.post(
    "/refresh",
    summary="刷新令牌",
    response_model=ApiResponse[TokenPairDTO],
)
async def refresh(
    payload: RefreshRequestDTO,
    service: AuthApplicationService = Depends(get_auth_service),
):
    tokens = await service.refresh(payload.refresh_token)
    return success_response(tokens, message=t("ok"))


@router.get(
    "/me",
    summary="当前用户",
    response_model=ApiResponse[UserDTO],
)
async def me(current_user: UserDTO = Depends(get_current_user)):
    return success_response(current_user, message=t("ok"))
