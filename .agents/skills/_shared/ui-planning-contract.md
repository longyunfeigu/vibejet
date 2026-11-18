# UI 规划合同（设计方向用）

> 本文件是屏型判定和视觉方向双轨的真相源，给 `vj-mock-board`、`vj-design-md-matcher` 这类定设计方向的 skill 用。
> **计划不用这套术语**：`vj-plan` 里页面只用大白话写交互（主流程 / 备选 / 出错路径 + 状态），规则在
> `vj-plan/SKILL.md`「页面怎么交互」，不在这里。
> 分工：实现期出口闸（富度 R0–R4、工艺 C1–C5、A/B 轨截图审查）真相源 = `.claude/rules/frontend.md`；
> 样式 token 数值真相源 = `docs/project/DESIGN.md`。基座本身不带 `DESIGN.md`（它是具体产品的设计合同，新产品开始时生成）；没有时以 `frontend/src/index.css` 现有 token 为准，文中引用 DESIGN.md 各节的要求在有产品后才适用。

## 1. 屏型判定（每个 UI Screen 必判）

`front-of-house | operational | mixed`

| 屏型 | 默认命中 | 定位 |
|------|----------|------|
| front-of-house | login、signup、landing、onboarding、未登录/首个空首屏、营销页 | 承载产品身份与信任，默认 UI-critical |
| operational | dashboard、table-list、审核台、detail、form、settings、admin 后台 | 承载高频操作与数据密度 |

不确定时标 `⚠️ 推断`，在各 skill 的用户确认环节让用户定。

## 2. 双轨触发（先方向，后单屏）

- **产品/品牌方向轨（低频）**：`docs/project/DESIGN.md` 缺失/明显过期、品牌方向不清、
  front-of-house 屏无 golden reference、或用户要求整体视觉升级 → 先跑
  `vj-design-md-matcher`（产出 `DESIGN.md` + golden screens）。
  不得在 plan / story 文案里临时发明风格。
- **单屏体验轨（高频）**：方向源已稳定、只是新增/重做具体 Screen → 检查页面体验地图完整度；
  缺单屏目标/结构或状态覆盖 → 在计划的"页面怎么交互"里补齐（目标、主流程、备选/出错、要覆盖的状态）。
- 两轨可以都需要（如新产品第一次做登录页：先定 DESIGN.md/golden，再做单屏结构与状态）。

## 3. 复杂操作流

用户要连续走 2 步以上、中途有资格 / 余额 / 审核这类判断、有删除 / 提交这类不可轻易撤销的动作、或要能重试 / 撤销 /
返回时，把主流程、备选和出错路径都走一遍。

## 4. 屏型要求与禁止项（实现期截图验证用）

**front-of-house**（默认 UI-critical）：
- 必须写清：产品身份/品牌区、≥2 个价值点或信任点、视觉锚点、主 CTA 默认可操作态、
  错误/loading/disabled 三态
- 禁止：裸居中表单卡、左侧/背景大面积纯空白、只有表单无品牌概念
- 不得把"可提交表单"当完成标准；AC 必须包含"页面体验地图对齐 / 设计合同对齐 / 截图审查"类
  Browser 验证，不允许只断言表单字段存在

**operational**：
- 必须写清：主数据容器、工具条/筛选、统计或摘要、行/批量操作、loading/empty/error 三态、
  信息密度要求
- 禁止：孤立卡片堆、巨型录入框当主视觉、无主内容锚点（无数据表或无主内容锚）
- AC 至少一条 Browser 验证覆盖"主数据容器 + 工具条/筛选/三态之一存在"，
  不能只验证一个卡片或表单存在

## 5. 计划里怎么写页面

见 `vj-plan/SKILL.md`「页面怎么交互」：从哪进、主流程、备选路径、出错路径、要覆盖的状态，用大白话写，
每条路径和状态在验收清单里有一项。本文件的屏型、富度、禁止项由 `vj-work` 实现期按 `.claude/rules/frontend.md` 截图验证时使用。
