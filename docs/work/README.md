# Work Documentation

This directory contains in-flight delivery work: one plan document per piece of work.

## Structure

```text
docs/work/
|- README.md
`- plans/    # 每块工作一份 {date}-{slug}.md：整份给人审（固定的只有决定、验收、执行顺序三节），验收对应的测试、执行记录和验收说明也写在同一份里；整份 PRD 另有一份 epic-0 拆分总览
```

## Rules

- Put each plan under `docs/work/plans/{date}-{slug}.md` (written by `vj-plan`, executed by `vj-work`).
  A full product is planned one PRD Epic at a time, not all at once.
- Keep durable architecture and review guidance in `docs/reference/`; keep the current data / API / UI
  shape in `docs/project/` (updated by `vj-work` when a plan finishes).
- Promote reusable learnings from completed plans into `docs/solutions/`,
  `docs/reference/guides/`, or ADRs.
- Superseded execution assets are deleted (recoverable from git history) or moved to
  `docs/archive/`; do not keep tombstones in place.
