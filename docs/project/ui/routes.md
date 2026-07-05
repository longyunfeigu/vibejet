# UI Routes

路由树、角色守卫、导航入口与跨 Epic 占位关系（vj-epic-plan 命中 route delta 时同步）。

## 路由树

| Route | Screen | 守卫 | 导航入口 | 状态 |
|-------|--------|------|----------|------|
| `/` | home（既有） | beforeLoad 登录守卫 | AppShell | active |
| `/login` | login（既有，front-of-house 编辑艺术轨） | 未登录可达 | 直达 | active |
| `/auth/callback` | OAuth 回调（既有） | - | - | active |
| `/record` | [screen-meal-record](surfaces.md#screen-meal-record) | beforeLoad 登录守卫（照抄 `routes/index.tsx`） | Epic 1 内直达 URL；首页拍照入口占位归 **Epic 2**（今日总览空态的醒目拍照入口） | planned (Epic 1) |

## 跨 Epic 占位

- Epic 2 落地时：首页（`/`）需提供 `/record` 的主入口（含今日无记录空态的醒目拍照引导，PRD Epic 2 R4）；届时更新本表导航入口列。
