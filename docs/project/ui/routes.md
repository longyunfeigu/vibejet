# UI Routes — 路由树与守卫

> 路由 / 守卫 / 导航真相源。`planned (Epic N)` 条目为拟议合同，实现验证通过后翻 `active`。
> 前端为 TanStack Router file-based（`frontend/src/routes/`）。

## 路由树

| Route | 文件 | 守卫 | 状态 | 说明 |
|-------|------|------|------|------|
| `/` | `routes/index.tsx` | 未登录 → redirect `/login`（`beforeLoad`） | active | 占位首页；`errorComponent` = `HomeError`（会话失效 → 重新登录；其他失败 → 重试） |
| `/login` | `routes/login/index.tsx` | 已登录 → redirect `/`（`beforeLoad`） | active | front-of-house 编辑艺术轨（已实现） |
| `/auth/callback` | `routes/auth/callback.tsx` | 公开 | active | 飞书 / Lark OAuth 回调（`code` + `state`） |

## 导航壳

- 现状：`AppShell`（`frontend/src/components/layout/AppShell.tsx`）。
