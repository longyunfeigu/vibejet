# AI Workflow

这份文档定义当前仓库推荐的 AI 开发工作流。

目标不是罗列所有 skill，而是回答 3 个实际问题：

1. 现在应该先用哪个 skill
2. 什么时候需要补 plan / API 契约 / 数据模型说明
3. 一个需求从想法到收口，完整链路是什么

## 1. 默认入口与三条交付轨

```text
vj router
  Patch -> 复现/断言 -> 窄改动 -> focused verify -> risk-based review
  Story -> Intent Contract -> 轻量执行计划 -> 实现/验证 -> risk-based review
  Epic  -> PRD/Architecture（按需）-> Epic/Story -> vj-epic-plan
        -> vj-plan-review -> vj-work -> E2E/review/QA（按风险）
```

默认先用 `vj` 选择最小可靠交付轨。Patch 不建 Story/Plan；普通 Story 可保留 durable Story，
但不默认生成 Epic review pack；只有命中 AGENTS.md strict trigger、跨 bounded context 或多个
独立能力时进入完整 Epic 链。

所有轨先建立 Intent Contract（目标/范围/非目标/可观察 done）和 Execution Contract
（轨道/风险/写面/验证/commit policy）。运行态写 `.vj/runs/*/run-state.json`；用户明确“不要
commit”时任何轨都不得创建 workflow commit。

## 2. 按阶段看该用什么

### 阶段 A：需求还没成 Story

当你还没有明确 Story，只是有一个产品想法或较大的需求时：

```text
vj-product-requirements
-> vj-architecture
-> vj-epic-story
-> vj-epic-plan（前端项目同步 Screen Contract）
-> vj-work
```

产出物通常是当前项目的需求、架构增量和 Story/Epic 文档；若在下游产品仓库使用，则落在下游仓库自己的 `docs/` 下。

PRD 定稿后想先看产品长什么样，再决定拆解方向：在进入 `vj-architecture` / `vj-epic-story`
之前按需插入 `vj-mock-board`（PRD → 单文件 mock board，缺 `DESIGN.md` 时它会先路由
§5.1 的方向轨）。板是研究产物，`vj-epic-story` 拆解与 `vj-epic-plan` 的 Screen Contract
可引用它作结构参考。

适用场景：
- 新需求还没拆解
- 需要先把产品目标和技术边界定下来
- 需要把需求拆成可执行的 Epic / Story

已有项目加单个、需要长期追踪的功能时，用 `vj-feature` 生成 durable Story；需求清楚且不需要
长期追踪时，`vj` 可直接选择 Story 轨执行。

### 阶段 B：计划与实现

#### 1. Epic 出计划

用 [vj-epic-plan](../../../.agents/skills/vj-epic-plan/SKILL.md)。

- 输入是 `docs/work/epics/` 下已拆好的 Epic（含 Story + 可执行 AC）
- 输出是 review pack 目录（README / design / decisions）+ task packets + catalog 同步
- 写盘后自动触发 `vj-plan-review` 做多视角审查
- handoff 前依次通过 `plan_lint.py`（结构）和 `workflow_doctor.py plan`（命令/路径/运行时语义）

#### 2. 执行

用 [vj-work](../../../.agents/skills/vj-work/SKILL.md)。

- 消费 vj-epic-plan 的 task packets，按 Task DAG / 波次推进
- auto 模式自动判定 fast / strict：命中权限、迁移、公共契约、事务、UI shell 等
  strict trigger 时自动升级
- worktree 隔离写代码；Unit 的 `Verification` 命令是 done signal
- 前端按 Screen/Route 整体交付，UI-critical 屏有独立截图审查 gate
- 开工前 `workflow_doctor.py plan <pack> --for-execution` 必须通过

#### 3. 复杂实现需要外部参考

用 [story-reference-impl](../../../.agents/skills/story-reference-impl/SKILL.md)。

适用场景：
- 技术实现复杂，需要参考 GitHub / 开源项目 / 框架官方文档
- 想先研究、再适配、最后实现

它的链路是：研究参考实现 -> DDD 适配设计 -> 分层实现 -> Review。
可作为 vj-epic-plan 前置研究，或在 vj-work 执行遇到复杂 Unit 时单独调用。

### 阶段 C：实现完成后的收口

`vj-work` 自身已包含 Unit Verification 与 risk-based review gate。在此之外按需继续：

1. [vj-test](../../../.agents/skills/vj-test/SKILL.md) — epic 级跨层 E2E（断言 DB/API/前端真实状态 + 变异自检）
2. [story-verify-fix](../../../.agents/skills/story-verify-fix/SKILL.md) — 启动前后端做联调验证与视觉对齐
3. [review](../../../.agents/skills/review/SKILL.md) — 结构化 pre-landing 审查，基于 `docs/reference/guides/review-checklist-python-fastapi.md`
4. [diff-aware-qa](../../../.agents/skills/diff-aware-qa/SKILL.md) — 第二层回归 QA，关注"这次 diff 还波及了哪些页面 / 路由 / 接口"
5. [vj-compound](../../../.agents/skills/vj-compound/SKILL.md) — 踩了坑或定了非平凡决策后沉淀到 `docs/solutions/`

## 3. 什么时候用 api-design 和 data-model

这两个 skill 都不是默认前置步骤。

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

- AI 不能说"实现违反了这些文档"
- 只能判断"本次改动是否引入了新的 contract / schema delta，需要补说明"
- 命中 delta 时同步创建或更新模块文档；旧 `api_spec.md` / `database_schema.md` 仅作为兼容读取 fallback

始终可校验的是：
- repo 硬约束
- Story 验收标准
- 现有代码模式

## 4. Plan 应该怎么用

Plan 以 **Epic 为单位**，由 `vj-epic-plan` 生成，落在
`docs/work/plans/{date}-epic-{N}-{slug}/`（review pack 目录）：

- `README.md` — reviewer 入口：一屏摘要、Known Conflicts、阅读路径、execution sketch、catalog sync 状态
- `design.md` — human 技术设计主文档（问题建模、架构、delta 摘要、理由、跨层不变量和风险；不复制精确 schema）
- `decisions.md` — 设计取舍、证据状态与 AC 偏离的唯一真相源（D/ACD）
- `docs/work/tasks/epic-{N}-{slug}/` — task packets（`task-index.md` + 每 task 一份执行文档），给 `vj-work` 直接消费

信息按维度只有一个来源：Story AC 定义可观察行为；approved decisions 定义取舍；
`docs/project/api|data|ui/` 定义精确合同；`design.md` 定义 delta 理由与不变量；task docs 是执行投影。
跨维度冲突必须停止并修正来源，不能靠文档优先级静默覆盖。

Plan status：`research-ready` 只允许执行 `research-only` 证据 task；证据完成后回到
`awaiting-approval`。只有 blocking 决策全部批准并通过 doctor，才能进入 `ready` 和生产实现。

### Execution Policy: fast | strict

执行策略按风险触发器判定，不再使用旧的 Flow A/B/C 标签。命中任一项即 strict：

- 改 DB migration / schema / 数据回填
- 改公共 API contract / DTO envelope / 错误码
- 改权限 / 认证 / 安全 / ownership / tenant 边界
- 引入外部系统或异步任务
- 复杂状态机 / 幂等 / 事务一致性
- 需求不清楚（一处歧义会改变行为）
- 影响多个 bounded context
- UI shell / navigation / design token 级变更
- 预计大 diff（跨子系统 ≥400 行或总计 ≥1000 行）

fast 覆盖其余普通任务（CRUD、DTO、字段映射、局部 UI data binding、文案样式）。
strict 意味着审批门、逐 task 记录与提交、完整 review / trace。

### Delta 同步

- **API Contract Delta**：改接口时在 plan 阶段写清，并同步 `docs/project/api/{module}.md`；全局约定变化才改 `docs/project/api/conventions.md`
- **Schema / Migration Delta**：改表结构时写清，并同步 `docs/project/data/{module}.md` 与 `docs/project/data/overview.md`
- **UI Surface Delta**：新增/更新 Screen 时写清，并同步 `docs/project/ui/surfaces.md` / `routes.md`

plan 阶段新增的 catalog 条目标 `planned (Epic N)`：它是该 plan 的精确拟议合同，不是已实现事实。
只有 vj-work 的 Unit verification、全量 review 和合同比对全部通过后才翻为 `active`；其他 Epic
默认只能把 active 条目当可消费的现状。

## 5. 前端设计怎么接入

前端设计生产端拆进主链路，并分成两条轨道。这里的原则是：**Screen Contract 完整度强制，ui-* skill 调用按缺口强制触发**。不要为了形式固定跑满所有 UI skill；也不能在字段缺失时跳过或自由发挥。

### 5.1 产品/品牌方向轨（低频）

当项目缺 `docs/project/DESIGN.md`、`DESIGN.md` 明显过期、品牌感不清、登录/落地/首个空态没有 golden screen，或用户明确要求"整体 UI 更好看 / 更有品牌感"时，必须先补产品/品牌方向：

```text
产品级 ui-requirement-brief
-> vj-design-md-matcher
-> docs/project/DESIGN.md
-> docs/reference/research/designs/golden/
```

这一轨解决"这个产品应该长什么样"：品牌气质、颜色/字体/间距/圆角/阴影、屏型富度地板、Reference Skeletons、front-of-house 的品牌表达和 golden screens。它不是每个 Story 都跑，也不在 `vj-work` 执行期临时跑。

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
| PRD 已定稿但整体产品长相没对齐过 | `vj-mock-board`（PRD → 单文件 mock board） |
| 单屏目标、模块顺序、信息层级不清 | `ui-page-goal-structure` |
| loading / empty / error / disabled / permission 等状态不清 | `ui-state-coverage` |
| 复杂操作流不清 | `ui-user-journey-audit` |
| UI 截图完成后视觉不稳定或 UI-critical 屏验收 | `ui-visual-consistency-audit` |
| 可复用组件需要沉淀规格 | `ui-component-spec-audit` |
| 交付研发/QA 前规格不完整 | `ui-handoff-readiness-check` |

复杂操作流不按页面名称枚举，按流程特征判定（多步、权限/资格判断、不可撤销动作、
恢复路径、改变业务状态——完整判定条目见
`.agents/skills/_shared/ui-planning-contract.md` §3，那是唯一真相源）。命中任一项，
就必须补 `ui-user-journey-audit`。

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

`vj-work` 执行 UI task 时对设计图的**发现**顺序：

1. task packet / Story 文件里的设计参考（`参考:` 行或 `### 设计参考` 表格）
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

如果自动发现失败，但你又要求"按设计稿还原"，那就需要手动给路径或 URL，不要让 AI 猜。

即使没有外部设计图，前端 Story 也不能退化成 AC 最小实现：

- 屏型（front-of-house / operational）的必写项与禁止项以 `.agents/skills/_shared/ui-planning-contract.md` §1/§4 为唯一真相源；实现期出口闸以 `.claude/rules/frontend.md` 为准。
- 如果 `DESIGN.md` 或 golden screen 缺失，不能指望 `ui-page-goal-structure` / `ui-state-coverage` 让 UI 自动变好看；它们只补单屏体验合同。先补产品/品牌方向轨，再进单屏实现。
- `vj-work` 完成 UI-critical 屏前必须保留桌面 + 移动截图，并由非实现者或 `ui-visual-consistency-audit` 做 pass/fail。

## 6. 多窗口 / 并行开发怎么做

并行执行的第一选择是 `vj-work` 自身的 Task DAG / 波次编排（serial-isolation / parallel-isolation）。
在此之外多人或多窗口同时工作时，优先用以下方式降低冲突：

- 在 plan 的 task-index 中明确文件所有权、依赖关系和阻塞点
- 用 Git 分支或 worktree 隔离并行实现
- 对会互相影响的 DB migration、公共接口、共享组件提前串行化
- 在执行日志或 PR 描述里记录 Story 的 `done / blocked / risk` 状态

## 7. 几条典型工作流

### 场景 1：已有项目加一个功能

```text
vj-feature（澄清 + 生成 Epic/Story）
-> vj-epic-plan（review pack + task packets）
-> vj-work（执行）
-> vj-test / diff-aware-qa（按需）
```

### 场景 2：普通后端 Epic

```text
已有 Epic/Story
-> vj-epic-plan
   -> 如改接口：命中 API delta，plan 阶段同步 docs/project/api/
   -> 如改 migration：命中 data delta，plan 阶段同步 docs/project/data/
-> vj-work（auto：普通 CRUD 走 fast，迁移/权限自动升 strict）
-> review（strict 下已内含；fast 下按需）
```

### 场景 3：复杂实现，参考开源

```text
已有 Epic/Story
-> story-reference-impl（研究参考实现 -> DDD 适配设计）
-> vj-epic-plan 吸收研究结论出计划
-> vj-work 执行
-> story-verify-fix -> review
```

### 场景 4：前后端联调 Epic，且有设计稿

```text
已有 Epic/Story（页面体验地图完整）
-> vj-epic-plan（Screen Contract + Frontend composition waves）
-> vj-work
   -> contract wave 稳定 API-for-UI
   -> backend capability waves
   -> frontend composition waves（按 Screen 整体实现 + 截图 gate）
   -> E2E polish（cross-screen visual polish pass）
-> vj-test（跨层 E2E + 前端截图证据）
-> diff-aware-qa
```

## 8. 当前仓库的现实约束

这几点必须记住：

- 当前仓库包含可编辑的 `frontend/src/`，前端实现按 `AGENTS.md` 的 React + TypeScript + Vite + Tailwind + shadcn 约束执行。
- 需要真实前端代码改动时，先确认目标 Route / Screen Contract / 设计来源是否齐备。
- `story-verify-fix` 可以做运行时验证和视觉检查，但不替代缺失的前端源码。

## 9. 一句话决策表

| 你现在手上的任务 | 用什么 |
|------------------|--------|
| 已有项目加一个功能 | `vj-feature` |
| 只有产品想法，还没拆 Story | `vj-product-requirements -> vj-architecture -> vj-epic-story` |
| PRD 定稿了，想先看产品长什么样 | `vj-mock-board`（缺 `DESIGN.md` 先走 `vj-design-md-matcher`） |
| 项目整体缺品牌/视觉方向，或登录/落地页缺 golden | 产品级 `ui-requirement-brief -> vj-design-md-matcher` |
| 已有 Epic/Story，要出实现计划 | `vj-epic-plan`（自动触发 `vj-plan-review`） |
| 已有 plan，要落地实现 | `vj-work` |
| 复杂实现，需要参考开源 | `story-reference-impl` |
| 实现完成后跑 epic 级 E2E | `vj-test` |
| 实现完成后联调 / 视觉对齐验证 | `story-verify-fix` |
| 做代码审查 | `review` |
| 查本次 diff 的回归风险 | `diff-aware-qa` |
| 沉淀踩坑 / 决策 | `vj-compound` |

## 10. 推荐默认顺序

如果你不想每次都重新判断，就按这个默认顺序走：

```text
需求未成型:
  vj-product-requirements
  -> vj-architecture
  -> vj-epic-story

已有项目加功能:
  vj-feature

计划与执行:
  vj-epic-plan（自动 vj-plan-review）
  -> vj-work

实现后（按需）:
  vj-test
  -> story-verify-fix
  -> review
  -> diff-aware-qa
  -> vj-compound
```

这就是当前仓库推荐遵循的 AI 工作流。
