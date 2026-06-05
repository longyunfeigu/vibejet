---
name: vj-plan-review
description: 为 vj-epic-plan 产出的 epic 实现计划做多视角独立审查——并行派 persona 子代理（一致性/可行性/范围/对抗/依赖并行）各审一个视角，汇总去重后由 Claude 自主判断采纳，并据采纳意见修正 plan 文档。在 vj-epic-plan 写盘后自动执行（取代 epic-plan 的 codex-review），用户可说"跳过审查"。也可手动 /vj-plan-review [plan路径]。在 vj-epic-plan 之后、vj-work 之前。
---

# vj-plan-review — Epic 计划多视角审查

在 `vj-epic-plan` 把 plan 写盘后，派多个 persona 子代理从不同视角独立审一遍，自主判断采纳，并据此修正 plan——让进入 `vj-work` 执行的 plan 先过一道独立质量门。

**工作流位置**：
```
vj-epic-story (WHAT) → vj-epic-plan (HOW) → 【vj-plan-review：本 skill】→ vj-work (执行) → vj-test → vj-compound
```

**设计取舍**：借 compound `ce-doc-review` 的「多 persona 并行审」理念（换视角求独立）+ vibejet 既有 `codex-review` 的「自主采纳→改文档→摘要」闭环，按 vj 轻量风格自包含实现，**零插件耦合**——persona 内联在本 skill 目录，不调任何 ce-* agent。裁剪掉 ce-doc-review 的重型机制：不做 safe_auto 静默改、不做跨轮记忆、不用 P0-P3 五级，findings 只用 vibejet 既有的 **Blocking/Non-blocking** 二分。

## 铁律

- **本 skill 被授权修正 plan**——这正是它的职责，与 vj-epic-plan「执行期不改 plan」不冲突（那是给 vj-work 的约束）。但**只改 plan 文档本身**，不碰 `epic.md`（WHAT 真相源）与 Story AC。
- **persona 子代理只读**：审查、确认事实（可 Glob/Grep/Explore），**不改任何文件**；改 plan 由编排器在主上下文统一执行。
- **自主采纳，但重大项设闸**：Blocking 默认采纳；命中 **AC 偏离 / 范围变化 / 需回改 epic.md** 的改动不静默落，列给用户确认（`adopt_mode: auto-with-gate`）。
- **不重审上游已审的**：PRD/架构/API/数据模型由 codex-review 审过；本 skill 只审 epic-plan 特有的 HOW（决策、Unit、DAG/波次、契约）。
- **审查对象是 plan，不是代码**：不实现、不跑测试。代码评审在 vj-work 之后。

## 输入

```
vj-plan-review                         # 自动触发(vj-epic-plan写盘后) / 空参取最新 plan
vj-plan-review docs/tasks/plans/2026-06-01-epic-1-...-plan.md   # 指定 plan
vj-plan-review epic-1                  # 按 epic 编号定位
```

## 配置项

```yaml
epic_plan_reviewer:
  plans_dir: docs/tasks/plans/
  default: latest                                  # 未指定取最新 *-plan.md
  personas: [coherence, feasibility, scope, adversarial, dependency]
  adopt_mode: auto-with-gate                       # Blocking自主；AC偏离/范围/改epic.md→问用户
  persona_defs: references/personas.md
  dispatch_template: references/subagent-template.md
```

---

## 工作流（5 Phase）

### Phase 1：定位 plan

1. **自动触发**（vj-epic-plan 写盘后调用）：用刚写的那份 plan。
2. **手动**：按参数定位；空参取 `plans_dir` 下最新 `*-plan.md`。读全文。
3. 读 `references/personas.md` 与 `references/subagent-template.md`。
4. 用户说"跳过审查"→ 直接结束，不派代理。

### Phase 2：并行派 persona 子代理

- 对 `personas` 列出的 5 个视角，各派一个**只读子代理**。用平台子代理原语（Claude Code：`Agent`/`Task`，对标本仓库 `vj-learnings-researcher` 的派发先例；无并行能力的平台退化为串行）。
- 每个代理的 prompt = `subagent-template.md`，把对应 persona 段填入 `{persona}`、plan 路径与全文填入 `{plan_path}`/`{plan_content}`。
- 子代理按输出契约返回 findings：`[序号] [Blocking|Non-blocking] 问题 | 证据(plan原文) | 建议修法`。
- 某代理失败/超时 → 用其余代理的结果继续，在摘要里记缺哪个视角；不因单个失败阻塞整轮。

### Phase 3：汇总去重

1. 汇总所有 findings。
2. **极简去重**：同一处被多个 persona 命中 → 合并为一条，标注命中的视角（多视角共指 = 信号强）。
3. 按 Blocking 在前、Non-blocking 在后排序。无 finding → 跳到 Phase 5 报"无需修正"。

### Phase 4：自主判断采纳 + 修正 plan

逐条判断（对齐 codex-review Phase 3）：

| 级别 | 规则 |
|------|------|
| **Blocking** | 默认采纳。仅当明显是 persona 误判（未看到完整上下文）时跳过，并记跳过原因。 |
| **Non-blocking** | 逐条评估：确实提质/防歧义 → 采纳；纯风格 / 与项目约定冲突 → 跳过。 |

**重大项设闸**（`auto-with-gate`）：采纳后的改动若触及 **AC 偏离、范围变化、或需回改 `epic.md`**，**不静默改**——用平台阻塞提问工具（Claude Code：`AskUserQuestion`；无则编号选项）列给用户确认后再落。其余改动直接落。

- **改 plan**：把采纳的建议应用到 plan 文档，每处标注来源注释 `<!-- vj-plan-review: applied [persona/序号] -->`。
- **dependency 视角的特殊处理**：若 DAG 与 `epic.md` 的 `**依赖**:` 行不一致——plan 抄错（plan 错）→ 直接改 plan 对齐 epic.md；plan 推导出更优依赖（epic.md 该改）→ 属重大项，走闸给用户，不静默改 epic.md。

### Phase 5：输出摘要

```
vj-plan-review 完成（N 条 finding，X Blocking，Y Non-blocking；视角：coherence/feasibility/scope/adversarial/dependency）

✅ 已采纳（M 条）：
[1] [Blocking] 问题 → 已修正（§位置）
...
⏭️ 已跳过（K 条）：
[2] [Non-blocking] 问题 → 跳过原因
...
⏸️ 待你确认（重大项，未落）：
[5] [Blocking] 需回改 epic.md 依赖行 → 已问/待答
...
（如有视角失败）⚠️ 未覆盖视角：dependency（代理超时）
```

修正后告知 plan 路径，提示下一步：`vj-work` 执行。

## 不做什么（边界）

- 不审 PRD/架构/API/数据模型（那是 codex-review 的活）；不审代码（vj-work 之后）。
- 不改 epic.md / Story AC（重大项走闸由用户定）。
- 不做 safe_auto 静默改、不做跨轮记忆、不用 P0-P3 分级、不做交互式逐条 walkthrough。
- 不实现、不跑测试。
