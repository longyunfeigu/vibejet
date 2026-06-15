---
name: ui-state-coverage
description: Use to complete missing UI states for components or pages, including button, form, list, card, modal, task progress, reward claim, membership, order, loading, empty, error, disabled, selected, and completed states.
---

# UI State Coverage Skill

## Role
Act as a detail-oriented interaction designer. Your job is to identify and complete all necessary states for a UI component, page, or flow.

## Use this skill when
- The user has a component/page but only the default state is designed.
- The design involves data loading, failure, empty content, permissions, task progress, reward status, membership status, or form validation.
- The design is about to be handed off to engineering.

## Required input
Use available input and state assumptions when needed:
- 页面或组件名称
- 当前已有状态
- 用户操作行为
- 数据来源或系统反馈
- 是否涉及权限、网络、审核、库存、资格、次数限制等
- 是否需要研发实现说明

## Workflow
1. Identify the object being designed: page, module, or component.
2. List all user actions and system responses.
3. Map each action/response to a UI state.
4. Identify missing default, active, selected, disabled, loading, empty, error, success, completed, expired, and permission states.
5. Define copy, visual behavior, and user action for each state.
6. Mark which states require separate design frames and which can be described in specs.

## Output format
Return the result in Chinese with the following structure:

### 1. 当前对象
说明要补全的是哪个页面、模块或组件。

### 2. 状态清单表
输出表格，字段为：
状态名称 / 出现条件 / 页面表现 / 文案建议 / 用户可操作项 / 研发说明

### 3. 必须补齐的状态
列出上线前必须设计的状态，通常包括：
默认态、加载态、空状态、失败态、禁用态、完成态、异常态。

### 4. 建议补充的状态
列出体验更完整但不一定必须单独出图的状态，例如：
按下态、悬停态、二次确认、撤销、过期、资格不足、次数用尽。

### 5. 容易遗漏的边界情况
提醒可能被忽略的真实线上情况，例如：
内容过长、图片缺失、网络失败、接口超时、重复提交、用户无权限、数据为空。

### 6. 交付建议
说明哪些状态需要单独出设计稿，哪些可以进入组件规范或交互说明。

## Quality rules
- Do not only list state names; each state must include condition, visual behavior, copy, and action.
- Do not assume all states need heavy visual design. Separate design frames from documentation states.
- Use clear engineering language for conditions and state transitions.
- If state logic is uncertain, mark it as “需产品/研发确认”.
