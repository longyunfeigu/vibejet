# API · 认证（/api/v1/auth）

> 信封与错误码见 `conventions.md`。所有成功响应为 `{ code, message, data, error }`，`data` 为下表 payload。
> 由 Google 登录特性补写（新增 `POST /auth/google`）。
> 由飞书 / Lark 登录特性追加（新增 `POST /auth/oauth/{provider}`）。

## 端点一览

| 方法 | 路径 | 说明 | 限流 scope |
|---|---|---|---|
| POST | `/auth/register` | 用户名+邮箱+密码注册 | `auth:register` |
| POST | `/auth/login` | 用户名或邮箱 + 密码登录 | `auth:login` |
| POST | `/auth/google` | **Google 登录（ID Token）** | `auth:google` |
| POST | `/auth/oauth/{provider}` | **飞书 / Lark 登录（授权码），provider ∈ {feishu, lark}** | `auth:oauth` |
| POST | `/auth/refresh` | 刷新令牌 | - |
| GET | `/auth/me` | 当前用户（Bearer） | - |

## POST /auth/google（新增）

请求：

```json
{ "credential": "<Google ID Token (GIS 返回的 JWT)>" }
```

响应 `data`（与 `/auth/login` 同款 `TokenPairDTO`）：

```json
{ "access_token": "...", "refresh_token": "...", "token_type": "bearer", "expires_in": 1800 }
```

行为与安全：
- 后端用 `google-auth` 验签：校验签名、`aud == GOOGLE_CLIENT_ID`、`iss`、`exp`；失败返回令牌错误。
- 找/链/建用户后签发**我们自己的** JWT（复用 `TokenProvider.issue_pair`），下游与密码登录完全一致。
- 链接策略：`email_verified` 为真才自动链接已有邮箱账号；否则新建独立账号且**不落未验证邮箱**
  （用占位邮箱 `{sub}@google.local`，防预注册接管，详见 `docs/project/data/auth.md`）。
- 配置：后端 `GOOGLE_CLIENT_ID`（未配置时非生产降级 `DevGoogleVerifier`，生产应拒绝）；前端 `VITE_GOOGLE_CLIENT_ID`。

## POST /auth/oauth/{provider}（新增）

`provider` 为路径参数，仅接受 `feishu`（open.feishu.cn）与 `lark`（open.larksuite.com）；其余值由 FastAPI 返回 422。

请求：

```json
{ "code": "<飞书/Lark 授权页回调返回的 authorization code>" }
```

响应 `data`（与 `/auth/login` 同款 `TokenPairDTO`）：

```json
{ "access_token": "...", "refresh_token": "...", "token_type": "bearer", "expires_in": 1800 }
```

行为与安全：
- 标准网页授权码流：前端整页跳转授权页拿 `code`（回调 `state` 防 CSRF），后端用 `app_secret` POST
  `{host}/open-apis/authen/v2/oauth/token`（v2 OIDC，无需先取 app_access_token）换 `access_token`，
  再 GET `{host}/open-apis/authen/v1/user_info` 取身份；任一步失败返回令牌错误（不回显 secret/token）。
- 稳定标识取 `union_id`（缺失回退 `open_id`）作为 `oauth_accounts.provider_sub`，`provider` 存 `feishu`/`lark`。
- 找/链/建用户后签发**我们自己的** JWT（复用 `TokenProvider.issue_pair`），下游与密码登录一致。
- 链接策略：仅当飞书返回 `enterprise_email`（管理员分配、可信，等价 Google `email_verified=true`）且命中已有账号时自动链接；
  无邮箱时合成占位邮箱 `{union_id}@{provider}.local` 建独立账号（详见 `docs/project/data/auth.md`）。
- 配置（fail-closed，缺 app_id/secret 该 provider 不可用）：后端 `FEISHU_APP_ID`/`FEISHU_APP_SECRET`/
  `FEISHU_OAUTH_REDIRECT_URI`（Lark 同名 `LARK_*`）；前端 `VITE_FEISHU_APP_ID`/`VITE_LARK_APP_ID`
  （可选 `VITE_*_AUTHORIZE_URL`/`VITE_*_REDIRECT_URI`，默认回调 `{origin}/auth/callback`，须与控制台注册一致）。

## 其余端点（既有）

- `/auth/register` 请求 `{ username, email, password, full_name? }` → `data` 为 `UserDTO`。
- `/auth/login` 请求 `{ username, password }`（username 接受用户名或邮箱）→ `TokenPairDTO`。
- `/auth/refresh` 请求 `{ refresh_token }` → `TokenPairDTO`。
- `/auth/me` 需 `Authorization: Bearer <access_token>` → `UserDTO`。

已知限制：
- refresh token 无轮换/吊销（无状态 JWT 的刻意取舍）：refresh 签发新令牌对后，
  旧 refresh token 在其 `exp` 前仍有效。需要主动吊销能力时再引入 jti + Redis 黑名单。
