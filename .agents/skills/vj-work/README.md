# vj-work

消费 `vj-epic-plan` 产出的 **epic 实现计划**，把它落地成已实现、已验证、已记录的代码。

## 位置

```text
vj-epic-story (WHAT)
      ↓
vj-epic-plan  (HOW: 实现计划 + task 文档 + Unit/Screen 波次)
      ↓
vj-work       (执行: auto/fast/strict + worktree + Verification + Screen composition)
      ↓
vj-compound   (可选沉淀)
```

## v2 核心

`vj-work` v2 默认使用 `execution_mode: auto`：

- **fast path**：普通任务默认路径。最小上下文、Unit Context Packet、worktree 隔离、Verification 驱动、final-only 结果记录；若执行 worktree 需要读取未提交 task/context 文件，会自动做 docs-context commit，不走审批。
- **strict path**：高风险任务路径。审批门、逐 Unit 文档/ledger、逐 Unit commit、完整 UI QA、完整 review/traceability。
- **auto**：命中 auth / permission / migration / public API / security / transaction / app shell / 大 diff / 用户要求审计等 strict trigger 时自动 strict，否则 fast。

## 三大核心能力

1. **Execution Context**：Phase 1 生成 `_execution_context.md`，把 layer skill / DESIGN.md / API / data / UI catalog 约束压成可回溯 checklist 和每个 Unit 的 Context Packet。Checklist 不是完整规范，所有条目必须带 source pointer。
2. **Verification 驱动执行**：每个 Unit 的 `Verification` 是 done signal。fast 和 strict 都不能跳过真实验证。
3. **Screen-first 前端执行**：前端 Epic 消费 task docs / `_execution_context.md` 中的 Screen context 与 `docs/project/ui/` catalog，先稳定对应 Screen 的 API / 状态 / 数据合同，再按 Screen/Route 整体实现 UI，避免按 Story 拼页面。
4. **风险触发质量门**：UI QA、test-first、System-Wide 检查、review 和 per-unit 记录按风险触发；高风险保留严格路径，普通任务不背审计型固定成本。

## Subagent 原则

**默认每个 task 派一个自包含 subagent 执行**（orchestrator 上下文卫生：主 session 只编排与审计，重活下沉子代理）。依赖型/共享文件 task 共享同一执行 worktree 串行派发（serial-isolation）；只有写集无交集且合同稳定的同波次 task 才用独立 worktree 并行（parallel-isolation）。inline 执行仅限运行时不支持 subagent、task trivial、或上下文已加载过半三种情况，须记录原因。

subagent 任务必须自包含：即使运行时支持继承上下文，也必须显式传 review pack 目录、task doc + task-index path、`_execution_context.md` path、Unit ID、Unit/Task Context Packet、write scope、Verification 和 return contract。若是 UI task，还必须传 Screen ID、Route、Primary Job、Covered Units、API-for-UI 和 Screen done。

## 文件

- `SKILL.md` — v2 执行工作流。
- `references/execution-context.template.md` — `_execution_context.md` 模板。
- task 文档模板不在本目录：唯一副本是 `.agents/skills/vj-epic-plan/references/task-doc.template.md`（回退生成时读它）。
- `README.md` — 本文件。
