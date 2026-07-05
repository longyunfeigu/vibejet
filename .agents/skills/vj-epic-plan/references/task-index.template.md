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

| Wave | Tasks | Units | Depends on | Write set isolated? | Done signal |
|------|-------|-------|------------|---------------------|-------------|
| | | | | | |

## Execution Lanes / Frontend Composition Waves

<!-- 前端 Epic 必填；纯后端 Epic 删除本节。字段与 vj-work execution-context.template.md 的 Lane 表对齐。 -->

| Lane | Wave | Scope | Start condition | Done signal |
|------|------|-------|-----------------|-------------|
| contract / backend-api-capability / frontend-composition / e2e-polish | | | {该 Screen 依赖的 API/状态/数据合同稳定条件} | |

## Barrier / Owner Tasks

| Task | Type | Shared output / files | Unlocks | Done signal |
|------|------|-----------------------|---------|-------------|
| | | | | |

## Unit to Task Mapping

| Unit | Story | Tasks | Unit done signal |
|------|-------|-------|------------------|
| | | | |

## Shared File Coordination

| File | Tasks | Handling |
|------|-------|----------|
| | | |

## Tasks

- [T001 ...](T001-....md)
