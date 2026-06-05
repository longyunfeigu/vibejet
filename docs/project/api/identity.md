# API · identity 模块

> 范围：模拟 Lark 登录、会话、身份关联、基于角色的访问控制（Epic 1）。
> 全局约定见 [conventions.md](./conventions.md)。数据模型见 [../data/identity.md](../data/identity.md)。
> 响应体均为统一信封，下表「Response」列描述 `data` 内结构。

## 端点

### POST /api/v1/exam/auth/mock-login

模拟 Lark 登录：选择 / 输入预置账号，建立会话并记录身份。

- **Auth**：无需登录。
- **Request**：`{ "account_id": "<预置账号标识>" }`
- **Response 200**（`data`）：`{ "user": { "id": int, "user_id": str, "name": str, "email": str, "role": "admin"|"employee" } }`
  - 同时下发 `Set-Cookie`（HttpOnly 会话 token）。
  - `user.id` = `users.id`（关联真相源）；`user.user_id` = Lark 身份「用户 ID」（`users.external_user_id`）。
- **错误**：账号不在预置列表，或缺 `name`/`email`/`external_user_id` 任一字段 → **401** `error.message_key="invalid_account"`（`BusinessCode.INVALID_ACCOUNT`）。
- **幂等**：同一 user 重复登录 → 撤销既有活跃会话并建新（或复用），保证该 user 活跃会话 ≤1。

### GET /api/v1/exam/auth/me

返回当前登录身份。

- **Auth**：`Depends(get_current_user)`（读 Cookie 会话）。
- **Response 200**（`data`）：`{ "user": { "id", "user_id", "name", "email", "role" } }`
- **错误**：无 / 失效会话 → **401** `UNAUTHORIZED`。

### POST /api/v1/exam/auth/logout

登出，撤销当前会话并清除 Cookie。

- **Auth**：Cookie（无会话也返回成功，幂等）。
- **Response 200**（`data`）：`{ "logged_out": true }`

## 鉴权依赖契约（Provides → Epic 2–6）

| 依赖 | 签名 | 行为 |
|------|------|------|
| `get_current_user` | `() -> CurrentUser{id:int, user_id:str(external), name, email, role}` | 读 Cookie → 活跃会话 → User；无有效会话 raise `UNAUTHORIZED`(401) |
| `require_admin` | FastAPI dependency | 依赖 `get_current_user`，`role!=admin` → `FORBIDDEN`(403) |
| `require_employee` | FastAPI dependency | 依赖 `get_current_user`，`role!=employee` → `FORBIDDEN`(403) |
| `require_role(role)` | `(Role) -> dependency` | 通用角色门，不匹配 → `FORBIDDEN`(403) |

> Epic 3–6 的受保护端点（如 `/exam/admin/papers`、`/exam/my/results`、`/exam/admin/questions`、`/exam/results/{id}`）统一引用上述依赖；这些端点本身在各自 Epic 实现，不在 Epic 1 范围内。

## 角色

| 角色值 | 含义 | 访问范围（R1.3） |
|--------|------|------------------|
| `admin` | 出题管理员 | 资料录入、知识点确认、出题审核、组卷、主观题复核、本场结果 |
| `employee` | 员工考生 | 仅本人试卷作答与本人结果 |

## 错误码（本模块新增）

| 码 | 名称 | HTTP | message_key |
|----|------|------|-------------|
| 30003 | `INVALID_ACCOUNT` | 401 | `invalid_account` |

复用：`UNAUTHORIZED`(30001/401)、`FORBIDDEN`(30002/403)。
