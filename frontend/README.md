# Vibejet Frontend

Vibejet 项目的前端工程。脚手架严格对齐 `.claude/skills/frontend-dev-guidelines/`。

## 技术栈

| 维度 | 选型 |
|---|---|
| 构建 | Vite 8 |
| 语言 | TypeScript 6（strict） |
| 框架 | React 19 |
| UI | MUI v9（emotion） |
| 路由 | TanStack Router（文件路由 + codegen） |
| 数据 | TanStack Query（`useSuspenseQuery` 为主） |
| 表单 | React Hook Form + Zod |
| 通知 | `useMuiSnackbar` hook（**禁用** react-toastify） |
| 测试 | Vitest + Testing Library + jsdom |
| Lint | ESLint flat config + Prettier |

> 注意：plan 写的是 MUI v7，实际 `pnpm add @mui/material` 拉到 v9.0.1（API 兼容 v7+，但 `Stack` 的 `alignItems` 已从 prop 移到 `sx`）。

## 启动

```bash
cd frontend
pnpm install
pnpm dev         # http://localhost:5173
```

其他命令：

```bash
pnpm build         # tsc -b && vite build → dist/
pnpm preview       # 本地预览 build 产物
pnpm typecheck     # tsc -b --noEmit
pnpm lint          # ESLint
pnpm format        # Prettier --write src/
pnpm format:check  # Prettier --check src/
pnpm test          # Vitest run（一次性）
pnpm test:watch    # Vitest watch
```

## 环境变量

`frontend/.env`：

```env
VITE_API_URL=http://localhost:8000
```

- `apiClient.baseURL = VITE_API_URL`（生产模式直接打 backend 绝对 URL）
- Dev 模式 Vite 把 `/api/*` 代理到 `VITE_API_URL`（见 `vite.config.ts`）

## 目录结构

```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/                    # 通用 UI 原子（Button、Input 等）
│   │   ├── layout/                # 布局（AppLayout）
│   │   └── SuspenseLoader/        # 项目级加载占位
│   ├── features/
│   │   └── {feature}/             # 按业务域聚合
│   │       ├── api/
│   │       ├── components/
│   │       ├── hooks/
│   │       ├── helpers/
│   │       ├── types/
│   │       └── index.ts           # 公共 API
│   ├── routes/                    # TanStack Router 文件路由
│   │   ├── __root.tsx             # 根路由（套 AppLayout）
│   │   ├── index.tsx              # /
│   │   └── {route}/index.tsx
│   ├── hooks/                     # 跨 feature 共享 hook
│   ├── contexts/                  # React Context Provider
│   ├── lib/                       # 工具与基础设施（apiClient）
│   ├── types/                     # 跨 feature 共享 type
│   ├── test/                      # Vitest setup
│   ├── main.tsx                   # React 入口
│   ├── index.css                  # 全局样式
│   ├── routeTree.gen.ts           # 自动生成（不要手改）
│   └── vite-env.d.ts
├── public/
├── package.json
├── tsconfig*.json
├── vite.config.ts
├── vitest.config.ts
├── eslint.config.js
├── .prettierrc.json
└── .env
```

## Path Alias

| 别名 | 指向 | 用途 |
|---|---|---|
| `@/` | `src/` | 通用 |
| `~types/` | `src/types/` | 类型 |
| `~components/` | `src/components/` | 组件 |
| `~features/` | `src/features/` | feature |

在 `tsconfig.app.json`（`paths`）和 `vite.config.ts`（`resolve.alias`）双侧配置。`vitest.config.ts` 镜像一份。

## 添加新 feature 的步骤

1. `src/features/{name}/` 建子目录：`api/` `components/` `hooks/` `types/`，建 `index.ts` barrel
2. `api/{name}Api.ts`：用 `apiClient` 包 endpoint
3. `hooks/use{Name}.ts`：用 `useSuspenseQuery` 包 query
4. `components/{Name}Card.tsx`：消费 hook，纯 UI
5. `src/routes/{name}/index.tsx`：用 `createFileRoute` + `lazy` + `<SuspenseLoader>` 包 component
6. `pnpm dev` 一次让 `routeTree.gen.ts` 自动重新生成

参考实现：`src/features/health/` + `src/routes/health/`。

## 已知限制 / TODO

1. **示例 health feature 在 dev 模式可能 CORS 失败**
   - backend `.env` 默认 `CORS_ORIGINS=["http://localhost:3000","http://localhost:8080"]`，**没有 5173**
   - 要么在 backend `.env` 加 `http://localhost:5173`，要么 frontend 改走 vite proxy（apiClient.baseURL 改成 `''`）

2. **vite proxy 只代理 `/api`，不代理 `/health`**
   - backend 的 `/health` 没挂在 `/api/v1` 前缀下（见 `backend/main.py:163`）
   - `healthApi` 用 absolute URL 直接打 backend，绕开 proxy

3. **auth 仅占位**
   - `src/hooks/useAuth.ts` 永远返回未登录
   - `apiClient` 拦截器未配置（无 Bearer token 注入、无 401 重定向）
   - 等首个真实需要登录的 Story 时落地

4. **没有 ErrorBoundary**
   - `useSuspenseQuery` 失败会冒到 React 默认 error handler
   - 后续真业务 feature 应在 route 层加 ErrorBoundary

5. **没有 i18n / Sentry / E2E**
   - 都按 plan 延后

## TanStack Router codegen

- `@tanstack/router-plugin` 在 dev/build 时扫描 `src/routes/` 自动生成 `src/routeTree.gen.ts`
- **该文件被跟踪**（不入 .gitignore）：因为 `build = tsc -b && vite build`，tsc 先跑，需要 gen 文件已存在
- 千万不要手改 `routeTree.gen.ts`，会被覆盖
- 加新 route 后跑一次 `pnpm dev`（或 `pnpm build`）让它重新生成，再 commit
