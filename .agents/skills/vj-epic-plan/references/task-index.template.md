<!-- 机检合同速查（plan_lint 硬规则）：
     · Epic Execution Checklist 用 C-ID/Severity/Applies to/Invariant/Source 五列表：C-ID 唯一、
       Severity ∈ blocking|advisory、Applies to 写 global 或真实 T-ID、每个 task 必须被 ≥1 条覆盖、
       Invariant/Source 非空
     · index 引用的每个 T 编号必须有对应 T 文档文件；孤儿 T 文档报 WARNING
     · verify.sh：每个 Unit 有 unit_U{n} 函数且接进 ALL_UNITS（漏接 = all 静默漏跑，ERROR）
     · 表格表头后必须紧跟 GFM 分隔行；不得残留模板占位符 -->

# Epic {N} {name} Task Index

**Human review pack:** `docs/work/plans/{date}-epic-{N}-{slug}/README.md`  
**Design:** `docs/work/plans/{date}-epic-{N}-{slug}/design.md`  
**Decisions:** `docs/work/plans/{date}-epic-{N}-{slug}/decisions.md`  
**Execution policy:** fast / strict

> This index is the execution entrypoint for `vj-work`. Task docs are execution projections, not truth sources. Story AC owns observable behavior; approved `decisions.md` entries own design choices; `docs/project/api|data|ui/` owns exact contracts; `design.md` owns delta rationale and cross-layer invariants. A cross-dimension conflict must STOP for source correction; it must not be resolved by silently choosing one document.
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

<!-- 本 epic 的高优先级约束。每条声明 severity、适用 task 与 source；vj-work 只把 global 或命中
     当前 T-ID 的行注入执行 prompt，orchestrator/reviewer 读完整表。plan_lint R14 校验 task 覆盖。
     不设固定条数，不把无 source 的泛泛规则塞进来。 -->

| C-ID | Severity | Applies to | Invariant | Source |
|------|----------|------------|-----------|--------|
| C01 | blocking | T001 | {具体、可执行的约束} | `{path 或 doc#anchor:行号}` |

## Verification

Unit verification entrypoint (materialized from Story AC `验证:` commands; on conflict the story wins):

```bash
bash docs/work/tasks/epic-{N}-{slug}/verify.sh {U-ID}   # one unit
bash docs/work/tasks/epic-{N}-{slug}/verify.sh all      # whole epic
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
