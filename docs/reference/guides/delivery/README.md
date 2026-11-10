# AI-Era Developer Delivery Workflow

**Status**: Active Standard
**Maintained by**: Development Team / Technical Lead
**Last Updated**: 2026-04-11

---

## What This Is

A quality assurance framework for AI-assisted development. Every feature and bug fix
goes through two mandatory phases before merging:

1. **Design phase** — understand the change, classify it, and produce a design document
2. **Checklist phase** — verify the implementation against a structured checklist

**Core principle**: Define what "done" looks like before coding starts — not after.

---

## The Four Skills

Use these skills via slash commands in the RD context:

| Skill | When to Use | Produces |
|-------|------------|---------|
| `/feature-design` | Before coding a new feature | Design doc in `docs/work/delivery/` |
| `/bug-fix-design` | Before fixing a bug | Design doc in `docs/work/delivery/` |
| `/feature-checklist` | After feature coding, before merging | Checklist report in `docs/work/delivery/` |
| `/bug-fix-checklist` | After bug fix coding, before merging | Checklist report in `docs/work/delivery/` |

Each skill runs step-by-step with a human confirmation gate between steps.

---

## Delivery Documents

All design documents and checklist reports are stored in:

```
docs/work/delivery/
├── [date]-feature-[slug]-design.md
├── [date]-feature-[slug]-checklist.md
├── [date]-bugfix-[slug]-design.md
└── [date]-bugfix-[slug]-checklist.md
```

Both documents must be linked in the PR description before merging.

---

## Feature Type Summary

| Type | Definition | Design Required | Checklist Size |
|------|-----------|----------------|----------------|
| T1 | Presentation only — styling, display, no logic change | No | 3–6 items |
| T2 | Logic extension — backward-compatible changes | Yes (lightweight) | 8–12 items |
| T3 | Conflicting change — breaks existing assumptions | Yes (standard) | 12–18 items |
| T4 | Architectural change — replaces core abstractions | Yes (full, tech lead approval) | 20+ items |
| T5 | Cross-cutting change — same small change across many files | Yes (standard) | 15–20 items |
| T6 | External dependency — library/provider upgrade or swap | Yes (lightweight) | 10–15 items |

---

## Reference Documents in This Folder

| Document | Purpose |
|----------|---------|
| [dev-process-and-bug-fix.md](./dev-process-and-bug-fix.md) | Full process standard — feature dev + bug fix steps, root cause analysis, side effect analysis, analogical investigation |
| [technical-design-spec.md](./technical-design-spec.md) | Technical design standard — when required, universal sections, level-specific templates T2–T6 |
| [test-case-requirements.md](./test-case-requirements.md) | Test case requirements — what must be tested per T1–T6, data migration testing, cross-feature interaction |
| [feature-type-classification.md](./feature-type-classification.md) | T1–T6 definitions, decision tree, classification output format |
| [checklist-generation-guide.md](./checklist-generation-guide.md) | How to generate checklists per type, item format, required categories |
| [checklist-templates/](./checklist-templates/) | Base templates for T1–T6 — starting point for checklist generation |

---

## Related Standards

- `AGENTS.md` (Commit & PR Guidelines)
- [Testing Guidelines](../common/testing.md)
- [Documentation Guidelines](../common/documentation.md)
