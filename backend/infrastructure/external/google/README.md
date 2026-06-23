# infrastructure/external/google

Google 身份验证适配器（实现 `application/ports/oauth.py` 的 `GoogleIdentityVerifier` 与 `GoogleAuthCodeExchanger`）。

| 文件 | 职责 |
|---|---|
| `code_exchanger.py` | `GoogleAuthCodeExchanger` —— **授权码流**：用 `client_secret` POST `oauth2.googleapis.com/token` 把 authorization code 换成 `id_token`，再交给 `GoogleIdTokenVerifier` 验签返回 `GoogleIdentity`；交换失败 / 缺 `id_token` 抛 `InvalidTokenException`。popup 模式 `redirect_uri="postmessage"`。 |
| `verifier.py` | `GoogleIdTokenVerifier` —— 用 `google-auth` 验 Google ID Token（签名 / `aud==GOOGLE_CLIENT_ID` / `iss` / `exp`），返回 `GoogleIdentity`；失败抛 `InvalidTokenException`。被 `code_exchanger` 复用。 |
| `dev_verifier.py` | `DevGoogleVerifier` —— **仅非生产**、不验签直接解码 credential，用于旧 ID-token 流 mock-first 联调。**当前授权码流未接线**（保留备用）。 |
| `__init__.py` | 导出上述三者。 |

装配点：`api/dependencies.py` 的 `_get_google_exchanger()` —— 仅当 `GOOGLE_CLIENT_ID` 与 `GOOGLE_CLIENT_SECRET` 同时配置时组装交换器（内部建一个 `GoogleIdTokenVerifier` 复用验签）；缺任一返回 None → `/auth/google` 拒绝（fail-closed）。
