# docs/solutions — 团队知识沉淀库

结构化记录**已解决的问题**与**已确立的决策**，让团队知识"复利"：下次碰到相似场景，检索即得，不必重新踩坑。

- **写端**：`vj-compound` skill —— 把刚解决的问题/决策写成本目录下带 YAML frontmatter 的文档。
- **读端**：`vj-learnings-researcher` 研究子代理（模板见 `.agents/skills/vj-epic-plan/references/research-agents.md` Agent D）—— 被 `vj-epic-plan` / `vj-work` / `review` 在开工前调用，检索相关历史学习。
- **契约**：frontmatter schema 见 `.agents/skills/vj-compound/references/schema.yaml`（与 `yaml-schema.md`）。

## 目录结构（problem_type → 子目录，按需创建）

bug 类：`build-errors/` `test-failures/` `runtime-errors/` `performance-issues/` `database-issues/` `security-issues/` `ui-bugs/` `integration-issues/` `logic-errors/`

knowledge 类：`architecture-patterns/` `design-patterns/` `tooling-decisions/` `conventions/` `workflow-issues/` `developer-experience/` `documentation-gaps/` `best-practices/`

文件名：`<YYYY-MM-DD>-<kebab-slug>.md`。写后用 `python3 .agents/skills/vj-compound/scripts/validate-frontmatter.py <file>` 校验。
