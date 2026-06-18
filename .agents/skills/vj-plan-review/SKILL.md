---
name: vj-plan-review
description: 为 vj-epic-plan 产出的 human review pack 做多视角独立审查——按 persona（human-design/一致性/可行性/范围/对抗/依赖并行/UI surface）审 README.md、design.md、decisions.md 与 task-index.md，汇总去重后自主判断采纳，并据采纳意见修正 review pack。在 vj-epic-plan 写盘后自动执行，用户可说"跳过审查"。也可手动 /vj-plan-review [review pack 路径 | legacy plan stub | epic 编号]。在 vj-epic-plan 之后、vj-work 之前。
---

# vj-plan-review — Epic Review Pack 多视角审查

在 `vj-epic-plan` 把 human review pack 写盘后，派多个 persona 从不同视角独立审一遍，自主判断采纳，并据此修正 review pack——让 human reviewer 先读得懂设计，让 `vj-work` 拿到的 task packet 不偏离设计真相源。

**工作流位置**：
```
vj-epic-story (WHAT) → vj-epic-plan (HOW) → 【vj-plan-review：本 skill】→ vj-work (执行) → vj-test → vj-compound
```

**设计取舍**：借 compound `ce-doc-review` 的「多 persona 审」理念（换视角求独立）+ vibejet 既有 `codex-review` 的「自主采纳→改文档→摘要」闭环，按 vj 轻量风格自包含实现，**零插件耦合**——persona 内联在本 skill 目录，不调任何 ce-* agent。裁剪掉 ce-doc-review 的重型机制：不做 safe_auto 静默改、不做跨轮记忆、不用 P0-P3 五级，findings 只用 vibejet 既有的 **Blocking/Non-blocking** 二分。

## 铁律

- **本 skill 被授权修正 review pack**——这正是它的职责，与 vj-epic-plan「执行期不改 review pack」不冲突（那是给 vj-work 的约束）。但**只改 `README.md` / `design.md` / `decisions.md` / `task-index.md` 与必要的 legacy stub 指针**，不碰 `epic.md`（WHAT 真相源）与 Story AC。
- **persona 只读**：审查、确认事实（可 Glob/Grep/Explore），**不改任何文件**；改 review pack 由编排器在主上下文统一执行。
- **自主采纳，但重大项设闸**：Blocking 默认采纳；命中 **AC 偏离 / 范围变化 / 需回改 epic.md** 的改动不静默落，列给用户确认（`adopt_mode: auto-with-gate`）。
- **不重审上游已审的**：PRD/架构/API/数据模型由 codex-review 审过；本 skill 只审 vj-epic-plan 特有的 HOW（问题建模、设计可读性、决策、Unit、DAG/波次、契约投影）。
- **审查对象是文档，不是代码**：不实现、不跑测试。代码评审在 vj-work 之后。

## 输入

```
vj-plan-review                                           # 自动触发(vj-epic-plan写盘后) / 空参取最新 review pack
vj-plan-review docs/tasks/plans/2026-06-01-epic-1-.../   # 指定 review pack 目录
vj-plan-review docs/tasks/plans/2026-06-01-epic-1-...-plan.md   # legacy stub，解析到 review pack
vj-plan-review epic-1                                    # 按 epic 编号定位
```

## 配置项

```yaml
epic_plan_reviewer:
  plans_dir: docs/tasks/plans/
  default: latest                                  # 未指定取最新 review pack 目录（含 README.md + design.md + decisions.md）
  personas: [human-design, coherence, feasibility, scope, adversarial, dependency, ui-surface]
  adopt_mode: auto-with-gate                       # Blocking自主；AC偏离/范围/改epic.md→问用户
  persona_defs: references/personas.md
  dispatch_template: references/subagent-template.md
```

---

## 工作流（5 Phase）

### Phase 1：定位 review pack

1. **自动触发**（vj-epic-plan 写盘后调用）：用刚写的 review pack 目录。
2. **手动**：按参数定位：
   - 目录路径：必须含 `README.md`、`design.md`、`decisions.md`。
   - legacy stub：读取 stub 中指向的 review pack 路径。
   - `epic-{N}`：在 `plans_dir` 下按最新匹配目录定位。
   - 空参：取 `plans_dir` 下最新 review pack 目录。
3. 读取 `README.md`、`design.md`、`decisions.md`；若 `task-index.md` 已生成，一并读取；若有 legacy stub，只读其指针，不把 stub 当设计真相源。
4. 读 `references/personas.md` 与 `references/subagent-template.md`。
5. 用户说"跳过审查"→ 直接结束，不派 persona。

### Phase 2：派 persona 审查

- 对 `personas` 列出的 7 个视角，各派一个**只读 persona**。有平台子代理原语时可并行；无并行能力的平台退化为主线程串行。
- 每个 persona 的 prompt = `subagent-template.md`，把对应 persona 段填入 `{persona}`、review pack 路径与拼接全文填入 `{review_pack_path}`/`{review_pack_content}`。
- persona 按输出契约返回 findings：`[序号] [Blocking|Non-blocking] 问题 | 证据(review pack 原文) | 建议修法`。
- 某 persona 失败/超时 → 用其余 persona 的结果继续，在摘要里记缺哪个视角；不因单个失败阻塞整轮。

### Phase 3：汇总去重

1. 汇总所有 findings。
2. **极简去重**：同一处被多个 persona 命中 → 合并为一条，标注命中的视角（多视角共指 = 信号强）。
3. 按 Blocking 在前、Non-blocking 在后排序。无 finding → 跳到 Phase 5 报"无需修正"。

### Phase 4：自主判断采纳 + 修正 review pack

逐条判断（对齐 codex-review Phase 3）：

| 级别 | 规则 |
|------|------|
| **Blocking** | 默认采纳。仅当明显是 persona 误判（未看到完整上下文）时跳过，并记跳过原因。 |
| **Non-blocking** | 逐条评估：确实提质/防歧义 → 采纳；纯风格 / 与项目约定冲突 → 跳过。 |

**重大项设闸**（`auto-with-gate`）：采纳后的改动若触及 **AC 偏离、范围变化、或需回改 `epic.md`**，**不静默改**——用平台阻塞提问工具（Claude Code：`AskUserQuestion`；无则编号选项）列给用户确认后再落。其余改动直接落。

- **改 review pack**：把采纳的建议应用到对应文件，每处标注来源注释 `<!-- vj-plan-review: applied [persona/序号] -->`。如果只是补清楚术语、模块理由、流程图、决策表、禁止依赖或 reviewer checklist，直接改 `design.md` / `decisions.md` / `README.md`。
- **dependency 视角的特殊处理**：若 `task-index.md` 与 `epic.md` 的 `**依赖**:` 行不一致——review pack 抄错 → 直接改 `task-index.md` / README execution sketch 对齐 epic.md；review pack 推导出更优依赖（epic.md 该改）→ 属重大项，走闸给用户，不静默改 epic.md。
- **human-design 视角的特殊处理**：如果 finding 是“读者无法建立心智地图”，优先改 `design.md` 的叙事结构，而不是把更多执行清单塞进 README；如果需要具体执行粒度，只在 `task-index.md` 或 task docs 投影。

### Phase 5：输出摘要

```
vj-plan-review 完成（N 条 finding，X Blocking，Y Non-blocking；视角：human-design/coherence/feasibility/scope/adversarial/dependency/ui-surface）

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

修正后告知 review pack 路径与改动文件，提示下一步：`vj-work` 执行。

## 不做什么（边界）

- 不审 PRD/架构/API/数据模型全量正确性（那是 codex-review 的活）；只审本 Epic 引入的 delta 是否被 review pack 讲清楚、投影到 catalog。
- 不改 epic.md / Story AC（重大项走闸由用户定）。
- 不做 safe_auto 静默改、不做跨轮记忆、不用 P0-P3 分级、不做交互式逐条 walkthrough。
- 不实现、不跑测试。
