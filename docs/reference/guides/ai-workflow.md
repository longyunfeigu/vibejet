# AI Workflow

这份文档定义当前仓库推荐的 AI 开发工作流。

如果你希望把当前多 skill 主线收敛成单入口编排，见 [run-story-design.md](run-story-design.md)。

目标不是罗列所有 skill，而是回答 3 个实际问题：

1. 现在应该先用哪个 skill
2. 什么时候需要补 plan / API 契约 / 数据模型说明
3. 一个 Story 从开始到收口，完整链路是什么

## 1. 默认主线

现在推荐的默认入口是：

```text
run-story
```

当用户已经有 Story，并希望按仓库默认流程一路做到实现、验证、review 和按需 QA 时，优先使用 `run-story`。

它内部会路由到：
- `do-story`
- 或 `story-reference-impl`
- 然后继续进入 `story-verify-fix -> review -> diff-aware-qa（按需）`

日常实现 Story 时，默认遵循这条主线：

```text
默认外部入口:
  run-story

内部路由:
  普通 Story -> do-story
  复杂 Story / 需要参考开源实现 -> story-reference-impl

统一后续:
  -> story-verify-fix
  -> review
  -> diff-aware-qa（如改动有回归风险）
```

这是当前仓库的默认开发闭环。

## 2. 按阶段看该用什么

### 阶段 A：需求还没成 Story

当你在下游应用里还没有明确 Story，只是有一个产品想法或较大的需求时：

```text
vj-product-requirements
-> vj-architecture
-> vj-epic-story
-> vj-epic-plan（前端项目同步 Screen Contract）
-> vj-work
```

产出物通常是当前项目的需求、架构增量和 Story/Epic 文档；若在下游产品仓库使用，则落在下游仓库自己的 `docs/` 下。

适用场景：
- 新需求还没拆解
- 需要先把产品目标和技术边界定下来
- 需要把需求拆成可执行的 Epic / Story

### 阶段 B：开始实现 Story

#### 1. 推荐默认入口

优先用 [run-story](../.agents/skills/run-story/SKILL.md)。

适用场景：
- 用户想端到端处理一个已有 Story
- 不想手动切换 skill
- 希望默认带上 verify / review / 按需 QA

#### 2. 普通 Story

用 [do-story](../.agents/skills/do-story/SKILL.md)。

适用场景：
- 需求边界已经比较清楚
- 不需要专门研究外部开源实现
- 改动范围可控

`do-story` 的职责：
- 读取 Story 内容
- 读取现有架构约束
- 判断 Flow A / B / C
- 生成或消费 plan
- 按 DDD 分层实现

#### 3. 复杂 Story

用 [story-reference-impl](../.agents/skills/story-reference-impl/SKILL.md)。

适用场景：
- 技术实现复杂
- 需要参考 GitHub / 开源项目 / 框架官方文档
- 想先研究、再适配、最后实现

`story-reference-impl` 的链路是：

```text
研究参考实现
-> DDD 适配设计
-> 分层实现
-> Review
```

### 阶段 C：实现完成后的收口

实现完成后不要直接结束。默认继续跑：

1. [story-verify-fix](../.agents/skills/story-verify-fix/SKILL.md)
2. [review](../.agents/skills/review/SKILL.md)
3. [diff-aware-qa](../.agents/skills/diff-aware-qa/SKILL.md)（按需）

职责区分：

- `story-verify-fix`
  - 验证当前 Story 自己是否通过
  - 启动后端，必要时启动前端
  - 跑 API / 联调 / 可选视觉检查
  - 失败时进入有限修复循环

- `review`
  - 做结构化代码审查
  - 优先找 blocking 问题、回归风险、缺失测试
  - 基于 `docs/reference/guides/review-checklist-python-fastapi.md`

- `diff-aware-qa`
  - 做第二层回归 QA
  - 关注“这次 diff 还波及了哪些页面 / 路由 / 接口”
  - 不是 Story 验收，而是影响面回归

## 3. 什么时候用 api-design 和 data-model

这两个 skill 现在都不是默认前置步骤。

### api-design

只在以下情况命中时使用：
- 新增 / 删除端点
- 请求 / 响应 schema 变化
- 错误码、分页、过滤、鉴权、幂等契约变化

默认产出是 **API Contract Delta**，不是一整份大文档。

### data-model

只在以下情况命中时使用：
- 新增表、字段、索引、约束
- 新增 migration
- 事务、一致性、幂等、状态流转相关的持久化模型变化

默认产出是 **Schema / Migration Delta**，不是一整份全库建模文档。

### 重要边界

如果对应的 `docs/project/api/{module}.md` 或 `docs/project/data/{module}.md` 不存在：

- AI 不能说“实现违反了这些文档”
- 只能判断“本次改动是否引入了新的 contract / schema delta，需要补说明”
- 命中 delta 时同步创建或更新模块文档；旧 `api_spec.md` / `database_schema.md` 仅作为兼容读取 fallback

始终可校验的是：
- repo 硬约束
- Story 验收标准
- 现有代码模式

## 4. Plan 应该怎么用

Plan 文件放在 `docs/tasks/plans/`，按该目录下的 `TEMPLATE.md` 创建
（§0 Triage 8 问 → Flow A/B/C → 分层填写）。

### Flow A / B / C

- `Flow A`
  - 小范围改动
  - 只填第一层和执行步骤

- `Flow B`
  - 多层改动
  - 填第一层 + 第二层

- `Flow C`
  - 高风险或多模块变更
  - 填完整 plan

### Plan 里现在有哪些关键 section

- `§0 Triage`
  - 判断是不是改 API 契约、DB schema、domain 规则等

- `§8.1 API Contract Delta`
  - 当改接口时填写
  - 同步写入 `docs/project/api/{module}.md`；全局约定变化才改 `docs/project/api/conventions.md`

- `§8.2 设计参考`
  - 当前端 Story 有设计稿时填写

- `§10.1 Schema / Migration Delta`
  - 当改表结构或 migration 时填写
  - 同步写入 `docs/project/data/{module}.md`
  - 如果当前项目维护数据模块索引，同时更新对应索引；没有索引时不要引用已归档的历史 overview

## 5. 前端设计怎么接入

前端设计生产端拆进主链路，并分成两条轨道。这里的原则是：**Screen Contract 完整度强制，ui-* skill 调用按缺口强制触发**。不要为了形式固定跑满所有 UI skill；也不能在字段缺失时跳过或自由发挥。

### 5.1 产品/品牌方向轨（低频）

当项目缺 `docs/project/DESIGN.md`、`DESIGN.md` 明显过期、品牌感不清、登录/落地/首个空态没有 golden screen，或用户明确要求“整体 UI 更好看 / 更有品牌感”时，必须先补产品/品牌方向：

```text
产品级 ui-requirement-brief
-> vj-design-md-matcher
-> docs/project/DESIGN.md
-> docs/reference/research/designs/golden/
```

这一轨解决“这个产品应该长什么样”：品牌气质、颜色/字体/间距/圆角/阴影、屏型富度地板、Reference Skeletons、front-of-house 的品牌表达和 golden screens。它不是每个 Story 都跑，也不在 `vj-work` 执行期临时跑。

### 5.2 单屏体验轨（按缺口强制）

每个 UI Screen 都必须有完整页面体验地图 / Screen Contract：

```text
Screen type
Route
Role
Primary Job
Regions
Information Priority
Key States
Richness Floor
Forbidden Patterns
API-for-UI
Screen done
Design source pointers
```

缺哪个维度，就必须调用对应 skill 补齐：

| 缺口 | 强制补齐方式 |
|------|--------------|
| 产品/品牌方向、登录/落地页 golden 缺失 | 产品级 `ui-requirement-brief -> vj-design-md-matcher` |
| 单屏目标、模块顺序、信息层级不清 | `ui-page-goal-structure` |
| loading / empty / error / disabled / permission 等状态不清 | `ui-state-coverage` |
| 复杂操作流不清 | `ui-user-journey-audit` |
| UI 截图完成后视觉不稳定或 UI-critical 屏验收 | `ui-visual-consistency-audit` |
| 可复用组件需要沉淀规格 | `ui-component-spec-audit` |
| 交付研发/QA 前规格不完整 | `ui-handoff-readiness-check` |

复杂操作流不按页面名称枚举，按流程特征判定。命中任一项，就必须补 `ui-user-journey-audit`：

- 用户需要连续完成 2 步以上。
- 中途有权限、资格、库存、余额、次数、审核、风控或依赖数据判断。
- 有提交、保存、发布、支付、删除、审批等不可轻易撤销动作。
- 需要 loading / success / error / retry / rollback / cancel / back / resume 等恢复路径。
- 操作结果会改变业务状态，或影响其他用户 / 下游流程。

登录、注册、提交、审核、支付、上传、发布、导入、开通、邀请、删除等只是常见示例，不是白名单。

清楚的屏不重复跑；不清楚的屏必须补齐。典型链路是：

```text
vj-epic-story 生成/检查页面体验地图
-> 缺字段时调用对应 ui-* skill 回填
-> vj-epic-plan 投影为 Screen Contract
-> vj-work 按合同整屏实现
```

### 5.3 稳定合同

- `docs/project/DESIGN.md` 是视觉与品牌合同，包含 token、屏型富度地板、Reference Skeletons、Do / Don't。
- `docs/reference/research/designs/golden/` 是屏型金标准，尤其用于 login / signup / landing / 首个空态和核心 operational screen。
- `docs/project/ui/surfaces.md` 是 Screen Contract：route、screen type、primary job、regions、states、API-for-UI、screen done、richness floor、forbidden patterns。
- `docs/project/ui/routes.md` 是路由、导航、守卫和入口合同。
- `vj-feature` / `vj-epic-story` 先判定走产品/品牌方向轨、单屏体验轨、两者都需要，或不需要 UI 前置。
- `vj-epic-plan` 把页面体验地图投影成 Screen Contract 并同步 `docs/project/ui/`；如果方向源缺失，先把 `ui-requirement-brief -> vj-design-md-matcher` 列为待办/阻塞，不在 plan 里发明风格。
- `vj-work` 读取 `DESIGN.md + golden + docs/project/ui/` 实现整屏，并用截图 + 独立视觉审查过 gate。

下面是 `do-story` 对 UI 设计图的**发现**顺序：

1. Story 文件里的 `### 设计参考` 表格
2. `docs/reference/research/designs/{epic-id}/` 下以 `{story-id}` 开头的图片
3. 当前对话里用户显式提供的路径或 URL

推荐命名：

```text
docs/reference/research/designs/{epic-id}/{story-id}-{page}.png
docs/reference/research/designs/{epic-id}/{story-id}-{page}-{state}.png
```

例如：

```text
docs/reference/research/designs/epic-003/3.2-dashboard.png
docs/reference/research/designs/epic-003/3.2-dashboard-empty.png
docs/reference/research/designs/epic-003/3.2-dashboard-mobile.png
```

如果自动发现失败，但你又要求“按设计稿还原”，那就需要手动给路径或 URL，不要让 AI 猜。

即使没有外部设计图，前端 Story 也不能退化成 AC 最小实现：

- `front-of-house`（login / signup / landing / 空首屏 / 营销页）必须有品牌/产品身份、价值点或信任点、视觉锚点、主 CTA 默认可操作态和三态；禁止单一居中表单卡。
- `operational`（dashboard / table-list / detail / form / settings）必须有主数据容器、工具条/筛选、统计或摘要、行/批量操作和三态；禁止孤立卡片堆和巨型录入框当主视觉。
- 如果 `DESIGN.md` 或 golden screen 缺失，不能指望 `ui-page-goal-structure` / `ui-state-coverage` 让 UI 自动变好看；它们只补单屏体验合同。先补产品/品牌方向轨，再进单屏实现。
- `vj-work` 完成 UI-critical 屏前必须保留桌面 + 移动截图，并由非实现者或 `ui-visual-consistency-audit` 做 pass/fail。

## 6. 多窗口 / 并行开发怎么做

本仓库当前不内置专门的 Story 状态技能。多人或多窗口同时工作时，优先用以下方式降低冲突：

- 在 Plan 中明确文件所有权、依赖关系和阻塞点
- 用 Git 分支或 worktree 隔离并行实现
- 对会互相影响的 DB migration、公共接口、共享组件提前串行化
- 在执行日志或 PR 描述里记录 Story 的 `done / blocked / risk` 状态

## 7. 几条典型工作流

### 场景 1：默认单入口

```text
已有 Story
-> run-story
```

### 场景 2：普通后端 Story（手动模式）

```text
已有 Story
-> do-story
-> 如改接口：补 API Contract Delta
-> 如改 migration：补 Schema / Migration Delta
-> story-verify-fix
-> review
```

### 场景 3：复杂后端 Story，参考开源实现（手动模式）

```text
已有 Story
-> story-reference-impl
-> 研究参考实现
-> DDD 适配设计
-> 实现
-> story-verify-fix
-> review
```

### 场景 4：前后端联调 Story，且有设计稿（手动模式）

```text
已有 Story
-> do-story
-> Story / docs/designs 中提供设计参考
-> story-verify-fix
   -> 启动后端
   -> 启动前端（如存在可运行前端）
   -> 跑联调
   -> 做轻量视觉对齐
-> review
-> diff-aware-qa
```

## 8. 当前仓库的现实约束

这几点必须记住：

- 当前仓库包含可编辑的 `frontend/src/`，前端实现按 `AGENTS.md` 的 React + TypeScript + Vite + Tailwind + shadcn 约束执行。
- 需要真实前端代码改动时，先确认目标 Route / Screen Contract / 设计来源是否齐备。
- `story-verify-fix` 可以做运行时验证和视觉检查，但不替代缺失的前端源码

## 9. 一句话决策表

| 你现在手上的任务 | 用什么 |
|------------------|--------|
| 已有 Story，想按默认链路一路做完 | `run-story` |
| 只有产品想法，还没拆 Story | `vj-product-requirements -> vj-architecture -> vj-epic-story` |
| 项目整体缺品牌/视觉方向，或登录/落地页缺 golden | 产品级 `ui-requirement-brief -> vj-design-md-matcher` |
| 已有 Epic/Story，要补前端设计合同 | `vj-epic-plan` 同步 `docs/project/ui/`；单屏缺结构/状态时强制用对应 `ui-*` skill 补齐 |
| 普通 Story 实现 | `do-story` |
| 复杂 Story，需要参考开源 | `story-reference-impl` |
| 实现完成后验证当前 Story | `story-verify-fix` |
| 做代码审查 | `review` |
| 查本次 diff 的回归风险 | `diff-aware-qa` |
| 多窗口跟踪 Story 占用和阻塞 | `story-status` |
| 做并行开发分组 / worktree 规划 | `parallel-dev-planner` |

## 10. 推荐默认顺序

如果你不想每次都重新判断，就按这个默认顺序走：

```text
需求未成型:
  vj-product-requirements
  -> vj-architecture
  -> vj-epic-story
  -> vj-epic-plan（前端项目同步 Screen Contract）
  -> vj-work

开始做 Story:
  run-story
  或（手动模式下）do-story / story-reference-impl

实现后:
  story-verify-fix
  -> review
  -> diff-aware-qa（按需）
```

这就是当前仓库推荐遵循的 AI 工作流。
