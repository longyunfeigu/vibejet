# infrastructure/external/google

Google 身份验证适配器（实现 `application/ports/oauth.py` 的 `GoogleIdentityVerifier`）。

| 文件 | 职责 |
|---|---|
| `verifier.py` | `GoogleIdTokenVerifier` —— 用 `google-auth` 验 Google ID Token（签名 / `aud==GOOGLE_CLIENT_ID` / `iss` / `exp`），返回 `GoogleIdentity`；失败抛 `InvalidTokenException`。 |
| `dev_verifier.py` | `DevGoogleVerifier` —— **仅非生产**：不验签直接解码 credential（JSON 或 JWT payload 段），用于 mock-first 联调。生产禁用。 |
| `__init__.py` | 导出上述两者。 |

装配点：`api/dependencies.py` 的 `_get_google_verifier()` —— 有 `GOOGLE_CLIENT_ID` 用真验签，否则非生产降级 dev，生产返回 None（`/auth/google` 拒绝）。
