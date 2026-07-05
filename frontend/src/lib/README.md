# src/lib — 跨域基础设施

被 features / routes / components 复用的客户端基础设施模块（无 UI、无业务规则）。

| 文件 | 职责 | 对外导出 |
|------|------|---------|
| `utils.ts` | className 合并工具 | `cn(...inputs)`（clsx + tailwind-merge） |
| `apiClient.ts` | 统一 HTTP 客户端（注入 Bearer + 401 单飞刷新） | `apiClient`（axios 实例，`baseURL = ${VITE_API_URL}/api/v1`，`withCredentials`） |
| `authStore.ts` | 客户端会话存储（token 持久化 + 变更订阅，`useSyncExternalStore` 兼容） | `type Session`、`getSession`、`setSession`、`clearSession`、`subscribe` |
| `queryClient.ts` | 全局共享的 React Query 客户端单例 | `queryClient` |
| `tokenPair.ts` | 后端 token 信封形状的唯一声明 + 到 `Session` 的映射（apiClient 刷新与 auth feature 共用） | `type TokenPairResponse`、`toSession(d)` |

## 约定

- `apiClient` 的 `baseURL`：`VITE_API_URL` 留空时为相对路径 `/api/v1`，经 Vite dev 代理转发到后端避免 CORS；设为绝对地址时直连后端。
- `apiClient` 响应拦截器在受保护端点首次 401 时用 `refresh_token` 静默刷新一次并重放原请求；并发 401 共享同一次刷新（单飞），刷新走裸 `fetch` 避免拦截器递归；刷新失败调 `clearSession`。
- `authStore` 的快照引用仅在 `setSession` / `clearSession` 时变更，满足 `useSyncExternalStore` 对稳定引用的要求；会话持久化在 `localStorage('vibejet.session')`。`clearSession` 会连带 `queryClient.clear()`，避免换用户后旧缓存被命中。
- `queryClient` 为单例：`main.tsx` 用它挂 `QueryClientProvider`，`authStore.clearSession` 登出时清同一份缓存；不在 `queryClient.ts` 内 import `authStore`（保持 `authStore → queryClient` 单向无环）。
- 这些模块只做技术能力封装，不含业务逻辑；业务用例编排在 `features/<x>/hooks/`。
