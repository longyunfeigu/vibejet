# src/lib — 跨域基础设施

被 features / routes / components 复用的客户端基础设施模块（无 UI、无业务规则）。

| 文件 | 职责 | 对外导出 |
|------|------|---------|
| `utils.ts` | className 合并工具 | `cn(...inputs)`（clsx + tailwind-merge） |
| `apiClient.ts` | 统一 HTTP 客户端 | `apiClient`（axios 实例，`baseURL = ${VITE_API_URL}/api/v1`，`withCredentials`） |
| `authStore.ts` | 客户端会话存储（token 持久化 + 变更订阅，`useSyncExternalStore` 兼容） | `type Session`、`getSession`、`setSession`、`clearSession`、`subscribe` |

## 约定

- `apiClient` 的 `baseURL`：`VITE_API_URL` 留空时为相对路径 `/api/v1`，经 Vite dev 代理转发到后端避免 CORS；设为绝对地址时直连后端。
- `authStore` 的快照引用仅在 `setSession` / `clearSession` 时变更，满足 `useSyncExternalStore` 对稳定引用的要求；会话持久化在 `localStorage('vibejet.session')`。
- 这些模块只做技术能力封装，不含业务逻辑；业务用例编排在 `features/<x>/hooks/`。
