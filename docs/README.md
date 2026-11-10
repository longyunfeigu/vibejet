# vibejet Documentation

This directory is the documentation entry point for `vibejet`. Reusable platform knowledge
(architecture, AI workflow, review standards, long-lived technical decisions) lives under
`project/` and `reference/`; product intent for the application currently built on top of the
platform is quarantined under `product/` so the two never mix.

## Quick Navigation

| Area | Path | Purpose |
|------|------|---------|
| Project architecture | [project/architecture.md](project/architecture.md) | Foundation-library goals, DDD layering, capabilities, and extension rules |
| API conventions | [project/api/conventions.md](project/api/conventions.md) | Reusable REST envelope, error, pagination, and auth-boundary conventions |
| Data contracts | [project/data/README.md](project/data/README.md) | Current persistent schema documentation status |
| Product intent | [product/](product/) | PRD and product-specific intent for the app built on this platform |
| Reference guides | [reference/](reference/) | Repo-local workflow guides, review rules, and ADRs |
| Delivery workflow | [work/](work/) | Epic, Story, plan review pack, and task packet conventions |
| Solutions knowledge base | [solutions/](solutions/) | Solved problems and established decisions (written via `vj-compound`) |
| Archive | [archive/](archive/) | Historical/downstream product docs that are not current baseline requirements |
| AI workflow | [reference/guides/ai-workflow.md](reference/guides/ai-workflow.md) | Repo-local skill selection and implementation workflow |
| Review checklist | [reference/guides/review-checklist-python-fastapi.md](reference/guides/review-checklist-python-fastapi.md) | Pre-landing review risks for this FastAPI backend |

## Structure

```text
docs/
|- README.md
|- archive/
|- product/
|  `- README.md
|- project/
|  |- api/
|  |- data/
|  |- ui/
|  `- architecture.md
|- reference/
|  |- README.md
|  |- adrs/
|  |- guides/
|  `- research/
|- solutions/
`- work/
   |- README.md
   |- epics/
   |- plans/
   `- tasks/
```

## Ownership Rules

- Put current project facts under `docs/project/`.
- Put archived historical/downstream-product material under `docs/archive/`.
- Put durable technical decisions under `docs/reference/adrs/`.
- Put reusable workflow and review guidance under `docs/reference/guides/`.
- Put temporary execution plans under `docs/work/plans/`, and executable task packets plus
  execution records under `docs/work/tasks/`.
- Put solved-problem and decision learnings under `docs/solutions/` (written via `vj-compound`).
- Put product intent (PRD, personas, launch materials, product-specific research) under
  `docs/product/` — never under `docs/project/`, which holds only platform facts and
  code-facing contracts (`api/`, `data/`, `ui/`, `DESIGN.md`).

## Maintenance

Update this index whenever a top-level documentation file is added, moved, renamed, or promoted
from a temporary plan into long-lived guidance.
