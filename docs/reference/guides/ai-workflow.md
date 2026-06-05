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
-> vj-ui-mock（前端项目：先 Phase A 出全局设计基座，再按 Epic 出每屏 v0 提示词）
```

产出物通常是下游应用自己的需求、架构增量和 Story/Epic 文档。`vibejet` 基础库不长期保留具体产品 PRD 或业务 Epic。

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

Plan 模板见 [TEMPLATE.md](../../tasks/plans/TEMPLATE.md)。

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
  - 同步写入 `docs/project/data/{module}.md`，并更新 `docs/project/data/overview.md`

## 5. 前端设计图怎么接入

设计图的**生产**用 `vj-ui-mock`：

- Phase A 产出全局设计基座 `docs/project/design_guidelines.md`（信息架构 / 导航骨架 / 设计系统 / 三态约定）
- Phase B 按 Epic/Story 产出每屏 v0/Lovable 提示词，落盘到 `docs/reference/research/designs/{epic-id}/{story-id}-{page}.prompt.md`，并回填 Story 的 `### 设计参考`
- 你把提示词粘进 v0/Lovable 出图后，将截图保存为同目录 `{story-id}-{page}.png`

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

- 当前 `frontend/` 默认不是可编辑源码目录，不要假设存在 `frontend/src/`
- 需要真实前端代码改动时，先确认正确的前端 workspace
- `story-verify-fix` 可以做运行时验证和视觉检查，但不替代缺失的前端源码

## 9. 一句话决策表

| 你现在手上的任务 | 用什么 |
|------------------|--------|
| 已有 Story，想按默认链路一路做完 | `run-story` |
| 只有产品想法，还没拆 Story | `vj-product-requirements -> vj-architecture -> vj-epic-story` |
| 已有 Epic/Story，要出前端设计基座与每屏提示词 | `vj-ui-mock` |
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
  -> vj-ui-mock（前端项目，可选）

开始做 Story:
  run-story
  或（手动模式下）do-story / story-reference-impl

实现后:
  story-verify-fix
  -> review
  -> diff-aware-qa（按需）
```

这就是当前仓库推荐遵循的 AI 工作流。
