# Work Documentation

This directory contains in-flight delivery assets: Epic/Story intent, plan review packs, and
task packets with their execution records.

## Structure

```text
docs/work/
|- README.md
|- epics/    # Epic/Story 意图与验收标准（what/why + AC）
|- plans/    # Epic plan review packs（README / design / decisions，给人审）
`- tasks/    # task packets + 执行记录（task-index、T*.md、verify.sh、_ledger 等，给 vj-work 执行）
```

## Rules

- Put active Epic and Story files under `docs/work/epics/`.
- Put plan review packs under `docs/work/plans/{date}-epic-{N}-{slug}/`.
- Put task packets and execution records under `docs/work/tasks/epic-{N}-{slug}/`; task docs are
  pure projections of the plan (safe to regenerate), while `_ledger.md` / test reports carry
  execution state.
- Keep durable architecture and review guidance in `docs/reference/`.
- Promote reusable learnings from completed plans into `docs/solutions/`,
  `docs/reference/guides/`, or ADRs.
- Superseded execution assets are deleted (recoverable from git history) or moved to
  `docs/archive/`; do not keep tombstones in place.
