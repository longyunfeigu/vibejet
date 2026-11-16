---
name: vj-compound
description: 把刚刚解决的问题 / 刚确立的决策沉淀为 docs/solutions/ 下的结构化学习文档（YAML frontmatter，可被 vj-learnings-researcher 检索）。用户说"沉淀这个""记录这次踩坑""compound 一下""把这个经验存下来"，或一段调试/决策/重构刚收尾时使用。
---

# vj-compound — 经验沉淀（写端）

趁上下文还新鲜，把刚解决的问题或刚定下的决策写成 `docs/solutions/` 下一份可检索的文档。
读端是 `vj-plan` 出计划时跑的 `scripts/scout.py`；两端共用
`references/schema.yaml` 这份 frontmatter 合同。

值得写：根因不显然的 bug；有"为什么不选 X"理由的架构/设计/选型决策；值得后来者遵循的约定或
工作流改进；重构中暴露的易踩坑。不值得写：拼写/格式/版本号修改；只对本次会话有意义的内容。

## 1. 收集

从当前会话收集，不做多 agent 考古：问题或决策是什么、可观察的症状或触发场景、根因或关键理由
（决策要写否决了什么）、怎么解决的、涉及哪些文件和层、可复用的模式或要避开的坑。用户给了提示
就以它为锚。信息不足以写出有用的条目时，问用户 1-2 个关键问题，不要编。

## 2. 分类与查重

按 `references/schema.yaml` 定 `track`（bug / knowledge）和最窄的 `problem_type`（knowledge 没有
更窄的值才用 `best_practice`）；目录按 `references/yaml-schema.md` 的 Category Mapping，
不存在就建。先用 `rg` 在 `docs/solutions/` 找标题或 tags 相近的条目：命中就刷新原条目
（增量补充，保留原 frontmatter 和初次 `date`，正文注明"更新于 YYYY-MM-DD"）；没命中再新建。

## 3. 写文档

文件名 `docs/solutions/<category>/<YYYY-MM-DD>-<kebab-slug>.md`。

frontmatter 严格按 `schema.yaml`：共用必填 `module`、`date`、`problem_type`、`component`、
`severity`；bug track 另需 `symptoms`、`root_cause`、`resolution_type`；可选 `applies_when`、
`related_components`、`tags`（小写连字符，最多 8 个）。数组项以 `` ` `` `[` `*` `&` `!` `|`
`>` `%` `@` `?` 开头或含 `: ` 时加双引号。enum 值必须精确匹配 schema。

正文：

```markdown
# <标题>
## 问题 / 背景
## 根因 / 关键洞察
## 解决 / 决策
## 否决的方案   <!-- 决策类必填，这是最有价值的部分 -->
- <方案> | <为什么不选>
## 复用 / 预防
```

不写真实 secrets、客户数据、业务资料原文，只记模式和结论。

## 4. 校验与报告

跑 `python3 .agents/skills/vj-compound/scripts/validate-frontmatter.py <文件>`，失败就按提示修。
`docs/solutions/README.md` 不存在时补一份一行说明（目录用途 + Category Mapping 链接）。
最后报告文件路径和一行摘要（track / problem_type / module）。
