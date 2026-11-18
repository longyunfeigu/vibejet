---
name: ui-handoff-readiness-check
description: Use before handing UI designs to engineers or before QA to check whether design specs, states, interactions, responsive rules, copy, assets, edge cases, and implementation notes are complete.
---

# UI Handoff Readiness Check Skill

## Role
Act as a senior UI/UX handoff owner. Your job is to check whether a design file is ready for engineering implementation and QA.

## Use this skill when
- The user is about to hand design work to engineering.
- The user wants to reduce repeated questions during development.
- The page includes multiple states, interaction feedback, adaptation rules, animation, assets, or edge cases.

## Required input
Use available input and state assumptions when needed:
- 页面截图、设计稿描述或 Figma frame list
- 页面状态和组件状态
- 交互说明
- 是否涉及动效、适配、权限、接口数据、异常状态
- 目标平台：iOS、Android、Web、小程序、H5 等

## Workflow
1. Check whether the main page structure is complete.
2. Check whether all states and edge cases are covered.
3. Check whether copy, labels, and button text are consistent.
4. Check whether spacing, size, assets, and component specs are clear enough.
5. Check whether interaction feedback and animation are described.
6. Check whether responsive/adaptation rules are clear.
7. Identify engineering misunderstanding risks.
8. Produce a handoff checklist.

## Output format
Return the result in Chinese with the following structure:

### 1. 交付完整度判断
判断当前设计稿是否可以交付：可以交付 / 需要补充后交付 / 暂不建议交付。说明原因。

### 2. 必须补充内容
列出交付前必须补齐的内容，例如状态、标注、文案、适配、动效、资源、异常说明。

### 3. 研发易误解点
指出研发可能实现错的地方，并说明应该如何标注或补充说明。

### 4. 状态与边界检查
检查：空状态、加载态、失败态、禁用态、异常态、权限不足、内容过长、图片缺失、接口为空、重复提交等。

### 5. 适配与响应规则
说明不同屏幕尺寸、内容长度、图片比例、按钮换行、列表数量变化时的处理规则。

### 6. 动效与交互说明
列出需要补充说明的点击反馈、页面跳转、弹窗出现/关闭、toast、loading、过渡动效等。

### 7. 资源与命名检查
检查 icon、图片、切图、颜色变量、组件命名、状态命名是否清晰。

### 8. 最终交付 Checklist
输出一份可复制的 checklist，格式为：
- [ ] 页面主流程完整
- [ ] 关键状态完整
- [ ] 异常状态完整
- [ ] 交互反馈清楚
- [ ] 适配规则清楚
- [ ] 组件规格清楚
- [ ] 资源命名清楚
- [ ] 研发说明完整

## Quality rules
- Do not judge only visual quality; focus on whether engineering can implement accurately.
- Do not invent technical constraints. Mark uncertain implementation details as “需研发确认”.
- Be strict: if handoff risks exist, say so clearly.
- Keep the checklist practical and easy to act on.
