# Plan: 2026-06-24 · 新增飞书 / Lark 联合登录（标准网页授权码流）

## Context

已支持 Google 登录（`feat/google`，OAuth 授权码 popup 流）。本次在 `feat/lark-login` 分支追加
**飞书（open.feishu.cn）与 Lark 国际（open.larksuite.com）登录**，标准网页登录形态（浏览器整页跳转 /
扫码 → 回调页拿 code），两个平台同一套代码、配置层区分 host。

底层联合登录设施已 provider 无关、直接复用：`OAuthAccount(provider, provider_sub)`、`oauth_accounts`
表（唯一键 `(provider, provider_sub)`）、`get_by_oauth/add_oauth_account`、`AuthApplicationService`
的 find/link/create 编排、JWT 签发。

与 Google 的核心差异：① 前端 popup → 整页跳转 + 回调路由；② 身份来源 = `code → access_token →
user_info`（飞书 v2 OIDC token 端点 `client_id+secret+code`，无需先取 app_access_token）；
③ 稳定标识 `union_id`；④ email 可能缺失，而 `users.email` 非空+唯一、`User` 实体强制校验合法 email。

## 已确认产品决策

- **平台**：飞书 + Lark 都要，配置层区分 host（两套独立 app 注册 → 两个 provider：`feishu` / `lark`）。
- **形态**：标准网页登录（跳转 + 回调）。
- **无 email**：合成占位邮箱 `{union_id}@{provider}.local`，**零 migration、不改 domain 不变量**。
- **邮箱自动 link**：自动 link，但仅凭 `enterprise_email`（管理员分配、组织管控）当「已验证邮箱」用于
  link（等价 Google `email_verified=true`）；自填 `email` 字段不参与 link，只作参考存档。

## §0 Triage → Flow C

| # | 问题 | 判定 |
|---|------|------|
| 1 | 单一用户目标？ | 是 |
| 2 | 单一业务模块（auth）？ | 是 |
| 3 | 不改 DB schema / migration？ | 是（合成邮箱复用 `oauth_accounts`，零 migration） |
| 4 | 不改公共 API 契约？ | 否（新增 `POST /auth/oauth/{provider}`） |
| 5 | 不涉及 domain 规则变化？ | 是（复用 find/link/create 与实体不变量） |
| 6 | 不涉及外部系统？ | 否（飞书 / Lark OAuth） |
| 7 | 不涉及权限 / 安全？ | 否（认证） |
| 8 | 少量文件、不超 2 层？ | 否 |

4 个「否」+ 强制升级（改认证/安全、引入外部系统）→ **Flow C**。

## 范围

- **做**：飞书+Lark 授权码网页登录、后端 code→身份适配器、共用 find/link/create、前端跳转+回调、契约文档、单测。
- **不做**：飞书客户端内 H5 免登（JSSDK）；扫码独立 UI（用授权页自带扫码）；改 `users` schema；改 Google
  现有流程；`apiClient` Bearer 拦截器（沿用 `feat/google` 既定延后项）。

## 方案概述

**后端**
1. `application/ports/oauth.py`：+ `OAuthIdentity(sub, email: Optional, email_verified, name)`、
   `LarkAuthCodeExchanger` Protocol（`async exchange(code) -> OAuthIdentity`）。
2. `infrastructure/external/lark/code_exchanger.py`（新）：`LarkAuthCodeExchanger(host, app_id,
   app_secret, redirect_uri)`：POST `{host}/open-apis/authen/v2/oauth/token` 换 access_token →
   GET `{host}/open-apis/authen/v1/user_info` 拿 `union_id/open_id/name/email/enterprise_email`。
   映射 `sub=union_id or open_id`、`email=enterprise_email or None`、`email_verified=bool(enterprise_email)`。
   失败/缺 sub → `InvalidTokenException`（不回显 secret/token）。host：feishu→open.feishu.cn、lark→open.larksuite.com。
3. `application/services/auth_service.py`：抽 `_complete_oauth_login(uow, provider, identity, *,
   synth_email_domain)`；`login_with_google` 改走它（行为不变）；新增 `login_with_oauth(provider, code)`
   从注入的 `oauth_exchangers: dict[str, LarkAuthCodeExchanger]` 取 exchanger。
4. `application/dto.py`：+ `OAuthLoginRequestDTO { code }`。
5. `api/routes/auth.py`：+ `POST /auth/oauth/{provider}`（校验 ∈ {feishu, lark}），`rate_limit("auth:oauth")`。
6. `api/dependencies.py`：`_get_oauth_exchangers()` 按 FEISHU_*/LARK_* 懒装配（fail-closed）注入 service。
7. `core/config.py`：+ `FEISHU_APP_ID/SECRET/OAUTH_REDIRECT_URI`、`LARK_APP_ID/SECRET/OAUTH_REDIRECT_URI`。

**前端**
8. `features/auth/helpers/oauthProviders.ts`（新）：从 env 读已配置 provider 的 `{provider, label,
   authorizeUrl, appId, redirectUri}`。
9. `features/auth/hooks/useOAuthRedirect.ts`（新）：`state={provider}:{nonce}` 存 sessionStorage，
   拼 authorize URL → `location.assign`。
10. `features/auth/components/OAuthRedirectButton.tsx`（新，参数化）：复用药丸样式 + 飞书/Lark logo。
11. `features/auth/api/authApi.ts`：+ `loginWithOAuth(provider, code)`。
12. `routes/auth/callback.tsx`（新 `/auth/callback`）：校验 state（防 CSRF）→ `loginWithOAuth` →
    `setSession` → `navigate('/')`；loading + 失败 UI。
13. `features/auth/components/LoginScreen.tsx`：渲染已配置 social 按钮；「或」分隔线在任一 social 存在时显示。
14. `pnpm dev` 重生成 `routeTree.gen.ts`。

## 验收标准
1. 配飞书 app → 登录页出现「使用飞书继续」→ 点击跳转授权页。
2. 回调校验 state 通过 → 后端换身份 → 落 `oauth_accounts(provider='feishu', provider_sub=union_id)` → JWT → 跳首页。
3. 无 enterprise_email 也能登录（合成占位邮箱独立账号）。
4. 有 enterprise_email 且命中已有同邮箱用户 → 自动 link（不新建）。
5. Lark 配置后同上，provider=`lark`。
6. `test_lark_code_exchanger.py` + `test_auth_lark_service.py` 绿；`tsc --noEmit` 0 错误。

## 风险
- 飞书 v2 `oauth/token` / `user_info` 响应结构与假设不符 → 端点/字段集中常量化，对照最新官方文档，单测覆盖各分支。
- `union_id` 非 ISV 应用可能缺失 → 回退 `open_id` 并记 warning。
- 自动 link 账号接管面 → 仅用 `enterprise_email` 作「已验证」键。
- `redirect_uri` 与控制台不一致 → 单一回调路径 `/auth/callback`，provider 编码进 state，文档写明需注册。

## §11 执行步骤
1. plan 落盘 + config/.env 占位。
2. 后端 port + Lark 适配器 → `test_lark_code_exchanger.py`。
3. 后端编排 `_complete_oauth_login` + `login_with_oauth` + DTO → `test_auth_lark_service.py` + 既有 google 测试。
4. 后端路由 + DI → `uv run pytest tests/ -q` 全绿、flake8/black。
5. 前端跳转+回调 → `pnpm tsc --noEmit`、`/login` 视觉、`/auth/callback` 错误态。
6. 文档：`docs/project/api/auth.md`、`docs/project/data/auth.md`、头注释 + README。
7. `review` skill 过 diff，blocking 修完收尾。

### 真机 E2E 已知边界
需真实飞书/Lark app_id+secret 且控制台注册 `{origin}/auth/callback`，占位配置下点按钮会因 invalid client 失败。
