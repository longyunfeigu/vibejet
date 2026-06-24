# 数据模型 · 认证（users / oauth_accounts）

> 由 Google 登录特性引入 `oauth_accounts` 表并放开 `users.hashed_password` 非空约束时补写。
> 迁移：`0001`(baseline，users) + `0003`(oauth_accounts + hashed_password 可空)。

## users（认证主体）

| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | int | PK | |
| username | varchar(50) | 唯一索引 `ix_users_username` | |
| email | varchar(255) | 唯一索引 `ix_users_email` | |
| hashed_password | varchar(255) | **可空** | 联合登录(Google)用户无本地密码时为 NULL |
| full_name | varchar(100) | 可空 | 显示名 |
| is_active | bool | 默认 true | |
| is_superuser | bool | 默认 false | |
| created_at / updated_at | timestamptz | | |
| deleted_at | timestamptz | 可空 | 软删除 |

要点：`hashed_password` 自 `0003` 起可空。密码登录路径对空哈希用户视作凭据错误（不报 500）。

## oauth_accounts（联合登录身份）

一个用户可绑定多个外部身份（1 user ↔ N identities）。

| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | int | PK | |
| user_id | int | FK→users.id `ON DELETE CASCADE`，索引 `ix_oauth_user_id` | 所属用户 |
| provider | varchar(32) | | 身份提供方：`google` / `feishu` / `lark`（飞书与 Lark 分属不同开放平台，独立 app，故各占一个 provider） |
| provider_sub | varchar(255) | | 提供方稳定唯一标识：Google 的 `sub`；飞书/Lark 的 `union_id`（缺失回退 `open_id`） |
| email | varchar(255) | 可空 | 提供方返回邮箱（参考用，非真相源）；飞书/Lark 存 `enterprise_email`（无则空） |
| created_at | timestamptz | | |

- **唯一约束** `uq_oauth_provider_sub (provider, provider_sub)`：同一外部身份只能绑一次，兜底并发链接竞争。
- 查询：`get_by_oauth(provider, sub)` 经此表 join 到 users。

## 链接策略（写入规则）

所有联合登录共用一段编排 `_complete_oauth_login(provider, identity)`：按 `(provider, sub)` 命中 → 该用户；否则当
`email_verified=true` 且邮箱命中已有用户 → 新建 oauth_accounts 链接；都不命中 → 新建无密码 user + 链接。**未验证邮箱不得自动链接到已有账号。**

各 provider 的 `email` / `email_verified` 来源：
- **Google**：id_token 的 `email` + `email_verified`（Google 总有邮箱）。
- **飞书 / Lark**：仅把 `enterprise_email`（管理员分配、组织管控，可信）作为 email 并视作 `email_verified=true`；
  用户自填的 `email` 字段**不参与链接**（不可信）。无 `enterprise_email` 时 `email=None, email_verified=False`，
  create 分支合成占位邮箱 `{union_id}@{provider}.local`（满足 `users.email` 非空+唯一；合成域 `.local` 不与真实邮箱冲突，
  故不会与已有账号撞唯一索引）。**无 schema 变更**：复用既有 `users` / `oauth_accounts`（迁移仍为 `0001` + `0003`）。
