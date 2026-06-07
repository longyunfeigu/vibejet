# vj-epic-plan

以**一个 Epic（含若干 Story）为单元**生成实现计划（HOW）。

## 在工作流中的位置

```
vj-epic-story (WHAT: Epic/Story + 可执行 AC)
      ↓
vj-epic-plan  (HOW: 本 skill —— 人工 Review 主线 + epic 级共享设计 + 每 Story 执行 Appendix + task 文档)
      ↓
vj-work / run-epic (执行)
```

## 产出

`docs/tasks/plans/{date}-epic-{N}-{slug}-plan.md`，结构见 `epic-plan.template.md`。输出按两类读者组织——**人工只读 §4 共享设计（+ §0 审批门），其余给执行器 / 校验器**：

- **人工 review 主面**：§4 共享设计（ERD / 流程时序 / 模块边界 / 术语），§2 的已定决策内联进图（扫图 = 批准方向）；§0 是 thin 审批门，只列待拍板 `D-ID`（链 §2），不写散文摘要、不放 Review Checklist。
- **给机器看（不需散文润色）**：§1 范围、§2 决策真相源、§3 跨 Epic 契约、§5 API / Schema Delta、§6 Unit 概览与依赖 DAG，以及 Appendix（Triage 审计、复用锚点、每个 Unit 的 Files / Approach / Patterns / Test、并行波次、共享文件冲突点、风险与回滚、提交步骤）。
- **Unit 粒度**：每个 Story 映射为一个 Implementation Unit；Unit 是产品语义边界，不按前端 / 后端 / 数据库拆开。
- **跨 Epic 契约（§3 只填 Consumes）**：单一真相源 = catalog（`docs/project/api/`、`docs/project/data/`）。`Consumes` 由 Agent B 读 catalog 生成；本 Epic 对下游的契约写进 catalog（§5 Catalog Sync），**不在 plan 写 Provides 表**；跨切面不变量（R1.x）写进 `data/overview.md` / `api/conventions.md`。下游 epic 读 catalog，不翻旧 plan。
- **决策单一真相源**：完整论证只写在 `## 2. 决策与 AC 偏离`。技术方案与 Story AC 冲突时必须回改 AC 或显式审批，不允许静默替换验收口径。
- **模块化契约目录同步**：命中 API delta 时更新 `docs/project/api/conventions.md` + `docs/project/api/{module}.md`；命中 schema / persistence delta 时更新 `docs/project/data/overview.md` + `docs/project/data/{module}.md`。同步发生在 `vj-plan-review` 采纳修正之后，保证 catalog 与最终 plan 一致。旧 `api_spec.md` / `database_schema.md` 仅兼容读取。
- **task 文档（执行投影）**：Phase 5 plan 定稿后，在 `docs/tasks/work/epic-{N}-{slug}/` 生成 `_ledger.md` + 每 task 一份 7 段文档。默认 `1 Unit = 1 task`；只有依赖、文件隔离、局部验证和并行收益都清楚时才允许 `1 Unit → 多 task`，且必须生成 task DAG / 波次 / 冲突表。task done 不等于 Unit done，Story AC 闭环仍由 Unit 验收。续作 / 重跑整目录覆盖重写。

## 关键设计取舍

- **不 fork compound 的 ce-plan**：只借其 implementation-units / Provides-Consumes / 方向性设计思想，按 vj 轻量风格自包含实现，零插件耦合。
- **research 并行多代理**：Phase 2 优先并行派 design-context / upstream-contracts / codebase-scout 三个只读研究任务（模板见 `references/research-agents.md`）+ 条件性 `vj-learnings-researcher`；无 subagent 能力时顺序内联执行，仍保留三份结构化结果。
- **学习飞轮**：读端 `vj-learnings-researcher`（Phase 2 调用），写端 `vj-compound`（实现收尾后沉淀 `docs/solutions/`）。

## 文件

- `SKILL.md` — 5 Phase 工作流
- `epic-plan.template.md` — plan 输出模板
- `references/research-agents.md` — Phase 2 并行研究代理模板（design-context / upstream-contracts / codebase-scout）
- `references/task-doc.template.md` — Phase 5 生成的 per-task 7 段执行文档模板（与 vj-work 同步副本）
- `README.md` — 本文件
