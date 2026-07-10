# Epic {N} {name} Task Index

**Human review pack:** `docs/tasks/plans/{date}-epic-{N}-{slug}/README.md`  
**Design:** `docs/tasks/plans/{date}-epic-{N}-{slug}/design.md`  
**Decisions:** `docs/tasks/plans/{date}-epic-{N}-{slug}/decisions.md`  
**Execution policy:** fast / strict

> This index is the execution entrypoint for `vj-work`. Task docs are execution projections, not truth sources. If a task conflicts with Story AC, catalog, `design.md`, or `decisions.md`, STOP and report.
>
> task done != Unit done. Unit done requires all sibling tasks plus Story AC / Unit Verification.
>
> Execution records (status, change narratives, verification results) live in `_ledger.md`
> (append-only, written by `vj-work`). Task docs in this directory may be regenerated wholesale.

## Required Gates

- review:
- migration/backfill:
- screenshot/browser:
- catalog sync:

## Epic Execution Checklist

<!-- 10-15 条本 epic 的高优先级硬约束。vj-work 会把本节原样注入每个 subagent prompt——
     这是执行者不全文读 guideline / DESIGN.md 的前提。每条必须具体、可执行、带 source pointer
     （plan_lint R14 机检兜底）；无 source pointer 的泛泛规则不得进入。只列本 epic 容易写错且
     影响质量的约束，不追求完整规范；执行中碰到清单外风险面时按 source pointer 展开原文。 -->

1. {约束} — Source: `{path 或 doc#anchor:行号}`

## Verification

Unit verification entrypoint (materialized from Story AC `验证:` commands; on conflict the story wins):

```bash
bash docs/tasks/work/epic-{N}-{slug}/verify.sh {U-ID}   # one unit
bash docs/tasks/work/epic-{N}-{slug}/verify.sh all      # whole epic
```

## Unit DAG

```mermaid
graph LR
```

## Task DAG / Waves

<!-- 并行是一等编排目标：barrier 收最窄、fan-out 尽量宽，避免无必要的线性链。
     同 Wave 且 Write set isolated? = yes 的 task，vj-work 默认并行派发。
     相邻小 task（同 lane、预计 diff <150 行、共享 pattern）在 Batch 列标同一组名，
     vj-work 会合并成一次 subagent 派发（Unit 验收边界不变）；无合批则留空。 -->

| Wave | Tasks | Units | Depends on | Write set isolated? | Batch | Done signal |
|------|-------|-------|------------|---------------------|-------|-------------|
| | | | | | | |

## Execution Lanes / Frontend Composition Waves

<!-- 前端 Epic 必填；纯后端 Epic 删除本节。每个 Screen 的完整合同住对应 task doc 的 Screen context 注入块与 docs/project/ui/ catalog；本表只承载 lane 级编排。 -->

| Lane | Wave | Scope | Start condition | Done signal |
|------|------|-------|-----------------|-------------|
| contract / backend-api-capability / frontend-composition / e2e-polish | | | {该 Screen 依赖的 API/状态/数据合同稳定条件} | |

## Barrier / Owner Tasks

| Task | Type | Shared output / files | Unlocks | Done signal |
|------|------|-----------------------|---------|-------------|
| | | | | |

## Unit to Task Mapping

<!-- Unit 拆多 task 时，在 Tasks 列给收口 task 标 `*`（如 T003, T005*）：
     收口 task 负责跑 `verify.sh {U-ID}` 完成 Unit 级验证。单 task Unit 自身即收口。 -->

| Unit | Story | Tasks | Unit done signal |
|------|-------|-------|------------------|
| | | | |

## Shared File Coordination

| File | Tasks | Handling |
|------|-------|----------|
| | | |

## Tasks

- [T001 ...](T001-....md)
