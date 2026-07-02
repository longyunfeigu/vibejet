# 2026-06-23 · Google 登录升级为 OAuth 授权码流 + 自定义按钮

> 执行记录（ad-hoc feature，非正式 Story）。完整设计见会话计划；本文件为 repo 侧可追溯记录。

## Context

`feat/google` 分支原本用 **GIS ID-token（credential）流**：前端 `<GoogleLogin>` iframe 按钮拿 ID token，
后端仅用 `GOOGLE_CLIENT_ID` 验 `aud`。两个问题：① 官方 iframe 按钮与登录页深色药丸体系不统一；
② 不是带 `client_secret` 的“正规后端流”。目标改成 **popup 授权码流**：前端拿 `code` → 后端用
`client_secret` 去 Google token 端点换 `id_token` → 复用验签 → 既有 find/link/create → 签发自有 JWT。

## 改动清单

**后端（DDD：port 抽象 + infra 实现 + composition root 接线）**
- `core/config.py`：新增 `GOOGLE_CLIENT_SECRET`、`GOOGLE_OAUTH_REDIRECT_URI`(默认 `postmessage`)。
- `application/ports/oauth.py`：新增 `GoogleAuthCodeExchanger` Protocol（`async exchange(code) -> GoogleIdentity`）。
- `infrastructure/external/google/code_exchanger.py`（新）：httpx POST `oauth2.googleapis.com/token` 换 `id_token`，
  复用 `GoogleIdTokenVerifier` 验签；交换失败/缺 id_token/非 JSON → `InvalidTokenException`。
- `application/services/auth_service.py`：`login_with_google(code)` 用 `await exchanger.exchange(code)`；find/link/create 不变。
- `application/dto.py`：`GoogleLoginRequestDTO.credential` → `code`。
- `api/routes/auth.py`：`/auth/google` 用 `payload.code`，summary 改“授权码”。
- `api/dependencies.py`：`_get_google_exchanger()` 仅在 id+secret 同时配置时组装（fail-closed）；移除 `DevGoogleVerifier` 接线。
- 测试：`tests/test_auth_google_service.py`（exchanger 化 + 未配置/停用）、`tests/test_google_code_exchanger.py`（新，httpx mock 4+1 例）。

**前端**
- `features/auth/hooks/useGoogleLogin.ts`：`useGoogleLogin({flow:'auth-code'})` 触发 popup，`onSuccess` 拿 `code` → mutation；返回 `{login, isPending}`。
- `features/auth/components/GoogleSignInButton.tsx`：白底描边药丸 + 官方四色 G logo + “使用 Google 继续”（次级样式守 C5）。
- `features/auth/api/authApi.ts`：`loginWithGoogle(code)` 发 `{code}`。

**关键修复（根因）**
- `frontend/src/lib/`（`apiClient.ts`/`authStore.ts`/`utils.ts`/README）本被 `.gitignore` 的 Python 打包规则 `lib/` 误伤 → 源文件无法提交、干净 checkout 编译不过。`.gitignore` 加 `!frontend/src/lib/` 负向规则解封。
- 配置位：`backend/.env` 加 `GOOGLE_CLIENT_ID=` / `GOOGLE_CLIENT_SECRET=` 占位；`frontend/.env` 的 `VITE_GOOGLE_CLIENT_ID` 为占位。

## 验证
- 后端：`uv run pytest tests/test_auth_google_service.py tests/test_google_code_exchanger.py` → 11 passed；flake8(非 B008)0、black 干净。
- 前端：`tsc --noEmit` 0 错误；`/login` 截图确认白底描边 Google 按钮 + “或” + 深色“登录”主次层次，无 GIS iframe。
- review：findings-first，0 blocking，4 non-blocking（已修 code_exchanger json 守卫）。

## 已知边界 / 后续
- **[HIGH] apiClient 未挂 Bearer 拦截器** → 登录后 `/auth/me` 401（Google+密码登录同此）。计划显式延后；真实凭据联调前需补 `Authorization: Bearer ${getSession()?.accessToken}` + 401 刷新。
- 端到端 popup 流需真实 `GOOGLE_CLIENT_ID/SECRET`（同一 Web client）才能跑通，当前占位下点按钮会因 invalid client 报错。
- `DevGoogleVerifier` 保留但授权码流未接线。
- authStore token 存 localStorage（XSS 面），属本分支既定模式。
