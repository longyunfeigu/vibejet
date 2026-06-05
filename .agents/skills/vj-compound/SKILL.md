---
name: vj-compound
description: 把刚刚解决的问题 / 刚确立的决策沉淀为 docs/solutions/ 下的结构化学习文档（YAML frontmatter，可被 vj-learnings-researcher 检索）。用户说"沉淀这个""记录这次踩坑""compound 一下""把这个经验存下来"，或一段调试/决策/重构刚收尾时使用。
---

# vj-compound — 团队知识沉淀（写端）

把**刚解决的问题**或**刚确立的决策**，趁上下文还新鲜，写成 `docs/solutions/` 下一份结构化、可检索的学习文档。它是学习飞轮的**写端**；读端是 `vj-learnings-researcher` agent（被 `vj-epic-plan` / `do-story` / `review` 调用）。两者共用同一份 frontmatter 契约：`references/schema.yaml`。

**核心理念**：每解决一个非平凡问题、每做一个有理由的取舍，就让团队的知识"复利"一次——下次有人碰到相似场景，检索即得，不必重新踩坑。

## 何时用 / 何时不用

**用**：一个 bug 被定位并修复（尤其根因不显然）；一个架构/设计/选型决策定下来且有"为什么不选 X"的理由；一个约定/工作流改进值得让后来者遵循；一次重构暴露了易踩的坑。

**不用**：纯拼写/格式/依赖号修改；只对本次会话有意义、无复用价值的内容；已在 `docs/solutions/` 有几乎相同条目（改用 §4 的刷新而非新建）。

## 输入

```
vj-compound                 # 沉淀本会话最近解决的问题/决策
vj-compound [一句话上下文]    # 额外提示要沉淀什么
```

## 工作流（4 Phase）

### Phase 1：收集上下文

从**当前会话**收集要沉淀的素材（不开重型多 agent 考古，本会话上下文优先）：

- 问题/决策是什么？可观察症状或触发场景是什么？
- 根因 / 关键洞察是什么？（bug：技术根因；决策：为什么这样、否决了什么）
- 怎么解决 / 怎么定的？涉及哪些文件、模块、层（domain/application/infrastructure/api/frontend）？
- 有什么可复用的模式、或后来者要避开的坑？

若用户给了上下文提示，以它为锚；否则回看本会话最近一段实质性工作。**信息不足以写出有价值的条目时，向用户问 1-2 个关键问题，不要硬编。**

### Phase 2：分类（决定 track + 目录）

按 `references/schema.yaml` 判定：

1. **track**：bug（缺陷/失败）还是 knowledge（实践/模式/决策/约定/工作流）。
2. **problem_type**：选**最窄**适用值（knowledge track 无更窄值时才用 `best_practice`）。
3. **目录**：按 `references/yaml-schema.md` 的 Category Mapping → `docs/solutions/<category>/`。目录不存在就建。

> 重复检查：先用 `rg` 在 `docs/solutions/` 找标题/tags 相近的已有条目。命中则走 §4 刷新；否则新建。

### Phase 3：写文档

文件名：`docs/solutions/<category>/<YYYY-MM-DD>-<kebab-slug>.md`（slug 取问题/决策的核心短语）。

**Frontmatter**（严格遵守 `references/schema.yaml`）：
- 共用必填：`module`、`date`、`problem_type`、`component`、`severity`
- bug track 另需：`symptoms`、`root_cause`、`resolution_type`
- knowledge track：上述 bug 字段可选；可加 `applies_when`
- 可选：`related_components`、`tags`（小写连字符，≤8）
- **YAML 安全**：数组项若以保留字符（`` ` `` `[` `*` `&` `!` `|` `>` `%` `@` `?`）开头或含 `: `，必须双引号包裹（见 yaml-schema.md）。

**正文结构**（简洁、面向"后来者能直接用"）：

```markdown
# <标题>

## 问题 / 背景
<可观察症状或决策触发场景；bug 给复现，决策给约束>

## 根因 / 关键洞察
<bug 的技术根因；或决策的核心理由>

## 解决 / 决策
<怎么修的 / 怎么定的。涉及文件用 repo 相对路径>

## 否决的方案 *(决策类必填，对齐 commit-trailer 的 Rejected)*
- <方案> | <为什么不选>

## 复用 / 预防
<后来者怎么用这条；要避开的坑；适用边界>
```

**敏感数据红线**（同 NFR 4.3）：不写真实 secrets、客户数据、业务资料/答题原文。只记模式与结论。

### Phase 4：校验 + 可发现性

1. **校验**：`python3 .agents/skills/vj-compound/scripts/validate-frontmatter.py <新文件路径>`，FAIL 则按提示修引号后重跑。
2. **可发现性**：确认 `docs/solutions/` 在 `CLAUDE.md` / `AGENTS.md` 的知识入口里被提及（让未来 agent 找得到）。若 `docs/solutions/README.md` 不存在，补一份一行索引说明本目录用途与 Category Mapping 链接。
3. **报告**：输出新建文件路径 + 一行摘要（track / problem_type / module）。

## §4 刷新已有条目（命中重复时）

不新建：读出原文件 → 增量补充新洞察/新坑 → 保留原 frontmatter（尤其 `date` 记初次，可加一行正文注明"更新于 YYYY-MM-DD"）→ 重跑校验。不要为了"看起来完整"重写无关字段。

## 常见错误

- ❌ 把只对本会话有意义的东西沉淀成"学习"——无复用价值就别写。
- ❌ frontmatter 用了 schema 之外的 enum 值——必须精确匹配。
- ❌ 决策类条目漏掉"否决的方案"——这是最有价值的部分。
- ❌ 写进敏感原文。
- ❌ 跳过 validate 脚本直接收工。

## 与其他组件的协作

```
（调试/决策/重构收尾） → vj-compound 写 docs/solutions/<category>/
                                     ↑ 同一份 schema.yaml 契约 ↓
              vj-learnings-researcher 读  ← vj-epic-plan / do-story / review 调用
```
