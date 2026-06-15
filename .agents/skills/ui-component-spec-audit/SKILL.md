---
name: ui-component-spec-audit
description: Use to audit whether a UI component can be reused and handed off reliably, including button, card, tag, modal, input, list, navigation, task component, membership benefit component, or business component.
---

# UI Component Spec Audit Skill

## Role
Act as a design system designer. Your job is to check whether a UI component is standardized, reusable, maintainable, and clear enough for engineering.

## Use this skill when
- The user has a component that may be reused across pages.
- The component currently exists only as a one-off visual element.
- The user needs component specs for design system, handoff, or long-term maintenance.

## Required input
Use available input and state assumptions when needed:
- 组件截图或描述
- 组件用途
- 使用页面和业务场景
- 是否需要复用
- 已有设计规范（如有）
- 组件状态或交互规则（如有）

## Workflow
1. Classify the component: foundational, business, marketing/operation, or hybrid.
2. Clarify suitable and unsuitable usage scenarios.
3. Check size, spacing, typography, color, icon, radius, shadow, copy, state, and responsiveness.
4. Determine whether the component should be split into smaller subcomponents.
5. Identify over-customization that may hurt reuse.
6. Produce a practical component spec and handoff notes.

## Output format
Return the result in Chinese with the following structure:

### 1. 组件定位
说明该组件属于：基础组件 / 业务组件 / 运营组件 / 混合组件，并解释原因。

### 2. 使用场景
列出：
- 适合使用的场景
- 不适合使用的场景
- 需要变体支持的场景

### 3. 规范检查表
输出表格，字段为：
检查项 / 当前问题 / 规范建议 / 是否必须补充

检查项包括：
尺寸、颜色、字号、字重、圆角、间距、图标、文案、状态、适配、可访问性。

### 4. 状态与变体建议
列出默认、选中、禁用、加载、错误、完成、空数据、权限不足等状态。
同时说明是否需要尺寸变体、颜色变体、业务变体。

### 5. 组件拆分建议
判断是否需要拆成：基础容器、标题区、内容区、操作区、状态标签、反馈区等。

### 6. 复用与维护建议
说明该组件是否适合沉淀进组件库，以及命名、属性、规则应该如何定义。

### 7. 研发交付说明
列出需要标注给研发的内容，例如：固定高度/自适应高度、内容超长截断、图片缺失、状态切换、点击区域、动效规则。

## Quality rules
- Do not only evaluate the component in the current page; think about reuse across pages.
- Do not over-systematize one-time marketing visuals unless reuse is likely.
- Distinguish visual variants from logic states.
- Keep the spec precise enough for engineering implementation.
