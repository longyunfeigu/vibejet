# UI Routes — 路由树与守卫

> 路由 / 守卫 / 导航真相源。`planned (Epic N)` 条目为拟议合同，实现验证通过后翻 `active`。
> 前端为 TanStack Router file-based（`frontend/src/routes/`）。

## 路由树

| Route | 文件 | 守卫 | 状态 | 说明 |
|-------|------|------|------|------|
| `/` | `routes/index.tsx` | 未登录 → redirect `/login`（`beforeLoad`） | active | 占位首页 |
| `/login` | `routes/login/index.tsx` | 公开 | active | front-of-house 编辑艺术轨（已实现） |
| `/auth/*` | `routes/auth/` | 公开 | active | OAuth 回调等 |

## 导航壳

- 现状：`AppShell`（`frontend/src/components/layout/AppShell.tsx`）。
