# vibejet Documentation

This directory is the documentation entry point for `vibejet`. Keep it focused on reusable
platform knowledge: architecture, AI workflow, review standards, execution plans, and long-lived
technical decisions.

## Quick Navigation

| Area | Path | Purpose |
|------|------|---------|
| Project architecture | [project/architecture.md](project/architecture.md) | Foundation-library goals, DDD layering, capabilities, and extension rules |
| Reference guides | [reference/](reference/) | Repo-local workflow guides, review rules, and ADRs |
| Task workflow | [tasks/](tasks/) | Epic, Story, kanban, and implementation plan conventions |
| AI workflow | [reference/guides/ai-workflow.md](reference/guides/ai-workflow.md) | Repo-local skill selection and implementation workflow |
| Review checklist | [reference/guides/review-checklist-python-fastapi.md](reference/guides/review-checklist-python-fastapi.md) | Pre-landing review risks for this FastAPI backend |

## Structure

```text
docs/
|- README.md
|- project/
|  `- architecture.md
|- reference/
|  |- README.md
|  |- adrs/
|  |- guides/
|  |- manuals/
|  `- research/
`- tasks/
   |- README.md
   |- epics/
   `- plans/
```

## Ownership Rules

- Put current project facts under `docs/project/`.
- Put durable technical decisions under `docs/reference/adrs/`.
- Put reusable workflow and review guidance under `docs/reference/guides/`.
- Put temporary execution plans under `docs/tasks/plans/`.
- Keep product-specific PRDs, launch materials, and downstream application workflows out of this
  base library unless they describe reusable platform behavior.

## Maintenance

Update this index whenever a top-level documentation file is added, moved, renamed, or promoted
from a temporary plan into long-lived guidance.
