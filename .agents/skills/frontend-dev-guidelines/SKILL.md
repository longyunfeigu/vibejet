---
name: frontend-dev-guidelines
description: Frontend development guidelines for vibejet's React + Vite + TypeScript + Tailwind v4 + shadcn/ui + TanStack stack. Use when creating components, pages, features, fetching data, styling, routing, forms, or working with frontend code. UI uses Tailwind utility classes + shadcn components (NOT MUI); design tokens come from docs/project/DESIGN.md compiled into src/index.css.
---

# Frontend Development Guidelines

## Purpose

vibejet 前端的统一规范。栈是当前最适合 AI coding 的组合：**React 19 + Vite + TypeScript(strict) + Tailwind v4 + shadcn/ui(Radix) + TanStack Router/Query + RHF/Zod**。样式用 Tailwind utility class + shadcn 组件，**不用 MUI / emotion / `sx`**。

设计 token 唯一来源 = `docs/project/DESIGN.md`，编译进 `frontend/src/index.css` 的 CSS 变量（`@theme` + `:root`）。改设计先改 DESIGN.md → index.css，**不在组件里硬编码颜色/圆角**。

## Canonical Stack（不要偏离）

| 关注点 | 选型 |
|---|---|
| 构建 | Vite 8 |
| 语言 | TypeScript strict（`@/` 单一别名；类型用 `import type`） |
| 样式 | Tailwind v4（CSS-first `@theme`，无 `tailwind.config.js`） |
| 组件 | shadcn/ui（new-york 风，Radix 原语，源码 copy 进 `src/components/ui/`，归你所有可改） |
| 类名合并 | `cn()` = clsx + tailwind-merge（`@/lib/utils`） |
| 变体 | class-variance-authority（cva），见 `ui/button.tsx` |
| 图标 | lucide-react |
| 数据 | TanStack Query（`useSuspenseQuery` 为主） |
| 路由 | TanStack Router（文件式，`routeTree.gen.ts` 由 dev 自动生成） |
| 表单 | React Hook Form + Zod（+ shadcn `Form`） |
| Toast | sonner（`import { toast } from 'sonner'`；`<Toaster/>` 已在 `main.tsx`） |
| HTTP | `apiClient`（axios，`@/lib/apiClient`，`baseURL=VITE_API_URL`，`withCredentials`） |

## New Component Checklist

- [ ] TS 函数组件 + props interface，命名导出 + 默认导出
- [ ] 样式用 Tailwind class；条件/合并用 `cn()`；多变体用 `cva`
- [ ] 复用 shadcn 组件（`@/components/ui/*`）；缺的用 `npx shadcn@latest add <c>` 拉进来（网络抖动见下方 curl 兜底）
- [ ] 颜色/间距/圆角走 token（`bg-background`/`text-foreground`/`text-muted-foreground`/`bg-primary`/`border-border`/`bg-card`/`bg-success`/`bg-destructive`…），不写裸 hex
- [ ] 数据用 `useSuspenseQuery`；**不写 `if (isLoading) return <Spinner/>` 这种 early-return**；外层包 `<SuspenseLoader>`
- [ ] 错误态用 route 的 `errorComponent` / ErrorBoundary + 重试；瞬时反馈用 `sonner`
- [ ] 图标用 lucide-react；交互元素要有 `focus-visible` 环（token `--ring`），键盘可达

## New Feature Checklist

```
features/<name>/
  api/<name>Api.ts       # 用 apiClient 包后端接口
  hooks/use<Name>.ts     # useSuspenseQuery 包装
  components/<Name>*.tsx # shadcn + Tailwind，消费 hook
  types/index.ts
  index.ts               # 公开 barrel
routes/<name>/index.tsx  # createFileRoute + lazy + <SuspenseLoader>
```

参考实现：`frontend/src/features/health/` + `frontend/src/routes/health/`。

## Product Richness（建富屏 — 别像 demo）

> 非协商铁律见 `.claude/rules/frontend.md`（按路径自动注入）。这里是 how-to。
> 核心：**屏丑通常不是栈 / DESIGN 的问题，是建得太薄。按页面体验地图建整屏，不停在 AC 最小；不许空屏。**

### 剧本 A：有可抄的高级作品（reference-based，首选）

1. **拿参考**：用户截图（最佳，最准、无登录墙）/ URL（用 web-access CDP 打开截**渲染图**，不能只 WebFetch HTML）/ 仅产品名（保真度较低）。挑**同屏类型**的参考（审核台找工单列表，仪表盘找 dashboard，别拿落地页参考表格）。
2. **拆"组成"不拆"皮"**：提取布局 / 信息密度 / 组件清单（统计卡 / 表格 / 筛选 / tabs / 徽章）/ 交互范式 / 间距层次；**丢掉品牌皮**（配色 / logo / 招牌字）。
3. **重皮肤化**：用 `DESIGN.md` token + shadcn 组件 + 真实/mock 数据落地 → 长得像本产品、但有参考的丰富度。
4. **对照**：截自己的图，跟参考比密度/组成、跟 DESIGN.md 比 token。

### 剧本 B：没有外部参考（from scratch）

1. **屏归型**：列表/控制台、仪表盘、详情、表单/向导、设置、空态——套该范式的标准富组成（控制台 = 工具条[筛选+搜索+主操作] + 密集表格 + 批量 + 统计摘要 + 行操作 + 全状态）。
2. **吃满「页面体验地图」**：把 epic 里该屏的 职责/主操作/次操作/关键状态/信息优先级 全建出来。
3. **品味工具按屏型选**：**front-of-house**（login/landing/营销）→ `design-taste-frontend` / `high-end-visual-design` 当"内化的高级标准"。**operational**（dashboard/table-list/审核台/detail/form/设置）→ **不调** `design-taste-frontend`（其 §13 明确 out-of-scope: dashboards/admin），改用 **`resources/dense-ui-craft.md`（operational 屏的 craft 真相源：间距分层/字重色阶层次/边框克制/对齐/微态/accent 预算）** + `DESIGN.md` §Richness Floor 对应屏型 + §Reference Skeletons + §Spacing Hierarchy + 一个密集后台参考（Linear/Airtable/Retool/Carbon）。两个方向都违规：marketing 留白（巨型空框、半屏 hero）和 wall-to-wall 挤死（页框/区块层用组件内间距）。

### 数据规则（不许空屏）

- 后端先行 → 接真接口（dev 库要有 seed 数据）。
- 后端没好 / 前后端并行 → `features/<x>/mock*.ts` 占位，**接口落地即删**。

### 富度 checklist（自检）

- [ ] 整屏按页面体验地图建全（外壳/导航/次操作），不是 AC 最小
- [ ] 有数据就上表格/统计/筛选，不堆孤立卡片
- [ ] 三态齐：加载(Skeleton) / 空(图标+引导动作) / 错误(原因+重试)
- [ ] 间距分四层（页框→区块→容器→组件，DESIGN.md §Spacing Hierarchy）；数值 mono 右对齐；状态 = 圆点+文案；长文截断 + title
- [ ] 资深 PM 一眼看像"已上线"，而不是 demo；也不像 Excel（见 `resources/dense-ui-craft.md` 反模式速查）
- [ ] **过 `.claude/rules/frontend.md`「出口闸：品味」对应轨**（done 前置条件；闸门条目以该文件为唯一真相源，不在此复述）：front-of-house 走 A 轨（A1–A3），operational 走 B 轨（B1–B5，内含工艺线 C1–C5）。任一不过则迭代，不准标 done。

## Styling（Tailwind v4 + shadcn）

- Utility class 内联，写在标记旁；合并/条件用 `cn(...)`。
- **禁止** `sx` prop、MUI theme、emotion、styled。
- 设计 token = CSS 变量（在 `src/index.css` 的 `:root` + `@theme inline`，源自 DESIGN.md）。语义类直接用：`bg-background text-foreground border-border bg-card bg-muted text-muted-foreground bg-primary text-primary-foreground bg-success bg-warning bg-destructive` 等。
- 多变体组件用 `cva`（看 `src/components/ui/button.tsx` 的写法）。
- 布局用 Tailwind `flex`/`grid`/间距 class（**不用 MUI Grid**）；响应式用 `md:`/`lg:` 断点。
- 改主题色/圆角/字体：改 `docs/project/DESIGN.md` → 同步 `src/index.css` 的 token，不在组件里硬编码。

## shadcn/ui 用法

- 组件是**复制进 `src/components/ui/` 的纯 TSX**（Radix + Tailwind），就是你的代码，可直接改。
- 添加：`npx shadcn@latest add button card dialog form table dropdown-menu ...`
- **registry 网络抖动兜底**（本仓库环境 `ui.shadcn.com` 偶发并发失败，单发 curl 稳定）：
  ```bash
  curl -s "https://ui.shadcn.com/r/styles/new-york-v4/<comp>.json" -o /tmp/c.json
  # 把 .files[].content 写到 src/components/ui/<comp>.tsx；把 .dependencies 用 pnpm add 装上
  ```
- `components.json` 是配置（new-york / neutral / cssVariables:true / `@/` 别名 / lucide）。Radix 走统一包 `radix-ui`（`import { Slot } from 'radix-ui'`）。

## Data Fetching（useSuspenseQuery）

- 每 feature 一个 `api/<name>Api.ts`，方法用 `apiClient`。
- `hooks/use<Name>.ts` 用 `useSuspenseQuery({ queryKey, queryFn })`，组件直接拿 `data`（无 `isLoading` 判断）。
- 外层用 `<SuspenseLoader>`（`@/components/SuspenseLoader`，Skeleton fallback）。
- 失败：靠 route `errorComponent` 或 ErrorBoundary 兜，给原因 + 重试（对应 DESIGN 三态强制）。
- query 默认项见 `main.tsx`（staleTime 30s、不 refetchOnWindowFocus、retry 1）。

## Routing（TanStack Router，文件式）

- `routes/<name>/index.tsx` 用 `createFileRoute('/<name>/')({ component, loader })`。
- 重组件用 `lazy(() => import(...))` 包，再套 `<SuspenseLoader>`。
- `src/routeTree.gen.ts` 由 `@tanstack/router-plugin` 在 `pnpm dev` 时自动生成，**不手改**；新增/改路由后跑一次 dev 重生。

## Forms（RHF + Zod + shadcn Form）

- zod schema + `zodResolver`；用 shadcn `Form/FormField/FormItem/FormLabel/FormControl/FormMessage`。
- 标签置于输入上方；必填加 `*` + `aria-required`；错误文案在字段下方（DESIGN §Component Rules）。
- 任一必填缺失禁用提交并就地提示。

## 三态（DESIGN 强制：加载/空/错误）

- **加载**：`SuspenseLoader` 骨架屏；按钮内联 spinner + 禁用；禁止整页空白。
- **空**：图标 + 一句说明 + 主引导动作。
- **错误**：ErrorBoundary/`errorComponent` + 原因 + 重试；瞬时用 `sonner` toast（成功/失败用语义色）。
- 状态表达 = 颜色 + 图标 + 文案三件套，不只靠颜色（无障碍）。

## File Organization

- `features/`：领域相关（每个含 `api/ components/ hooks/ types/`，可选 `helpers/`）。
- `components/ui/`：shadcn 组件（vendored）。`components/layout/`：外壳。`components/<Shared>/`：跨域复用（如 `SuspenseLoader`）。
- `lib/`：`apiClient`、`utils`(cn)。`hooks/`：跨域 hook（如 `useAuth` 占位）。

## TypeScript / Performance

- strict、不用 `any`、显式返回类型、类型导入用 `import type`（`verbatimModuleSyntax` 开启）。
- `useMemo`/`useCallback` 用于昂贵计算与传给子组件的 handler；重组件 `React.lazy`；`React.memo` 谨慎用。

## Core Principles

1. **Tailwind + shadcn + DESIGN.md token**，绝不 MUI/`sx`/裸 hex。
2. **`useSuspenseQuery` + `<SuspenseLoader>`**，不写 early-return loading。
3. `cn()` 合并 class，`cva` 管变体。
4. shadcn 组件是 vendored、可改的你自己的代码。
5. `@/` 单一别名。
6. Toast 用 sonner，图标用 lucide。
7. 三态（加载/空/错误）必备；状态 = 色 + 图标 + 文案。

## Reference

- 参考实现：`frontend/src/features/health/`、`frontend/src/routes/health/`、`frontend/src/components/ui/*`、`frontend/src/index.css`(token)。
- 设计来源：`docs/project/DESIGN.md`（token / 字阶 / §Spacing Hierarchy / §Richness Floor / §Reference Skeletons）。
- 密屏工艺：`resources/dense-ui-craft.md`（operational 屏 craft 真相源）。
