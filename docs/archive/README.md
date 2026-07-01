# Archive

This directory contains historical or downstream-product documentation that is
not part of the current `vibejet` baseline.

Archived documents preserve context and may contain stale paths that reflected
the repository layout when they were written. Do not treat them as current
architecture, API, schema, or implementation requirements unless they are
explicitly promoted back into `docs/project/`, `docs/reference/`, or
`docs/tasks/`.

## Index

- `run-story-design.md` — 已废弃的 run-story 单入口 Story 编排设计（run-story/do-story
  skill 已于 2026-06 移除，Story 交付统一收敛到 `vj-epic-plan` → `vj-work`）。
- `story-plan-TEMPLATE.md` — 已废弃的 Story 级 plan 模板（Triage 8 问 + Flow A/B/C）。
  现行 plan 由 `vj-epic-plan` 按 Epic 生成 review pack，执行策略用 Execution Policy
  fast | strict 表达。
