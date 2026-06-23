# API · 认证（/api/v1/auth）

> 信封与错误码见 `conventions.md`。所有成功响应为 `{ code, message, data, error }`，`data` 为下表 payload。
> 由 Google 登录特性补写（新增 `POST /auth/google`）。

## 端点一览

| 方法 | 路径 | 说明 | 限流 scope |
|---|---|---|---|
| POST | `/auth/register` | 用户名+邮箱+密码注册 | `auth:register` |
| POST | `/auth/login` | 用户名或邮箱 + 密码登录 | `auth:login` |
| POST | `/auth/google` | **Google 登录（ID Token）** | `auth:google` |
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
- 链接策略：`email_verified` 为真才自动链接已有邮箱账号；否则新建独立账号（详见 `docs/project/data/auth.md`）。
- 配置：后端 `GOOGLE_CLIENT_ID`（未配置时非生产降级 `DevGoogleVerifier`，生产应拒绝）；前端 `VITE_GOOGLE_CLIENT_ID`。

## 其余端点（既有）

- `/auth/register` 请求 `{ username, email, password, full_name? }` → `data` 为 `UserDTO`。
- `/auth/login` 请求 `{ username, password }`（username 接受用户名或邮箱）→ `TokenPairDTO`。
- `/auth/refresh` 请求 `{ refresh_token }` → `TokenPairDTO`。
- `/auth/me` 需 `Authorization: Bearer <access_token>` → `UserDTO`。
