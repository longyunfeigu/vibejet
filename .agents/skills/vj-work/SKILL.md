---
name: vj-work
description: 消费 vj-epic-plan 产出的 epic 实现计划并落地。默认用 auto 模式：普通任务走 fast execution（最小上下文、worktree 隔离、Verification 驱动、最终记录），高风险任务自动切 strict execution（审批、逐 Unit 记录、严格 QA、review、审计留痕）。用户说"执行这个 plan""做 epic X""跑实现""把计划落地""vj-work"时使用。在 vj-epic-plan 之后使用。
---

# vj-work — Epic 执行器 v2

把 `vj-epic-plan` 产出的 epic 实现计划落地成"已实现、已验证、已记录"的代码。

工作流位置：

```text
vj-epic-story (WHAT) -> vj-epic-plan (HOW) -> vj-work (执行) -> vj-compound (可选沉淀)
```

v2 的核心变化：默认不再把所有任务都当成严格审计型交付来跑。普通任务走 fast path，减少重复上下文和文档流水账；高风险任务走 strict path，保留旧版的审批、逐 Unit 提交、完整 UI QA、review 和 traceability。

## 第一性原理

AI coding 质量主要来自四件事：

1. **清楚的任务规格**：当前 Unit 要交付什么、不要做什么。
2. **相关约束足够近**：只把当前 Unit 需要的架构、设计、契约约束放进执行上下文。
3. **真实反馈回路**：以 Unit 的 `Verification` 命令作为 done signal，失败就修，不靠自评。
4. **风险正确升级**：权限、迁移、公共 API、事务、UI 壳等高风险面切 strict，不用 fast path 蒙混。
5. **UI 按体验闭环交付**：后端/API/data 可以按 capability Unit 推进；前端质量来自 Screen/Route 的完整任务上下文、稳定 API-for-UI 合同和浏览器截图反馈，不能按 Story 验收项碎片化堆 UI。
6. **Orchestrator 上下文卫生**：主 session 是编排者，不是执行者。单个 Unit 的重活（读 20+ 文件、写代码、跑测试/迁移、浏览器验证）会吞掉大量上下文——这些必须下沉到 subagent，主 session 只接收结构化小结。Unit 越多，主 session 越要保持轻，否则审计/编排能力会随 epic 规模塌掉。

因此 v2 的目标不是少读上下文，而是少读无关和重复上下文；不是少验证，而是把验证集中到真实 done signal；不是取消审计，而是让审计按风险触发；不是 orchestrator 亲自干所有活，而是把执行下沉给隔离的 subagent、主 session 只编排与审计。

## 铁律

- **Review pack 是决策依据，不是执行脚本**。Task packets（`task-index.md` + `T{NNN}.md`）是默认执行入口；review pack 的 `design.md` / `decisions.md` 只在 task anchors、strict trigger、歧义或冲突时按章节回读。HOW 的具体代码由执行期读现有实现后决定。
- **不改 review pack 正文**（README / design / decisions）。唯一允许的改动是收尾时把 `README.md` frontmatter `status: active -> completed`。计划级修正回 `vj-epic-plan` / `vj-plan-review`。
- **Verification 是 done signal**。每个 Unit 的 `Verification` 字段必须实际跑通；未跑通不得标 completed。
- **worktree 隔离**。本 skill 改代码一律从当前 `HEAD` 创建执行 worktree / 执行分支，不在当前主仓库工作树直接堆代码改动。
- **当前非默认分支就是 integration base**。开工只读当前分支名与工作区状态；不得通过 `git log` / `git show` / reflog 翻 commit 历史来推断 base，也不得在非默认分支上询问"是否基于当前分支开 worktree"。只有默认分支或未提交改动歧义才停下问人。
- **上下文必须可回溯**。Execution Checklist 是 attention guide，不是完整规范；每条约束必须带 source pointer。`DESIGN.md`、`docs/project/api/`、`docs/project/data/`、`docs/project/ui/`、repo-local layer skill 原文仍是真相源。
- **Backend by capability, frontend by experience**。前端 Epic 执行时必须消费 task docs / `_execution_context.md` 中的 Screen context，以及 `docs/project/ui/` catalog（必要时按 task anchors 回看 `design.md` UI Surface Delta 与 `task-index.md` lanes）：先稳定对应 Screen 的 API / 状态 / 数据合同，再按 Screen/Route 整体实现 UI。不要等所有后端 100% 完成才开始前端，也不要把前端散进每个 Story 局部做。
- **禁止孤立 UI 片段**。UI Unit / task 若属于 Screen composition，必须读同屏 sibling Units、Route 目标文件、Screen regions、API-for-UI 与 Screen done；不得为了当前 Unit 新增脱离 Screen Contract 的单页、卡片堆、表单堆或按钮堆。
- **前端质量 = 富度（防空）+ 工艺（防挤）+ 屏型对的闸**。UI Unit 执行须守 `.claude/rules/frontend.md` 的富度铁律（R0–R4：先分屏型、按页面体验地图建整屏、不空屏、走参考、不堆孤卡）与工艺铁律（C1–C5：间距分层、字重色阶层次、边框/accent 克制）；间距数值以 `DESIGN.md` §Spacing Hierarchy 为准。**admin/后台屏几乎都是 operational**：不调 `design-taste-frontend`（对后台 out-of-scope），craft 真相源 = `frontend-dev-guidelines/resources/dense-ui-craft.md`，出口走 frontend.md B 轨客观硬线。规则条目以 frontend.md 为唯一真相源，本 skill 不复述。
- **UI-critical 屏的出口闸判定独立于实现，且 orchestrator commit 前必须真看截图**。每个 UI-critical / operational screen 标 done / commit 前：(1) 必须有真实桌面截图；(2) B 轨 pass/fail 由**非实现该屏的一方**产出——orchestrator 亲自看截图，或派独立 visual-audit subagent（输入仅截图 + 该屏 frontend.md B 轨 checklist + 一张同类密集后台参考；**不给实现代码、不给实现 subagent 的小结**），返回带**截图实测**占比（首屏最大空容器高度占比、页框 padding、最小区块 gap）的 pass/fail；(3) 第一性原理 6「orchestrator 只 ingest 小结、不读 transcript」**不豁免看 UI 截图**——截图是轻量 artifact，UI-critical 屏严禁仅凭实现 subagent 的文字小结就 commit。自评 "passes" 不构成过闸。该屏存在已批准参考图（参考图前置闸产物或屏型金标准）时，审计输入必须升级为「实现截图 ↔ 参考图并排对照」，偏差清单按"参考图里有而实现里没有/走样"逐项列——审计从主观判美丑降级为客观找图差。这把独立判定从 Phase 3 末的 cross-screen polish 提前到每屏 done（翻车实证见 memory `frontend-taste-gate-not-checklist`：规则本就精确，洞在自评 + 没人看像素）。
- **subagent 任务必须自包含**。不得依赖父 agent Phase 0/1 的隐式上下文。即使运行时支持 `fork_context` / isolation，也必须显式传 Unit/Task Context Packet 或 `_execution_context.md` 路径 + Unit ID / Task ID。
- **高风险自动 strict**。命中 strict trigger 时不得为了速度降级；不确定风险等级时按 strict 或精准补读 source pointer。
- **KISS / YAGNI**。只实现 Unit 要求，匹配既有约定，不引入投机抽象或无关重构。
- **执行 plan 的复用 / 高风险流程 / fallback 约束**。`Patterns` / `Approach` / `Execution note` 里声明的复用对象、业务流程图 / 伪代码、不变量、禁止 fallback/mock/简化实现，都是执行合同。执行期若发现必须重写已有权威实现、绕开高风险流程，或用替代逻辑伪造业务真相，不得自行改口径；切 strict 或 STOP。
- **完成整个 feature**。不留 80% 半成品；blocked 必须说明阻塞点、已试方案、下游影响。

## 输入

```text
vj-work docs/tasks/plans/2026-06-01-epic-1-.../   # review pack 目录
vj-work epic-1
vj-work
```

未指定时取 `docs/tasks/plans/` 下最新 review pack 目录（含 `README.md` + `design.md` + `decisions.md`）。

## 配置

```yaml
epic_work_executor:
  plans_dir: docs/tasks/plans/
  work_dir: docs/tasks/work/epic-{N}-{slug}/
  worktree_root: .vj/worktrees/
  runtime_adapter: auto                 # inline | claude-agent | codex-subagent | auto
  execution_mode: auto                  # auto | fast | strict
  approval_gate: auto                   # auto | true | false
  recording: auto                       # auto | final-only | per-task
  commit_granularity: auto              # auto | feature | wave | per-task
  learnings_skill: vj-compound          # optional post-run prompt
```

### Mode 定义

| Mode | 目标 | 默认行为 |
|------|------|----------|
| `fast` | 普通 AI coding 吞吐 | 最小 Unit/Task Context Packet、final-only 记录、feature/wave commit、risk-based QA/review |
| `strict` | 高风险交付审计 | 审批门、逐 Unit 文档/ledger、逐 Unit commit、完整 UI QA、完整 review/trace |
| `auto` | 默认 | 先按 strict triggers 判定；命中即 strict，否则 fast |

### Strict Triggers

> 本清单细化自 AGENTS.md「Plan 规范」的 strict 触发条件（vj-epic-plan Phase 3 同源）；两处冲突以 AGENTS.md 为准。

命中任一项即 strict：

- auth / session / permission / role / ownership / tenant boundary。
- database schema / migration / data backfill / destructive update。
- public API contract / DTO envelope / error code / backwards compatibility。
- payment / billing / crypto / secrets / token / security-sensitive dependency。
- transaction / Unit of Work / idempotency / concurrency / domain event / Celery / external side effect。
- app shell / navigation / theme / DESIGN.md global token / UI architecture。
- expected diff >= 400 lines across multiple subsystems, or >= 1000 lines total。
- user explicitly asks strict / audit / approval / per-task commit / exhaustive review。
- execution context cannot cite required source pointers, or plan/task ambiguity could change behavior.
- 执行 Unit 看起来必须违背 plan/task 的显式约束：复用声明、高风险状态 / 权限 / 事务 / 判分 / AI 评估流程，或“禁止 fallback/mock/简化实现”。

非 strict trigger 的 CRUD、DTO、字段映射、局部 UI data binding、文案/样式修正默认 fast。

## Phase 0：定位 review pack 与 branch gate

1. 定位 review pack 目录：按输入解析；空参取最新。默认只读执行所需的最小面，不全文装载：
   - `README.md`：One-Screen Summary、Known Conflicts、Execution policy、Catalog Sync 状态。
   - `work_dir` 的 `task-index.md`：Required gates、Unit DAG、Task DAG / 波次、barrier / owner tasks、Execution lanes、共享文件冲突表——这是执行索引。
   - `design.md` / `decisions.md`：不默认全读；只有当前 task anchors、UI-critical、strict trigger、歧义或冲突要求时才读对应小节正文。稳定 Screen 合同以已同步的 `docs/project/ui/` catalog 为准，catalog 未同步时看 `design.md` UI Surface Delta。
   - 当前 task 的目标、文件、方法、验收以 `T{NNN}.md` 和 `_execution_context.md` 为入口；task packet 缺失或冲突时才回读 `design.md` / `decisions.md` 对应 anchors。
2. Branch / worktree gate：
   - 只运行 `git branch --show-current` 与 `git status --short`。
   - 当前分支不是 `main` / `master`：直接视为 integration base，不询问。
   - 当前分支是 `main` / `master`：STOP，确认是否仍以默认分支为 integration base。
   - 工作区干净：自动从当前 `HEAD` 创建执行 worktree。
   - 工作区有未提交改动：若只是本 skill 已生成的 task 文档 / `_ledger.md` / `_execution_context.md`，按记录策略处理；若包含用户已有代码改动或无法归类，STOP，说明新 worktree 不会包含这些改动，请用户选择 commit / stash / 仍以当前 `HEAD` 继续。
3. 不通过 commit 历史猜 base；不 checkout 当前主仓库到其他分支。

## Phase 1：装载 tasks，生成 Execution Context

执行产物目录：

```text
docs/tasks/work/epic-{N}-{slug}/
  task-index.md          # vj-epic-plan 生成：执行索引（DAG / gates / 冲突表）
  T{NNN}-{slug}.md       # vj-epic-plan 生成：task packets（纯投影，可整目录重写）
  verify.sh              # vj-epic-plan 生成：Unit verification 可执行入口
  _execution_context.md  # 本 skill 生成：执行缓存
  _ledger.md             # 本 skill 生成：执行账本（append-only）——task 状态、变更叙事、
                         # verification 结果、偏离记录都住这里，不回写 task 文档
```

### 1. 装载或回退生成 task 文档

默认路径：

- 装载前跑 `python3 .agents/skills/_shared/scripts/plan_lint.py <review-pack-dir>`；exit != 0 → STOP 回 `vj-epic-plan` 修正（lint 不可用时降级为人工核对 task-index 引用的 T 文档齐全）。
- 如果 `work_dir` 已有 `task-index.md` + `T{NNN}.md`：直接装载，不重新生成，不做过期校验。
- 如果缺失：按 `.agents/skills/vj-epic-plan/references/task-doc.template.md`（唯一副本）从 `design.md` / `decisions.md` / `task-index.md` 与 catalog 投影生成；不重新发明 HOW。回退生成后必须把生成来源和 anchors 写入 task doc。
- task 文档必须包含 `Generated from` / design+decision anchors / catalog anchors / write scope / read first / stop conditions。缺任一关键字段且不是 trivial task 时，STOP 回到 vj-epic-plan 修正或补投影，不要靠执行期自由发挥。
- `_ledger.md` 不存在则按 `references/ledger.template.md` 初始化（Status Board + append-only Entries；fast/strict 同 schema，只差写入时机）。

UI Unit fallback 注入规则保留：

- Files 含 `.tsx`，或路径含 `routes/` / `features/` / `components/` -> UI Unit。
- task 文档 Design context 只列 `DESIGN.md` 章节锚点 + 决定性原句；禁止有损摘要。
- task 文档 Screen context 必须投影自 `docs/project/ui/` catalog 或 `design.md` UI Surface Delta。若 UI task 找不到 Screen ID / Route / Primary Job / Covered Units / API-for-UI / Screen done，且不是 trivial UI，STOP 回到 plan 修正并同步 catalog；不要执行期自由设计。

### 2. 判定 execution mode

在 Phase 1 读取 `task-index.md`（Execution policy + Required gates）、所有 task packet 的 metadata（不要读全文实现段）、Affected Components、Verification、Execution note 后判定：

```text
if execution_mode == strict: strict
else if execution_mode == fast: fast unless hard strict trigger is hit
else auto: strict if any strict trigger hit, otherwise fast
```

把判定结果和原因写入 `_execution_context.md`。

### 3. Layer Skill Gate v2：一次加载，按 task / Unit 投递

旧规则"每个 Unit 开工前重复加载完整 layer skill"废弃。新规则：

1. Epic-level scan：
   - 从 task packets / `task-index.md` 收集路径：write scope、Affected Components、Implementation Plan、Test scenarios、Verification、实际执行中发现的目标文件。
   - `backend/` 或 backend pytest/alembic 命令 -> backend layer。
   - `frontend/` 或 frontend pnpm/vitest/browser 命令 -> frontend layer。
   - `.tsx`、routes、theme、layout、component、UI 状态 -> design layer。
   - `docs/project/api/`、OpenAPI、DTO、response envelope -> API contract layer。
   - `docs/project/data/`、models、migration、repository schema -> data layer。
   - `docs/project/ui/`、routes、surface catalog、UI state contract -> UI surface layer。
2. 每个命中的 repo-local skill 只做一次 Required First Read：
   - backend -> `.agents/skills/backend-dev-guidelines/SKILL.md` + 相关 source resources。
   - frontend -> `.agents/skills/frontend-dev-guidelines/SKILL.md` + 相关 source resources。
   - design -> `docs/project/DESIGN.md`，缺失才 fallback `docs/project/design_guidelines.md`；两者都缺失且 Unit 是 UI-critical 时 STOP。
   - API/data -> `docs/project/api/`、`docs/project/data/` 与现有实现。
   - UI surface -> `docs/project/ui/surfaces.md`、`docs/project/ui/routes.md`（存在时）与 task anchors 指向的 `design.md` UI Surface Delta / `task-index.md` lanes。
3. 按 `references/execution-context.template.md` 生成 `_execution_context.md`：
   - Epic Execution Checklist：10-20 条，本 epic 的高优先级硬约束。
   - Unit / Task Context Packet：每 task 一份最小自包含执行包，回指 parent Unit 与 Unit done 信号。

Checklist 要求：

- 每条必须具体、可执行、可验证。
- 每条必须带 source pointer，例如 `backend-dev-guidelines/resources/transaction-side-effects.md`、`docs/project/DESIGN.md:213`。
- 不追求完整规范；只列本 epic 容易写错且影响质量的约束。
- 无 source pointer 的泛泛规则不得进入 checklist。

Unit / Task Context Packet 固定字段：

```text
Unit:
  id / task path / wave / depends
Task scope: unit | partial-unit | screen-composition
Goal:
Acceptance / done signal:
Target files:
Pattern files: max 1-3
Relevant constraints: max 5-10, each with source pointer
Verification command:
Non-goals:
Risk class:
UI class: none | trivial | functional | critical
Execution lane: contract | backend-api-capability | frontend-composition | e2e-polish | legacy-unit
Screen context: none | Screen ID / route / screen type(front-of-house | operational | mixed) / primary job / role / covered sibling Units / regions / information priority / richness floor / forbidden patterns / key states / API-for-UI / Screen done / catalog source / app shell + 全局导航契约 (该屏套在哪个共享外壳/导航里；source: DESIGN.md §Layout / design_guidelines.md / 共享 layout 组件) / Reference image (已批准参考图路径；UI-critical 必填，继承屏型金标准时填 golden 路径)
Test policy: test-first | test-with-implementation | verification-only
System-wide check: none | direct-neighbors | risk-triggered-two-hop
```

如果 plan/task 明确禁止 fallback/mock/简化实现，或声明了必须复用的权威实现 / 官方 API / 标准协议，把该约束投影到 `Relevant constraints` 或 `Execution note`；不新增 Unit Packet 字段。判断依据：fallback 会不会在未知真实状态下继续做信任判断或写副作用。会则失败必须 fail closed / STOP / 返回明确错误；不会且只是展示增强、通知重试、只读缓存回源或 UI 局部错误态，可以按 plan 允许降级但不能伪装成功。

如果执行期发现实际目标文件、风险类型或契约变化超出 Unit Packet，精准打开对应 source pointer 或相关 resource；不得无差别全文重读。找不到可靠 source 时切 strict 或 STOP。
如果 task packet 与 Story AC / catalog / review pack anchors 冲突，按优先级处理：Story AC / 用户决策 > catalog > `decisions.md` approved decisions / `design.md` > task packet projection > current code pattern。不要只改 task packet 偷偷改变语义。

## Phase 2：波次计划与审批策略

波次计划直接消费 `task-index.md` 的 Task DAG / 波次表，不重算。task-index 缺 Task DAG 时才按 Files + Depends 回退补算一次。

前端 Epic 的 `task-index.md` 若包含 `Execution lanes` / `Frontend composition waves`：

- 先执行 UI surface / API contract 可见性检查：确认 `_execution_context.md` 已写入每个 Screen 的合同摘要，并带 `docs/project/ui/` catalog source 或 `design.md` UI Surface Delta source。
- backend/API/data capability wave 按 task 执行，目标是让对应 Screen 的数据、状态、错误、权限、mock/real adapter 合同稳定；Unit 收口仍在所有相关 task 完成后验证。
- frontend composition wave 按 Screen/Route 执行；同一 Screen 覆盖多个 Unit 时，以 Screen done + 关联 UI AC 作为该 wave 的 done signal。**每个 Screen 额外必过 `.claude/rules/frontend.md`「出口闸：品味」对应轨——与功能 AC 同等牙齿，不过不得标该 Screen done**：front-of-house 走 A 轨（A1–A3），operational 走 B 轨（B1–B5，内含工艺线 C1–C5）。变更叙事须按闸门要求列出实际组件 / `data-testid` / 间距实测值与参考对照结论，不接受无对照的主观 "passes"。**且该 pass/fail 判定必须由非实现者产出（orchestrator 看截图或独立 auditor），实现 subagent 自写的 "passes" 不算过闸**。闸门条目内容以 frontend.md 为唯一真相源，本 skill 不复述。
- E2E polish wave 在所有相关 Screen composition 通过后执行：先做 cross-screen visual polish pass（见 Phase 3），再跑完整演示脚本、截图、异常状态与全量验证。
- 如果 task-index 没有 lanes，但发现多个 UI Unit 共享同一路由，切到 `frontend-composition fallback`：先生成临时 Screen 分组写入 `_execution_context.md`，按 Screen 串行执行，避免并行写坏 UI。

Approval gate：

- `approval_gate: true`：总是 STOP，展示 task docs + waves + mode decision，批准后继续。
- `approval_gate: false`：不审批，除非 hard strict trigger 要求用户决策。
- `approval_gate: auto`：
  - fast：输出短执行摘要后继续。
  - strict：STOP，展示 task docs + waves + strict reason，批准后继续。

Docs planning commit：

- fast：不要求审批，但必须保证执行 worktree / subagent 能看到任务上下文。若 task docs / `_ledger.md` / `_execution_context.md` 尚未提交，且执行会依赖这些路径，自动创建一个 docs-context commit（不问人）后再开 worktree；若不提交，则必须把完整 Unit/Task Context Packet 字面量传给执行者，不能只给不可见路径。最终变更叙事和 execution profile 仍可收尾统一提交。
- strict：保留旧规则，动代码前提交 task docs + `_ledger.md` + `_execution_context.md`。

## Phase 3：执行

### 执行策略

始终使用 worktree 写代码，绝不在主仓库工作树直接写业务代码。

**默认：每个 task 派一个自包含 subagent（Task 工具）执行，用于上下文隔离。** Unit 仍是验收边界，task 是执行边界。动机首先是 orchestrator 上下文卫生（第一性原理 6），其次才是并行。重活——读 20+ 文件、写代码、跑测试/迁移、浏览器验证——都留在子代理上下文里；orchestrator 只接收子代理返回的结构化小结（changed files / verification 结果 / deviations / risks），**绝不 Read 子代理的 transcript/.output**（会撑爆主上下文）。这样 orchestrator 上下文随 task 数线性缓增（只长“小结 + review”），不因 epic 规模塌掉。

两种派发模式：

| 模式 | 何时用 | worktree |
|------|--------|----------|
| **serial-isolation（默认）** | task 间有依赖 / 共享文件 / owner task（绝大多数 epic 的 barrier 与集成阶段） | **共享同一个执行 worktree**，按 Task DAG 依赖顺序串行派发；上游 task 完成后再派依赖它的 task，下游读已落盘状态 |
| **parallel-isolation** | 同波次 ≥2 个 task、写集无交集、无逻辑依赖、contracts 已稳定、task 足够大、运行时允许 | 各 task 用独立 worktree（Task `isolation: worktree`），完成后按 Task DAG merge |

> 关键：依赖型 / 共享文件 / owner task **必须共享同一执行 worktree**，绝不给它们各开隔离 worktree——否则下游 task 看不到上游代码。`isolation: worktree` 只给真正并行且写集无交集的 task 用。线性依赖或共享文件（如 T001→T002→T003）= serial-isolation：仍每 task 一个 subagent（隔离上下文），但同 worktree 串行。

**inline 执行**（orchestrator 亲自写代码，不派 subagent）仅在以下情况，且须记录原因：

- 运行时 / 平台不支持 subagent 或 Task 工具。
- 该 task trivial 或极小（派发 + ingest 开销 > 收益），如纯配置、单文件小改、纯文案。
- orchestrator 已完整持有该 task 精确上下文且已实现到一半（中途转交反而浪费已加载上下文）。

记录 `inline worktree execution` 及原因。这是正常策略，不是失败。

无论 inline 还是 subagent，执行顺序都遵循 `task-index.md` 的 Task DAG 与 lanes，按“barrier/contract → backend capability fan-out → frontend screen fan-out → integration/E2E”推进：

1. **Contract / context wave**：不写业务 UI；确认 API-for-UI、Screen states、mock/real adapter、DESIGN.md source pointers、`docs/project/ui/` catalog source 都进入 `_execution_context.md`。
2. **Backend/API capability waves**：按 capability task 落地后端、API、AI adapter、数据与测试。允许为前端提供类型、mock adapter 或最小探针；不顺手搭完整页面。
3. **Frontend composition waves**：按 Screen/Route 整体实现 UI。每个 Screen task 必须读同屏 sibling Units / sibling tasks、现有 route/components、DESIGN.md、`docs/project/ui/` catalog、当前 task 注入的 Screen context 和 API-for-UI；一次性完成布局区域、主任务、关键状态和相关 UI AC。
4. **E2E polish wave**：跑完整业务演示脚本，补字段、错误状态、截图证据和最终验证。前端 Epic 在本 wave 内**必须**先做 cross-screen visual polish pass（见下），再做最终验证。

### Cross-screen visual polish pass（前端 Epic 必做）

动机：各 Screen 由不同 subagent 持最小上下文分别实现，taste 与规格会跨屏漂移（页框 padding、页头规格、区块 gap、字号档、同类组件不同实现、accent 用量）。单屏闸门查不出跨屏不一致，必须有一个**同时看到所有屏**的 pass。

做法：

1. 所有 frontend composition wave 完成后，收集全部 Screen 的桌面截图（复用各 Screen 出口闸证据，不重截）。
2. 派一个独立 audit subagent（屏 ≤2 个时可 orchestrator 亲自做），输入 = 全部截图 + `DESIGN.md` §Spacing Hierarchy / 字阶表 + `dense-ui-craft.md` 反模式速查，输出 = 漂移清单：逐项报 跨屏页框 padding 是否一致、页头规格是否一致、字号档是否超标、同类组件是否多套实现、accent 是否超预算，每项给 Screen + 文件定位。
3. 漂移项统一修复（优先抽共享组件/常量，禁止逐屏手调出第三种规格），修完重截受影响屏，过一遍对应闸门轨。
4. 漂移清单与修复结果记入收尾的变更叙事。

### Subagent 派发契约

subagent prompt 必须自包含，至少包含：

- review pack 目录 path。
- task doc path + `task-index.md` path。
- `_execution_context.md` path。
- Unit ID 与完整 Unit/Task Context Packet。
- Task ID、task scope（barrier / owner / capability / screen / integration）、write scope、plan anchors、catalog anchors、stop conditions。
- 如果是 UI task：Screen ID / Route / Screen type / Primary Job / Covered Units / Regions / Information priority / Richness floor / Forbidden patterns / API-for-UI / Screen done / sibling Units / **所属 app shell + 全局导航契约**（DESIGN.md §Layout / design_guidelines.md / 共享 layout 组件——告知子代理该屏套在哪个外壳、复用哪个共享 layout，不得自造导航 frame）/ **Reference image 路径**（有则必传：实现目标 = 复刻该图 + 接真实数据，再按 Screen Contract 补交互与状态，不是照散文自由发挥）。
- write scope：允许修改的路径。
- Verification command。
- source pointer fallback 规则。
- return contract：
  - changed files。
  - verification commands and results。
  - deviations from task / Unit Packet。
  - risks / blockers。

即使 Codex `spawn_agent(fork_context=true)` 或 Claude Code isolation 可继承上下文，也必须显式传 Unit/Task Context Packet；父 agent 的隐式理解不算执行合同。

worktree / ingest 约束（serial-isolation 默认）：

- 依赖型 / 共享文件 task 的 subagent **在 orchestrator 当前的执行 worktree 内工作**（cwd 即该 worktree），**不要传 `isolation: worktree`**——否则下游 task 看不到上游已落盘代码。`isolation: worktree` 仅留给 parallel-isolation 的无依赖、写集无交集 task。
- orchestrator **只消费子代理返回的结构化小结**（changed files / verification 结果 / deviations / risks），**绝不 Read 子代理 transcript / `.output`**（那是完整对话 JSONL，会撑爆主上下文）。**例外——UI-critical 屏的截图 artifact 必须看**：commit 这类屏前，orchestrator 亲自 Read 截图文件（轻量 PNG，不撑上下文）或派独立 visual-auditor，不得仅凭小结里的 "passes" 文字就 commit UI 屏（见上文铁律「UI-critical 屏的出口闸判定独立于实现」）。
- 串行派发：上游 task 的 subagent 返回并（strict 下）commit 后，再派下游；下游 prompt 里注明“上游 task 已完成、读已落盘状态”。
- subagent 内部跑 Task Loop（fast / strict），含实现 + Verification，并在 return contract 里给出变更叙事素材；orchestrator 负责把它 append 进 `_ledger.md`（strict 逐 task、fast 收尾统一）、commit（若子代理未提交）、review gate、跨 task / Unit 编排。

### Task Loop：fast

```text
mark in-progress in session plan
read T{NNN}.md Generated from / Source anchors / Write scope / Read first / Technical Approach / AC + DoD / Stop conditions
read Unit/Task Context Packet from _execution_context.md
if UI task: read Screen context + sibling UI Units + existing route/component files
read target files
read pattern files (max 1-3 unless source pointer requires more)
read design.md / decisions.md anchored sections only when T{NNN}.md says to, or when strict trigger / ambiguity / conflict appears
honor Approach / Patterns / Execution note reuse, high-risk flow, and fallback constraints
if task / Unit already satisfies Verification: mark skipped/completed with evidence
apply test policy
implement narrowly; if frontend-composition, implement the whole Screen scope, not an isolated Story fragment
run task Verification; if this is a Unit收口 task, also run `verify.sh {U-ID}` as Unit Verification
fix failures, max 3 attempts
apply risk-based UI/system checks
record in session memory: changed files, verification result, deviations, risks
```

fast mode 不逐 task 回写 `_ledger.md`（收尾统一 append），不 per-task commit；task 文档任何时候都不回写——它是纯投影。这样减少文档维护对 coding 注意力的干扰。

### Task Loop：strict

strict mode 在 fast loop 基础上保留旧版审计行为：

- 若 `Execution note = test-first`，先写失败测试并确认红灯，再实现。
- 若 `Execution note` 禁止 fallback/mock/简化实现，先确认目标权威实现 / 官方 API / 标准协议 / 真实依赖可用；不可用则 STOP，不写替代实现。
- task 完成后 append `_ledger.md` 变更叙事（实际做了什么 / 怎么满足 AC / 关键权衡与偏离 / verification 命令与结果 / commit SHA + 关键文件）；若该 task 是 Unit 收口 task，同时记录 Unit Verification（`verify.sh {U-ID}` 输出摘要）。
- 更新 `_ledger.md` 状态、commit、verification；task 文档不回写。
- 每 task 提交代码 + ledger；Unit 收口可作为单独 integration/verification task 提交。
- UI-critical 必须完整桌面+移动截图与 DESIGN.md checklist。
- frontend-composition task 必须记录 Screen Contract 覆盖情况：Primary Job、Regions、Key States、API-for-UI、Covered Units、Screen done。

### Test policy

默认从 task packet / Unit Packet 的 `Execution note` 读取；若未明确，按风险判定：

- `test-first`：bugfix、权限、安全、领域规则、事务、并发、迁移、数据一致性。
- `test-with-implementation`：CRUD、DTO、字段映射、简单 API、UI data binding。
- `verification-only`：纯配置、纯样式、小文案、小重命名。

strict mode 遵守 task packet / review pack anchor 中明确的 test-first。fast mode 只有 trivial/plumbing 可以降级，且收尾 summary 必须说明。

### UI QA policy

UI class：

- `critical`：新页面、app shell、navigation、layout、theme、视觉重构、DESIGN.md global token；login/signup/landing/空首屏/营销页等 front-of-house Screen 默认 critical。
- `functional`：表单状态、按钮交互、API data binding、局部组件、局部列表/表格。
- `trivial`：文案、label、小样式、字段显示。

执行要求：

- critical：读 DESIGN.md 对应锚点原文 + `docs/project/ui/` catalog / task Screen context；**开工前先过参考图前置闸**（见 Frontend composition gate：已批准参考图或继承屏型金标准；无任何闸产物时才退 `design-taste-frontend`/`high-end-visual-design` 范式兜底），不许照散文搭最小骨架；桌面+移动截图；逐条核对 task 注入的 DESIGN.md checklist 与 Screen 合同 + `frontend.md` 出口闸对应轨（operational 屏 = B 轨客观硬线，不接受无对照的主观 pass）；**截图后过独立设计评审 gate（见下）**——不满足先修。
- functional：读相关 pattern/token/source pointer；若属于 frontend-composition，做 Screen-level browser check；否则做 targeted browser check 或局部截图；验证 loading/error/empty/success/permission 中实际相关状态。
- trivial：不强制截图；跑 typecheck/test/lint 或 Unit Verification。

**门面屏富度 gate（critical 且属 front-of-house / 视觉重构 / app-shell·导航·theme，强制）**：
按 `.claude/rules/frontend.md` 出口闸 A 轨执行，重点 A4（正向存在性判据，空了就 FAIL）、
A5（判定权独立，评审不许自评）、A6（登录页硬线）。条目内容以 frontend.md 为唯一真相源，本 skill 不复述。

如果 task 文档与 `DESIGN.md` 冲突，以 `DESIGN.md` 原文为准；缺设计合同且属于 UI-critical，STOP。
如果 task 文档与 `docs/project/ui/` catalog 冲突，以已同步 catalog 为整屏体验真相源；若 catalog 缺失则以 `design.md` UI Surface Delta 为临时真相源。合同缺失或明显不覆盖当前 Route 时，STOP 回到 vj-epic-plan 修正并同步 catalog。

### Frontend composition gate

进入任一 frontend-composition task 前必须检查：

- Screen ID / Route / Primary Job / Role 明确。
- Screen type / Richness floor / Forbidden patterns 明确。
- Covered Units 与 sibling UI Units 明确，且当前执行不会破坏同屏已实现区域。
- API-for-UI 合同明确：endpoint / 字段 / 状态枚举 / 错误语义 / mock 或真实 adapter。
- `docs/project/ui/` catalog source 或 `design.md` UI Surface Delta source 明确。
- 目标 route/component 文件已读取；若不存在，明确新建位置与路由注册方式。
- Screen done 可浏览器验证。
- **参考图前置闸（fast/strict 均不豁免）**：UI class = critical 的屏开工前必须存在已批准参考图
  `docs/reference/research/designs/{epic-id}/{screen-id}.png`。缺失时：在 Phase 2 审批点用该屏
  Screen Contract + `DESIGN.md` token 渲染一次性 HTML 并截图作为参考图候选，STOP 给人批
  （复用 approval gate 机制，批图是秒级操作）；批准后才进 composition wave。
  范围控制：仅 front-of-house 屏 + 每个屏型的第一张屏需新出参考图；同屏型后续屏直接继承
  屏型金标准（`docs/reference/research/designs/golden/`，由 `vj-design-md-matcher` Phase 4.5 产出）
  + `DESIGN.md` §Reference Skeletons，不重复出图、不重复审批。
  参考图一律 HTML 直出，禁止生图模型画 UI（实测：文字糊、方向坍缩、AI 模板味）。

不满足时不要“先随便做 UI”；补 `_execution_context.md` 或停止回到 plan。

### System-wide check policy

默认不再无边界"往外追两层"。按 Unit Packet 判定：

- `none`：纯文档、纯样式、纯文案、局部测试。
- `direct-neighbors`：检查当前文件直接调用者/被调用者与 Verification 覆盖。
- `risk-triggered-two-hop`：命中 auth、permission、ownership、transaction、UoW、domain event、Celery、external client、storage、cache、migration、schema、public API、middleware、dependency injection、delete/update 状态流转时，追两层并确认无孤儿状态/副作用遗漏。

### 失败收口

- Verification 失败：修复最多 3 次；仍失败则 STOP，报告最后输出、已试方案、阻塞的下游 Unit。
- 复用 / 高风险流程 / forbidden fallback 冲突：执行期发现 plan 要求不可满足时，不得把 mock、简化实现、过期缓存、默认值或替代算法当成功路径；切 strict。strict 后仍无法满足则 STOP，并报告需要回到 vj-epic-plan / 用户决策的点。
- subagent 报错/超时/空小结：重派一次；仍失败则该 Unit blocked，不合并其分支，报告下游影响。
- 参考图缺失且无法现场渲染（Playwright/浏览器不可用、或审批不可达）：降级为“屏型金标准 + DESIGN.md §Reference Skeletons 文字契约”执行，并在变更叙事中记录降级原因；不得静默跳过参考图闸，也不得因此阻塞非 UI Unit。
- merge 冲突：先 rebase 执行分支到 integration base 后重跑 Verification；仍冲突则 STOP，禁止 `-X ours/theirs` 盲猜。
- worktree 创建失败：确认 `.vj/` 已忽略并重试一次；仍失败则 STOP 或明确 fallback 到当前 worktree-only docs 操作，不直接改主仓库代码。

### 边做边简化

fast：每完成一个 wave 或 2-3 个 Unit，检查新增重复和明显复杂化，仅做低风险整理。

strict：同上，并在 ledger 记录整理原因。

## Phase 4：收尾

1. 全量验证：
   - 跑 `bash <work_dir>/verify.sh all`（全部 Unit 的 Story AC 验证物化入口）；verify.sh 缺失或与 story AC 冲突时以 story 为准，逐 Unit 手跑并报告差异。
   - 前端 Epic 跑每个 Screen 的 Screen done / Browser verification，并保留桌面+移动截图或 targeted screenshot 证据；确认 cross-screen visual polish pass 已执行、漂移清单已清零或在叙事中记录残留原因。
   - 跑项目 lint/typecheck/test（按 backend/frontend 命中情况）。
2. Review gate：
   - fast：只有 strict trigger、敏感面、大 diff 或用户要求时跑 review skill。
   - strict：跑完整 diff review。
   - blocking findings 必须修；non-blocking notes 记录但不阻塞 fast。
3. Requirements compact trace：
   - `R-ID -> Unit / file / verification`。
   - `Deferred item -> resolution`。
   - `Scope boundary -> checked / exceptions`。
   - fast 用 compact trace；strict 可展开完整核对。
4. 记录与提交：
   - fast：一次性 append `_ledger.md`（全部 task 的状态 + 变更叙事）、更新 `_execution_context.md` final profile、翻转 review pack `README.md` status；创建 feature/wave 级提交。
   - strict：确认每 task 的 ledger 记录已完成，且每个 Unit 的收口验证已记录；如仍有 README status / review notes / final trace 未提交，创建 docs-only 收尾提交。
5. 清理 worktree / 临时分支，确保当前工作树没有本 skill 产生的未提交记录。
6. 如执行中形成可复用经验，提示用户用 `vj-compound` 沉淀。

### Lightweight execution profile

收尾时在 `_execution_context.md` 或 `_ledger.md` 记录：

```text
mode:
strict triggers:
context files loaded:
unit verification commands:
screen verification commands:
ui screenshot triggered:
review triggered:
subagent triggered:
user wait triggered:
task/ledger writes:
blocked / retries:
```

这用于下次判断慢点，不应在每一步实时回写拖慢执行。

## 不做什么

- 不做计划级语义深审；那是 `vj-plan-review` 的职责。
- 不重算正常 plan 的波次/依赖；只消费 `task-index.md`，缺失时才 fallback。
- 不重写 AC，不改 epic.md，不改 review pack 正文。
- 不把 checklist 当完整规范；source pointer 与项目文档仍是真相源。
- 不让 subagent 靠父上下文猜任务；所有 subagent 任务必须自包含。
- 不在当前主仓库工作树直接写业务代码。
