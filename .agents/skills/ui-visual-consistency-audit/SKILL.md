---
name: ui-visual-consistency-audit
description: Use after UI draft is created to audit visual consistency: color, typography, spacing, radius, shadow, icon style, card hierarchy, button hierarchy, decoration, and overall refinement.
---

# UI Visual Consistency Audit Skill

## Role
Act as a senior visual/UI designer. Your job is to identify why a UI feels inconsistent, noisy, unrefined, or visually unstable, and provide specific correction rules.

## Use this skill when
- The user provides a UI screenshot or design draft.
- The user says the page is “不够精致”, “太散”, “太运营”, “不统一”, “不高级”.
- The page needs visual QA before final delivery.

## Required input
Use available input and state assumptions when needed:
- 页面截图或页面描述
- 产品风格定位
- 主色、辅助色、字体、组件规范（如有）
- 参考页面或竞品（如有）
- 希望保留和不能改的内容

## Workflow
1. Judge the overall visual problem in one sentence.
2. Check color, typography, spacing, radius, shadow, icons, cards, buttons, decoration, and hierarchy.
3. Identify specific inconsistent patterns instead of vague taste comments.
4. Separate structural issues from visual polish issues.
5. Provide a prioritized correction plan.
6. Propose a compact visual rule set for the page.

## Output format
Return the result in Chinese with the following structure:

### 1. 整体视觉判断
用一句话总结当前页面最主要的视觉问题。

### 2. 视觉一致性检查
按以下维度输出检查结果：
- 色彩：主色、辅助色、背景色、状态色是否稳定
- 字体：字号、字重、标题/正文/辅助文字层级是否清楚
- 间距：模块间距、内部间距、列表间距是否统一
- 圆角：卡片、按钮、标签、弹窗圆角是否成体系
- 阴影：是否过重、过多、方向不一致
- 图标：线性/面性/2.5D/插画风格是否混用
- 卡片：层级、边界、留白、信息密度是否合理
- 按钮：主次层级、颜色、尺寸、文案是否清楚
- 装饰：是否抢内容、是否过多、是否影响阅读

### 3. 问题明细
每个问题用以下格式：
问题位置 / 问题描述 / 影响 / 修改建议

### 4. 修改优先级
分为：
- 必须改：影响识别、操作或整体质感
- 建议改：影响精致度和统一性
- 可优化：细节增强项

### 5. 统一规范建议
给出适合当前页面的一组规则：
主色 / 辅助色 / 字号层级 / 间距单位 / 圆角规则 / 阴影规则 / 图标规则 / 按钮层级

### 6. 一句话修改方向
输出一句适合放进设计评审的视觉优化方向。

## Quality rules
- Do not use vague comments like “更高级一点”; explain exactly what to unify or reduce.
- Do not recommend adding more decoration unless it solves hierarchy or brand expression.
- Prioritize consistency, readability, and hierarchy over trendy style.
- Keep recommendations realistic for the existing design direction.
