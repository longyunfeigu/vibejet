---
name: vj-work
description: 消费 vj-epic-plan 产出的 epic 实现计划并落地为已实现、已验证、已记录的代码。用户说"执行这个 plan""做 epic X""跑实现""把计划落地""vj-work"时使用。在 vj-epic-plan 之后使用；单 Story 小需求同样按单 Unit 执行。
---

# vj-work — Epic 执行器 v3

把 `vj-epic-plan` 产出的 task packets 落地成"已实现、已验证、已记录"的代码。
工作流位置：在 vj-epic-plan（及其自动的 vj-plan-review）之后；完整链条见 `docs/reference/guides/ai-workflow.md` §1。

v3 核心变化（相对 v2）：**task doc 即执行包**——废弃 `_execution_context.md` 二次蒸馏层，
Epic Execution Checklist 与 packet 字段由 vj-epic-plan 在 plan-time 一次做对；并行成为同波次
默认派发策略；人在环审批集中到 Phase 2 一次处理；验证按 task 定向 → Unit 收口 → Epic 全量
分层去重。mode 判定与执行档案记入 `_ledger.md`。

## 第一性原理

质量来自：①清楚的任务规格（task doc）②相关约束足够近（packet 内联 + Epic Checklist，不靠
全文重读 guideline）③真实反馈回路（Verification 是 done signal）④风险正确升级（strict
triggers）⑤UI 按 Screen 体验闭环交付，不按 Story 碎片堆砌 ⑥orchestrator 上下文卫生（重活
下沉 subagent，主 session 只编排与审计）。速度来自：同一信息只蒸馏一次（plan-time）、
同一材料只读一次（精准指针代替全文）、可并行的事不串行、等人的事集中一次等。

## 铁律

1. **Task packets 是执行入口**。`task-index.md` + `T{NNN}.md` 即执行包；review pack 的
   design/decisions 只在 anchors、strict trigger、歧义或冲突时按小节回读。不改 review pack
   正文；唯一允许改动是收尾把 README frontmatter `status: active -> completed`。
2. **Verification 是 done signal**。task 定向命令必须实际跑通，未跑通不得标 completed；
   验证分层：task 定向 → Unit 收口 `verify.sh {U-ID}` → Phase 4 Epic 全量，同层不重复跑。
3. **worktree 隔离**。改代码一律从当前 `HEAD` 开执行 worktree，不在主仓库工作树写业务代码。
4. **当前非默认分支即 integration base**。只读分支名与工作区状态；不翻 commit 历史猜 base；
   仅默认分支或未提交改动歧义才停下问人。
5. **上下文可回溯**。Epic Checklist 与 packet 约束是 attention guide 不是完整规范，每条带
   source pointer；`DESIGN.md`、catalog、layer skill 原文仍是真相源，碰到清单外风险面按
   指针展开对应小节，不无差别全文重读。
6. **Backend by capability, frontend by experience**。前端按 Screen/Route 整体实现
   （Screen context 住 task doc 注入块 + `docs/project/ui/` catalog）；禁止孤立 UI 片段、
   脱离 Screen Contract 的单页/卡片堆/表单堆；合同稳定即可开工，不等后端 100%。
7. **前端出口闸以 `.claude/rules/frontend.md` 为唯一真相源**（A/B 轨、富度 R、工艺 C），
   本 skill 不复述。整屏交付（frontend-composition）与 UI class = critical 的屏，pass/fail
   判定权独立于实现者：orchestrator commit 前必须真看截图或派独立 visual-auditor，实现
   subagent 自评 "passes" 不构成过闸（协议见 `references/ui-execution.md`）；
   functional 局部改动走 targeted check，不需独立审计。
8. **subagent 任务自包含**。显式传 task doc path + Epic Checklist 原文 + write scope +
   Verification + return contract（完整契约见 `references/subagent-dispatch.md`）；
   orchestrator 只 ingest 结构化小结，绝不 Read 子代理 transcript / `.output`
   （UI 截图 artifact 例外——必须看）。
9. **高风险自动 strict**。命中 strict trigger 不得为速度降级；不确定风险等级按 strict
   或精准补读 source pointer。
10. **plan 声明的复用 / 高风险流程 / 禁 fallback 约束是执行合同**。执行期发现必须违背时
    不得自行改口径：切 strict，仍无法满足则 STOP。KISS/YAGNI：只实现 task 要求。
11. **完成整个 feature**。不留 80% 半成品；blocked 必须说明阻塞点、已试方案、下游影响。

冲突真相源优先级：Story AC / 用户决策 > catalog > `decisions.md` approved / `design.md` >
task packet 投影 > 现有代码模式。task doc 与 `DESIGN.md` 冲突以 `DESIGN.md` 原文为准。

## 输入与配置

```text
vj-work docs/tasks/plans/2026-06-01-epic-1-.../   # review pack 目录
vj-work epic-1
vj-work                                            # 取 plans_dir 下最新 review pack
```

```yaml
epic_work_executor:
  plans_dir: docs/tasks/plans/
  work_dir: docs/tasks/work/epic-{N}-{slug}/
  worktree_root: .vj/worktrees/
  execution_mode: auto          # auto | fast | strict
  approval_gate: auto           # auto | true | false
  commit_granularity: auto      # auto: fast=feature/wave, strict=per-task
  learnings_skill: vj-compound  # optional post-run prompt
```

## Mode 与 strict triggers

| Mode | 目标 | 行为 |
|------|------|------|
| `fast` | 普通 AI coding 吞吐 | 最小读集、收尾统一记录、feature/wave commit、风险触发 QA/review |
| `strict` | 高风险交付审计 | 审批门、逐 task ledger + commit、完整 UI QA、完整 review/trace |
| `auto`（默认） | 先判 strict triggers | 命中即 strict，否则 fast；执行中命中新 trigger 立即升级 |

Strict triggers（细化自 AGENTS.md「Plan 规范」，冲突以 AGENTS.md 为准）——命中任一即 strict：
auth/session/permission/ownership/tenant；DB schema/migration/backfill/破坏性更新；公共 API
契约/DTO envelope/错误码/向后兼容；payment/crypto/secrets/安全敏感依赖；事务/UoW/幂等/并发/
domain event/Celery/外部副作用；app shell/navigation/theme/DESIGN.md 全局 token/UI 架构；
预计 diff 跨子系统 ≥400 行或总计 ≥1000 行；用户明确要求 strict/audit/审批/逐 task commit；
执行包引不出必需 source pointer 或歧义会改变行为；执行看起来必须违背 plan 显式约束
（复用声明、高风险流程、禁 fallback/mock/简化实现）。
非 trigger 的 CRUD、DTO、字段映射、局部 UI data binding、文案/样式修正默认 fast。

## Phase 0：定位与 branch gate

1. 按输入解析 review pack 目录；空参取最新。
2. Branch gate：只跑 `git branch --show-current` + `git status --short`。非默认分支 → 直接
   视为 integration base 不询问；默认分支 → STOP 确认。工作区干净 → 从当前 `HEAD` 开执行
   worktree；有未提交改动 → 本 skill 产物按记录策略处理，用户代码改动 STOP 让用户选
   commit / stash / 仍以当前 `HEAD` 继续。
3. 不 checkout 主仓库到其他分支。

## Phase 1：装载（不再二次蒸馏）

1. 跑 `python3 .agents/skills/_shared/scripts/plan_lint.py <review-pack-dir>`；exit != 0 →
   STOP 回 `vj-epic-plan` 修正（lint 不可用时降级为人工核对：T 文档齐全 + Execution note
   五字段完整）。
2. 读 `task-index.md`（唯一默认全读文件）：Required gates、**Epic Execution Checklist**、
   Unit/Task DAG、波次 + Batch 列、Execution lanes、共享文件冲突表。
3. task docs 已存在 → 直接装载；缺失 → 按 `vj-epic-plan/references/task-doc.template.md`
   （唯一副本）从 design/decisions/task-index + catalog 回退投影生成，写明 Generated from +
   anchors，不重新发明 HOW。执行包字段不完整（Execution note 五字段、UI task 的 Screen
   context）且非 trivial → STOP 回 vj-epic-plan，不在执行期自由发挥。
4. Mode 判定：只读各 task 的 Execution note / Risk class 与 task-index Required gates，
   不读 task 全文；结果与理由写入 `_ledger.md` Mode Decision（按
   `references/ledger.template.md` 初始化）。

v2 的 epic-level layer scan 与 `_execution_context.md` 生成已废弃：Epic Checklist 由
plan-time 产出，orchestrator 不再全文扫读 layer skill。

## Phase 2：波次计划与集中审批

- 波次直接消费 task-index 的 Task DAG / Batch / lanes，不重算；缺 Task DAG 才按
  Files + Depends 回退补算一次。
- 前端 Epic 无 lanes 但多个 UI Unit 共享同一路由 → 生成临时 Screen 分组记入 `_ledger.md`，
  按 Screen 串行执行，避免并行写坏 UI。
- **参考图批量前置闸**（前端 Epic，fast/strict 均不豁免）：开工前一次处理全部 UI-critical
  屏——已有已批参考图或可继承屏型金标准的直接登记；缺的一次性渲染全部候选并**一次审批全批**；
  执行中不再逐屏 STOP。完整协议与降级规则见 `references/ui-execution.md`。
- Approval gate：`true` → 总是 STOP；`false` → 不审批（hard strict trigger 仍需用户决策）；
  `auto` → fast 输出短执行摘要后继续，strict 一次 STOP（waves + strict reason + 参考图候选
  一并展示）。无人值守且 strict 审批不可达 → fail closed：不执行 strict 面 task，输出阻塞
  报告。批图审批与 strict 执行审批是两个不同 gate：参考图闸的降级路径只适用于非 strict 面
  的 UI task，同屏命中 strict trigger 时 fail closed 优先。
- Docs-context commit：fast 下执行若依赖未提交的 task docs / `_ledger.md`，自动创建
  docs-context commit（不问人）；strict 动代码前提交。

## Phase 3：执行

Unit 是验收边界，task 是执行边界。派发模式按序判定：

| 模式 | 条件 | worktree |
|------|------|----------|
| **batch dispatch**（plan 显式标注优先于下两行） | task-index Batch 同组；或执行期发现相邻小 task（同 lane、合计 diff <300 行、共享 pattern） | 一次派发多 task，共享 worktree |
| **parallel-isolation**（同波次默认） | 同 wave + 冲突表写集无交集 + 无依赖 + 未标 Batch | 各 task 独立 worktree，完成后按 DAG merge |
| **serial-isolation** | 依赖链 / 共享文件 / owner task | 共享执行 worktree，按 DAG 串行派发 |
| **inline** | 无 subagent 运行时 / task trivial / 上下文已加载过半 | 执行 worktree，记录原因 |

关键：依赖型 / 共享文件 task 绝不各开隔离 worktree（下游看不到上游代码）。派发字段、
return contract、worktree/ingest 细则见 `references/subagent-dispatch.md`。

**subagent 默认读集（冷读瘦身）**：task doc 全文 + prompt 内注入的 Epic Checklist + 目标
文件 + ≤3 pattern files。guideline / `DESIGN.md` 全文不进默认读集——只按 task doc Read
first 的精准指针、或执行中碰到清单外风险面时展开对应小节；找不到可靠 source → 切 strict
或 STOP。

wave 推进顺序：contract/barrier → backend capability fan-out → frontend screen
composition → integration/E2E polish。backend wave 允许为前端提供类型、mock adapter 或
最小探针，不顺手搭完整页面；frontend wave 按 Screen/Route 一次性完成布局区域、主任务、
关键状态与关联 UI AC。

### Task Loop：fast

```text
read T{NNN}.md 全文（含 Execution note packet 字段 + UI 注入块）
if UI task: read Screen context 指向的 catalog 小节 + 同屏 sibling + 现有 route/component
read 目标文件 + pattern files（≤3）
若已满足 Verification：标 skipped/completed 附证据
按 Test policy 实现；frontend-composition = 整屏 scope，不做 Story 碎片
跑 task 定向 Verification（禁全量套件）；失败修复，最多 3 次
Unit 收口 task 另跑 bash verify.sh {U-ID}
按 System-wide check 字段做邻域检查（none | direct-neighbors | risk-triggered-two-hop）
return 结构化小结（changed files / verification / deviations / risks）
```

fast 不逐 task 回写 ledger（收尾统一 append）、不 per-task commit；task 文档任何时候不回写。

### Task Loop：strict（在 fast 基础上追加）

- `test-first` 先写失败测试确认红灯再实现；禁 fallback 的 task 先确认真实依赖/权威实现
  可用，不可用 STOP 不写替代实现。
- 每 task 完成即 append `_ledger.md` 变更叙事 + commit（代码 + ledger）。
- UI-critical 完整桌面+移动截图；frontend-composition 记录 Screen Contract 覆盖情况。

### Test policy（task doc Execution note 未明确时按风险判定）

`test-first`：bugfix、权限、安全、领域规则、事务、并发、迁移、数据一致性。
`test-with-implementation`：CRUD、DTO、字段映射、简单 API、UI data binding。
`verification-only`：纯配置、纯样式、小文案、小重命名。
fast 只有 trivial/plumbing 可降级且收尾 summary 说明；strict 遵守 plan 标注不降级。

### UI QA（按 task doc 的 UI class 字段）

- `critical`（新页面、app shell、theme、front-of-house 屏默认）：对照 Phase 2 已批参考图
  实现；桌面截图 + frontend.md 对应轨闸 + 独立视觉审计（见 `references/ui-execution.md`）；
  移动端截图仅当 responsive 是 AC 或屏型合同要求。
- `functional`：Screen-level 或 targeted browser check，验证实际相关状态。
- `trivial`：typecheck/test/lint 即可，不强制截图。
- UI-critical 缺设计合同（`DESIGN.md` 与 fallback 均缺）→ STOP。
- 进入 frontend-composition task 前核对：Screen 合同字段完整、参考图已批或继承 golden、
  目标 route/component 已读（不存在则明确新建位置与路由注册）、Screen done 可浏览器验证。
  不满足不要"先随便做 UI"，回 Phase 1 步骤 3 的 STOP 路径。
- Cross-screen visual polish：≥3 屏派独立 pass，≤2 屏 orchestrator 逐屏审计时顺手核对
  （见 `references/ui-execution.md`）。

### 边做边简化

每完成一个 wave 或 2-3 个 Unit，检查新增重复与明显复杂化，只做低风险整理；strict 在
ledger 记录整理原因。

## 失败模式与兜底

| 场景 | 一线处理 | 仍失败 |
|------|---------|--------|
| Verification 失败 | 修复 ≤3 次 | STOP：报最后输出、已试方案、阻塞的下游 Unit |
| 复用/高风险流程/禁 fallback 冲突 | 切 strict | STOP 回 vj-epic-plan / 用户决策；禁把 mock/简化当成功路径 |
| subagent 报错/超时/空小结 | 重派 1 次 | 该 task blocked，不合并其分支，报下游影响 |
| 参考图无法渲染 / 审批不可达 | 降级屏型金标准 + 文字契约，记 ledger | 不静默跳过；不阻塞非 UI task |
| merge 冲突 | rebase 到 integration base 重跑 Verification | STOP；禁 `-X ours/theirs` 盲猜 |
| worktree 创建失败 | 确认 `.vj/` 已忽略，重试 1 次 | STOP 或 fallback 当前树 docs-only 操作，不改主仓库代码 |
| plan_lint 不可用 | 人工核对 T 文档齐全 + packet 五字段 | 缺关键字段且非 trivial → STOP 回 plan |
| strict 审批不可达（无人值守） | fail closed：不执行 strict 面 task | 输出阻塞报告，列已完成/未执行清单 |

## Phase 4：收尾

1. 全量验证（只在此处跑一次）：`bash <work_dir>/verify.sh all`（缺失或与 Story AC 冲突以
   story 为准逐 Unit 手跑并报差异）；前端逐屏 Screen done + 截图证据，确认 cross-screen
   漂移清单清零或记录残留原因；跑项目 lint/typecheck/test（按 backend/frontend 命中面）。
2. Review gate：fast 仅 strict trigger、敏感面、大 diff 或用户要求时跑 `review` skill；
   strict 跑完整 diff review。blocking findings 必修；non-blocking 记录不阻塞 fast。
3. Compact trace：`R-ID -> Unit/file/verification`、`Deferred -> resolution`、
   `Scope boundary -> checked`；strict 可展开完整核对。
4. 记录与提交：fast 一次性 append `_ledger.md`（全部 task 条目 + Final Execution Profile）
   并创建 feature/wave commit；strict 确认逐 task 记录完整，补 docs-only 收尾提交。
   翻转 review pack `README.md` status。
5. 清理 worktree / 临时分支；如有可复用经验提示 `vj-compound` 沉淀。

## 不做什么

- 不做计划级语义深审（`vj-plan-review` 职责）；不重算正常 plan 的波次/依赖。
- 不重写 AC、不改 epic.md、不改 review pack 正文。
- 不生成 `_execution_context.md`——task doc 即执行包；执行包不完整回 `vj-epic-plan` 修正，
  不在执行期自建蒸馏层。
- 不让 subagent 全文重读 guideline / `DESIGN.md`，也不让 subagent 跑全量测试套件。
- 不让 subagent 靠父上下文猜任务；所有派发必须自包含。
- 不在主仓库工作树直接写业务代码。
