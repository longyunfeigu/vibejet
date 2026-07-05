# vj-epic-plan

以**一个 Epic（含若干 Story）为单元**生成实现计划（HOW）。

## 在工作流中的位置

```
vj-epic-story (WHAT: Epic/Story + 可执行 AC)
      ↓
vj-epic-plan  (HOW: 本 skill —— 人工 Review manifest + epic 级 delta + catalog sync + task 文档)
      ↓
vj-work (执行)
```

## 产出

`docs/tasks/plans/{date}-epic-{N}-{slug}/` review pack 目录。输出按两类读者组织——**human reviewer 看 README/design/decisions，执行器看 task-index/T*.md/verify.sh**：

- **Context Ownership**：review pack 是人工 review manifest + 本 Epic delta；稳定跨 Epic 上下文写入 catalog；AI coding 执行上下文写入 task docs / `_execution_context.md`。
- **人工 review 主面**：`README.md` 负责入口、冲突和阅读路径；`design.md` 负责问题建模、术语场景、模块边界、依赖图、核心流程、DB/API 设计、风险和 reviewer checklist；`decisions.md` 是 D/ACD 唯一真相源。
- **给机器看（不需散文润色）**：`docs/tasks/work/epic-{N}-{slug}/task-index.md` + `T*.md`，包含 Unit/Task DAG、波次、共享文件冲突、write scope、验证命令和 stop conditions。
- **Unit 粒度**：每个 Story 映射为一个 Implementation Unit；Unit 是产品语义边界，不按前端 / 后端 / 数据库拆开。
- **前端 Surface 粒度**：前端 Epic 在 `design.md` 生成 UI Surface Delta / Screen Contract，按 Screen/Route 定义 Screen type、Primary Job、Regions、Information Priority、Richness Floor、Forbidden Patterns、States、Covered Units、API-for-UI 和 Screen done，并在 Phase 5 同步到 `docs/project/ui/surfaces.md` / `routes.md`。产品/品牌方向来自 `docs/project/DESIGN.md` + golden screens；若缺失，先回到产品级 `ui-requirement-brief -> vj-design-md-matcher`，不要在 plan 里发明风格。Story/Unit 继续负责验收追踪；前端实现由 `task-index.md` 的 Frontend composition waves 按 Screen 聚合执行。
- **跨 Epic 契约**：单一真相源 = catalog（`docs/project/api/`、`docs/project/data/`、`docs/project/ui/`）。`Consumes` 由 Agent B 读 catalog 生成；本 Epic 对下游的契约写进 catalog，**不在 review pack 写 Provides 表**；跨切面不变量（R1.x）写进 `data/overview.md` / `api/conventions.md` / `ui/surfaces.md`。下游 epic 读 catalog，不翻旧 review pack / legacy plan。
- **决策单一真相源**：完整论证只写在 `decisions.md`。技术方案与 Story AC 冲突时必须回改 AC 或显式审批，不允许静默替换验收口径。
- **模块化契约目录同步**：命中 API delta 时更新 `docs/project/api/conventions.md` + `docs/project/api/{module}.md`；命中 schema / persistence delta 时更新 `docs/project/data/overview.md` + `docs/project/data/{module}.md`；命中 UI delta 时更新 `docs/project/ui/surfaces.md` + `docs/project/ui/routes.md`。同步发生在 `vj-plan-review` 采纳修正之后，保证 catalog 与最终 review pack 一致。旧 `api_spec.md` / `database_schema.md` 仅兼容读取。
- **task 文档（执行投影）**：Phase 5 review pack 定稿后，在 `docs/tasks/work/epic-{N}-{slug}/` 生成 `task-index.md` + 每 task 一份 7 段文档 + `verify.sh`（Unit verification 可执行入口，命令物化自 Story AC `验证:`）。默认 `1 Unit = 1 task`；只有依赖、文件隔离、局部验证和并行收益都清楚时才允许 `1 Unit → 多 task`，且必须生成 task DAG / 波次 / 冲突表。前端 Screen composition task 是 UI Surface Delta / catalog 明确要求时的执行投影，必须列 Covered Units、Screen done 和 UI AC 回指。task done 不等于 Unit done，Story AC 闭环仍由 Unit 验收。**task 文档是纯投影，不承载执行记录**（状态 / 变更叙事 / verification 结果住 vj-work 的 `_ledger.md`），因此续作 / 重跑整目录覆盖重写是安全的。写盘后必须跑 `plan_lint.py` 机检（anchors 闭合、T 文档齐全、路径存在），exit 0 才能 handoff。

## 关键设计取舍

- **不 fork compound 的 ce-plan**：只借其 implementation-units / Provides-Consumes / 方向性设计思想，按 vj 轻量风格自包含实现，零插件耦合。
- **research 并行多代理**：Phase 2 优先并行派 design-context / upstream-contracts / codebase-scout 三个只读研究任务（模板见 `references/research-agents.md`）+ 条件性 `vj-learnings-researcher`；无 subagent 能力时顺序内联执行，仍保留三份结构化结果。
- **学习飞轮**：读端 `vj-learnings-researcher`（Phase 2 调用），写端 `vj-compound`（实现收尾后沉淀 `docs/solutions/`）。

## 文件

- `SKILL.md` — 5 Phase 工作流
- `references/plan-pack-readme.template.md` — human review 入口模板
- `references/plan-pack-design.template.md` — human 技术设计模板（三区制：叙事区 5 必答问题 / 合同区刚性块 / 深潜附录；锚点只锚合同区）
- `references/design-golden-sample.md` — design.md 三区制金样例（写法参照，标题勿照抄）
- `references/plan-pack-decisions.template.md` — D/ACD 决策真相源模板
- `references/task-index.template.md` — task 执行入口模板
- `references/task-doc.template.md` — per-task 7 段执行文档模板（**唯一副本**，vj-work 回退生成也用这份）
- `references/verify.template.sh` — Unit verification 可执行入口模板
- `references/research-agents.md` — Phase 2 并行研究代理模板（design-context / upstream-contracts / codebase-scout）
- `.agents/skills/_shared/scripts/plan_lint.py` — Phase 5 机检脚本（vj-work Phase 1 装载前也跑）
- `README.md` — 本文件
