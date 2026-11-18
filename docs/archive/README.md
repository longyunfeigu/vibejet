# Archive

This directory contains historical or downstream-product documentation that is
not part of the current `vibejet` baseline.

Archived documents preserve context and may contain stale paths that reflected
the repository layout when they were written. Do not treat them as current
architecture, API, schema, or implementation requirements unless they are
explicitly promoted back into `docs/project/`, `docs/reference/`, or
`docs/work/`.

## Index

- `skills/`：2026-11-16 精简时移出的 skill（22 个）。14 个在仓库内无流程引用（视觉风格包、出图转代码、上线检查、输出防截断、设计说明与交付规格审查）；7 个是通用审美规则和 UI 规划清单（design-taste-frontend、high-end-visual-design、ui-requirement-brief、ui-page-goal-structure、ui-state-coverage、ui-user-journey-audit、ui-visual-consistency-audit）——方向改由 `DESIGN.md` 具体值 + 截图独立评判承担，单屏结构与状态写在计划的"页面怎么交互"。放在这里不会被 Claude / Codex 加载；要恢复，把目录移回 `.agents/skills/` 即可。
- `skills/story-verify-fix` + `guides/story-verify-fix-design.md`：环境→验证→联调→视觉对齐→自动修复的流水线，已被 `vj-work`（起环境跑基线、页面做完即跑端到端、收尾回归）完整覆盖；计划外改动用 `diff-aware-qa`。
