---
title: "Epic {N} {name} Plan Entry"
type: epic-plan-legacy-stub
status: active
date: YYYY-MM-DD
epic_id: "{N}"
epic_source: docs/tasks/epics/epic-{N}-{slug}/epic.md
execution_policy: "fast | strict"
---

# Epic {N} {name} Plan Entry

This file is a compatibility entrypoint for tools or humans that still expect
`docs/tasks/plans/*-plan.md`.

The actual human-review plan is now a review pack directory:

- [README.md]({date}-epic-{N}-{slug}/README.md) — reviewer entry, known conflicts, reading path, catalog sync status
- [design.md]({date}-epic-{N}-{slug}/design.md) — problem model, glossary by scenario, module boundaries, flows, data/API design, risks
- [decisions.md]({date}-epic-{N}-{slug}/decisions.md) — D/ACD truth source, approved decisions, AC deviations, rejected alternatives

The execution entrypoint for `vj-work` is:

- `docs/tasks/work/epic-{N}-{slug}/task-index.md`

Do not add detailed design, task DAGs, file lists, or catalog content to this
legacy stub. Update the review pack and regenerate task docs instead.
