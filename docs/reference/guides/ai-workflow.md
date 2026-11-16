# AI Workflow

这份文档定义当前仓库推荐的 AI 开发工作流，回答三个问题：现在该用哪个 skill；什么时候要出计划、
补接口 / 数据说明；一个需求从想法到收口的完整链路是什么。

## 1. 默认入口与三条交付轨

```text
vj router
  Patch -> 复现/断言 -> 窄改动 -> 定向验证 -> 按风险 review
  Story -> 回复里写几行意图 -> 实现/验证 -> 按风险 review
  Plan  -> vj-plan（一份计划文档，整份给人审）-> vj-work（读代码、验收变测试、按执行顺序做完）-> E2E/review/QA（按风险）
```

默认先用 `vj` 选最小可靠的交付轨。Patch 和 Story 不建文档；多个能力、跨 bounded context、命中
`AGENTS.md` strict 触发条件，或要做 PRD 里的一个 Epic 时走 Plan。

所有轨开工前在回复里用几行说清意图（目标 / 非目标 / 怎样算做完）和执行方式（轨道 / 改哪里 / 怎么验证 /
是否 commit）。用户明确"不要 commit"时任何轨都不得创建 commit。

## 2. 从想法到上线

### 还只有产品想法

```text
vj-product-requirements（采访 → 方向原型 → PRD）
-> vj-architecture（按需）
-> vj-plan（整份 PRD → 每块一份计划）
-> vj-work
```

PRD 是产品层面的事，想清楚一次；它的 §4 分好了 Epic，§11 排好了顺序，就是路线图。把整份 PRD 交给
`vj-plan`，它先出一份**拆分总览**（几份、谁等谁、共享的表和服务谁落地、每条决定归哪份），再**按 Epic 拆成
多份计划、一次全部写完**；Epic 有两组互不相干的能力或验收会超过约 40 项就再拆成几份。计划不写改哪些文件，
所以不用等前置计划做完再补；`after:` 只表示先后。

PRD 定稿后想先看整个产品长什么样，可以插一步 `vj-mock-board`（缺 `DESIGN.md` 时它会先走 §5.1 的方向轨）。

### 已有项目加一个功能

直接用 `vj-plan`，输入是一句功能描述；它会问清谁用、什么场景、做什么、不做什么，再出计划。
功能会改变 PRD 的押注或非目标时，先用 `vj-product-requirements` 的 update 模式改 PRD。

### 计划长什么样

`vj-plan` 产出一个文件 `docs/work/plans/{date}-{slug}.md`：

| 部分 | 格式 | 内容 |
|------|------|------|
| 做什么、为什么 | 自由 | 一个使用场景讲清要解决什么、做完什么样、不做什么 |
| 方案总览 | 默认章节 | 一句话方案 + 总体思路；改动现有系统时附改造前后对比 |
| 关键设计 | 默认章节，小节自由起 | 数据怎么存、状态怎么变、主流程（按需配实体关系图 / 状态图 / 时序图）、页面怎么交互（主流程 / 备选 / 出错） |
| 改到哪些已有东西、风险和回滚 | 改动现有系统时必写 | 要变的旧假设和处理、副作用、回滚和不可逆的部分 |
| 要你拍板的决定 | 固定表格 | 每条：问题、不定会怎样、推荐、挡哪一步；状态 待你定 / 待证据 / 上线前定 / 已定 |
| 验收清单 | 固定表格 | 每个场景要保证什么、自动测试 / 浏览器 / 人工 |
| 执行顺序 | 固定编号列表 | 先做什么、哪些能并行、哪一步等哪个决定 |
| 验收对应的测试、执行记录、验收说明 | `vj-work` 追加 | 开工时把验收项对应到测试；子任务进度；做完后怎么试、要你亲手试的项、没做的部分 |

计划写完后调 `prd-to-bdd`，以 PRD 加这份计划为输入生成中文用例表和待激活的 feature（`AutoTest/modules/`），
人把关看用例表；`plan_case_trace.py` 核对每条验收都进了用例。验收清单写一次用三次：开工前人审；写代码时 AI 先把它变成测试；做完后自动项由 AI 跑，
人工项交给人亲手试。还没定、只能靠真实测试回答的事（如"AI 能不能听懂口语"）写成执行顺序里的证据步骤，
决定只挡它写明的那一步，其余照常做。

交付前过 `plan_lint.py`（固定三节、决定状态和挡哪一步、验收格式、前置计划）。单份 `policy: strict` 时派独立审查；
整份 PRD 拆成多份时只审一次，看跨计划冲突。

### 执行

`vj-work` 开工时一次问完挡路的决定，起好运行环境并跑一遍基线，读真实代码，把验收项对应到测试（计划末尾"验收对应的测试"，
过 `plan_lint.py --for-execution`）。然后按执行顺序的切片派子任务：一个切片一个干净会话的子代理，交代里附上前面切片的产出和
写成明确句子的硬要求，先写测试、看到它失败再实现，回来交"给下一个切片的交接"；子代理说做完不算，它自己重跑检查命令，
通过才记进执行记录。加迁移或改同一个注册文件的切片串行，其余并行；有接口约定时先落接口数据结构，前端用模拟数据和后端并行。
前端切片开工前先拿用例表对一遍交互，页面做出来就按 `prd-to-bdd` 的激活流程激活它的用例并用 `run-test` 真跑，测试自身的问题交给
`test-self-heal`。收尾跑全量回归和 review，把数据 / 接口 / 页面的现状更新到 `docs/project/`，在计划末尾写验收说明，
其中带一张针对这次改动的发布前清单（机器能查的先跑掉，剩下 5–10 项由人签字）。

### 收口（按需）

1. [vj-test](../../../.agents/skills/vj-test/SKILL.md) — 跨任务的端到端测试（断言 DB / API / 前端真实状态 + 变异自检）
2. [story-verify-fix](../../../.agents/skills/story-verify-fix/SKILL.md) — 启动前后端做联调验证与视觉对齐
3. [review](../../../.agents/skills/review/SKILL.md) — 结构化 pre-landing 审查
4. [diff-aware-qa](../../../.agents/skills/diff-aware-qa/SKILL.md) — 这次改动还波及了哪些页面 / 路由 / 接口
5. [vj-compound](../../../.agents/skills/vj-compound/SKILL.md) — 踩了坑或定了非平凡决策后沉淀到 `docs/solutions/`

复杂实现需要参考开源项目时，在出计划前或执行中用
[story-reference-impl](../../../.agents/skills/story-reference-impl/SKILL.md)：研究参考实现 → DDD 适配设计 → 分层实现。

## 3. api-design 和 data-model 什么时候用

都不是默认前置步骤。计划的关键设计里写清这次的接口 / 数据变化；`vj-work` 做完后把现状更新到
`docs/project/api/{module}.md`、`docs/project/data/{module}.md`。需要单独写一份完整的接口或数据说明时才用：

- `api-design`：新增 / 删除端点，请求 / 响应 schema、错误码、分页、过滤、鉴权、幂等契约变化；
- `data-model`：新增表、字段、索引、约束、migration，事务 / 一致性 / 状态流转相关的持久化变化。

对应模块文档不存在时，AI 不能说"实现违反了这些文档"，只能判断这次改动有没有引入需要补说明的变化。
始终可校验的是：repo 硬约束、计划的验收清单、现有代码模式。

## 4. fast 和 strict

计划 frontmatter 的 `policy` 按风险判定，命中任一 strict 触发条件即 strict（触发条件只在 `AGENTS.md`
「Plan 规范」维护）。fast 覆盖普通任务（CRUD、字段映射、局部 UI data binding、文案样式）。
strict 多两件事：出计划后派独立审查；`vj-work` 收尾一律跑完整 review。

## 5. 前端设计怎么接入

原则：**页面字段写完整是强制的，ui-* skill 按缺口调用**。不为形式跑满所有 UI skill，也不在字段缺失时自由发挥。

### 5.1 产品 / 品牌方向轨（低频）

项目缺 `docs/project/DESIGN.md`、它明显过期、品牌感不清、登录 / 落地 / 首个空态没有 golden screen，
或用户明确要"整体更好看、更有品牌感"时，先补方向：

```text
产品级 ui-requirement-brief -> vj-design-md-matcher -> docs/project/DESIGN.md + docs/reference/research/designs/golden/
```

这一轨回答"这个产品应该长什么样"，不在每个计划里跑，也不在 `vj-work` 执行期临时跑。

### 5.2 单屏体验轨（按缺口）

计划里页面只用大白话写交互：从哪进、主流程、备选、出错路径、要覆盖的状态（规则在 `vj-plan/SKILL.md`「页面怎么交互」）。
计划阶段不强制跑下面的 skill；需要更细的设计时按缺口选用：

| 缺口 | 补齐方式 |
|------|----------|
| 产品 / 品牌方向、登录 / 落地页 golden 缺失 | 产品级 `ui-requirement-brief -> vj-design-md-matcher` |
| PRD 已定稿但整体长相没对齐过 | `vj-mock-board` |
| 单屏目标、模块顺序、信息层级不清 | `ui-page-goal-structure` |
| loading / empty / error / disabled / permission 等状态不清 | `ui-state-coverage` |
| 复杂操作流需要更细的旅程审查 | `ui-user-journey-audit` |
| 截图完成后视觉不稳定 | `ui-visual-consistency-audit` |
| 可复用组件需要沉淀规格 | `ui-component-spec-audit` |
| 交付研发 / QA 前规格不完整 | `ui-handoff-readiness-check` |

### 5.3 稳定合同

- `docs/project/DESIGN.md`：视觉与品牌合同（token、屏型富度地板、Reference Skeletons、Do / Don't）。
- `docs/reference/research/designs/golden/`：屏型金标准。
- `docs/project/ui/surfaces.md` / `routes.md`：已经做出来的页面和路由，`vj-work` 做完计划后更新。
- `vj-work` 读 `DESIGN.md + golden + docs/project/ui/` 实现整屏，截图后由非实现者判 pass / fail；
  实现期出口闸以 `.claude/rules/frontend.md` 为准，参考图和多屏一致性见 `vj-work/references/ui-execution.md`。

设计稿放 `docs/reference/research/designs/{计划 slug}/{页面}.png`（状态变体加 `-empty`、`-mobile` 后缀），
在计划的关键设计里引用。自动找不到又要求"按设计稿还原"时，手动给路径，不要让 AI 猜。

## 6. 多窗口 / 并行开发

并行的第一选择是 `vj-work` 自己的并行（没依赖、不改同一文件的子任务各开 worktree）。多人或多窗口同时工作时：
按计划的执行顺序分工，开工前各自在执行记录里写清要改哪些文件；用分支或 worktree 隔离；会互相影响的 migration、
公共接口、共享组件提前串行。

## 7. 当前仓库的现实约束

- `frontend/src/` 可编辑，前端实现按 `AGENTS.md` 的 React + TypeScript + Vite + Tailwind + shadcn 约束执行。
- 需要真实前端改动时，先确认计划里的页面入口、交互路径和设计来源齐备。
- `story-verify-fix` 做运行时验证和视觉检查，不替代缺失的前端源码。

## 8. 一句话决策表

| 你现在手上的任务 | 用什么 |
|------------------|--------|
| 一两个文件的小改动 | `vj`（Patch / Story 轨，直接改） |
| 已有项目加一个功能 | `vj-plan` → `vj-work` |
| 只有产品想法 | `vj-product-requirements` → `vj-plan`（一次一个 Epic） |
| PRD 定稿了，想先看产品长什么样 | `vj-mock-board`（缺 `DESIGN.md` 先走 `vj-design-md-matcher`） |
| 项目整体缺品牌 / 视觉方向 | 产品级 `ui-requirement-brief -> vj-design-md-matcher` |
| 复杂实现，需要参考开源 | `story-reference-impl` |
| 做完后跑端到端测试 | `vj-test` |
| 做完后联调 / 视觉对齐验证 | `story-verify-fix` |
| 代码审查 / 查回归风险 | `review` / `diff-aware-qa` |
| 沉淀踩坑 / 决策 | `vj-compound` |
