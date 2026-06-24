# infrastructure/external/lark

飞书 / Lark 身份适配器（实现 `application/ports/oauth.py` 的 `LarkAuthCodeExchanger`）。

飞书（`open.feishu.cn`）与 Lark 国际（`open.larksuite.com`）端点路径相同、仅域名不同，故共用同一份实现，由 `host` 区分。

| 文件 | 职责 |
|---|---|
| `code_exchanger.py` | `LarkAuthCodeExchanger` —— **授权码流**：POST `{host}/open-apis/authen/v2/oauth/token`（`client_id+client_secret+code`，v2 OIDC，无需先取 app_access_token）换 `access_token`，再 GET `{host}/open-apis/authen/v1/user_info`（`Authorization: Bearer`）拿身份，返回 `OAuthIdentity`。映射 `sub=union_id or open_id`、`email=enterprise_email or None`、`email_verified=bool(enterprise_email)`。任一步失败 / 缺 sub 抛 `InvalidTokenException`（不回显 secret/token）。`LARK_OPEN_HOSTS` 提供 provider→host 映射。 |
| `__init__.py` | 导出 `LarkAuthCodeExchanger`、`LARK_OPEN_HOSTS`。 |

与 Google 适配器的差异：飞书/Lark 不返回可本地验签的 `id_token`，身份靠 `user_info` 接口（多一次 HTTP）；稳定标识用 `union_id` 而非 `sub`；`email` 可能缺失。

装配点：`api/dependencies.py` 的 `_get_oauth_exchangers()` —— 按 `FEISHU_APP_ID/SECRET`（host=feishu）与 `LARK_APP_ID/SECRET`（host=lark）分别懒装配，缺 id/secret 则该 provider 不可用（fail-closed），由 `POST /auth/oauth/{provider}` 消费。

链接策略：只把 `enterprise_email`（管理员分配、组织管控）当作「已验证邮箱」用于自动链接已有账号（等价 Google `email_verified=true`）；无 email 时上层合成占位邮箱 `{union_id}@{provider}.local` 建独立账号。详见 `docs/project/data/auth.md`。
