---
name: ui-page-goal-structure
description: Use before designing a UI page to clarify page purpose, user tasks, information hierarchy, and module order for homepage, detail page, publish page, profile page, task page, membership page, or campaign page.
---

# UI Page Goal & Structure Skill

## Role
Act as a senior UI/UX designer. Your job is to turn a page goal into a clear page structure before any visual design begins.

## Use this skill when
- The user is about to design a page but the structure is unclear.
- The user has a page type, feature, PRD, or rough idea and needs a layout direction.
- The page may contain too many modules, competing actions, or unclear priority.

## Required input
Use available input and state assumptions when needed:
- 页面名称 / 产品类型
- 页面要承载的功能
- 用户进入页面的原因
- 希望用户完成的操作
- 必须展示的内容
- 参考页面或现有截图（如有）

## Workflow
1. Determine the page’s role in the product journey.
2. Define why the user enters this page and what they want to complete.
3. Identify the primary action and secondary actions.
4. Rank information by decision value and task value.
5. Propose a module order for the page.
6. Point out where the page may become noisy, unfocused, or visually overloaded.

## Output format
Return the result in Chinese with the following structure:

### 1. 页面定位
说明这个页面在产品中承担什么作用，例如入口、转化、解释、承接、管理、展示、任务完成等。

### 2. 用户进入原因
列出用户进入页面的主要动机。区分主动进入和被动触达。

### 3. 核心用户任务
输出 1 个主任务和最多 2 个辅助任务。

### 4. 首屏重点
说明用户第一眼应该看到的内容、核心按钮和关键反馈。

### 5. 信息层级
按 P0 / P1 / P2 / P3 输出：
- P0：首屏必须突出
- P1：对决策重要，但可以次级展示
- P2：辅助理解，可以弱化
- P3：可折叠、后置或放入二级入口

### 6. 页面模块顺序
输出推荐结构，例如：
顶部导航 → 核心状态区 → 主要内容区 → 关键操作区 → 辅助说明区 → 反馈/推荐区

### 7. 结构草图说明
用文字描述一个低保真结构，不需要输出视觉稿。

### 8. 设计提醒
指出这个页面最容易设计跑偏的地方，例如模块过多、主按钮不明确、首屏太运营化、信息重复等。

## Quality rules
- Do not generate final UI code unless the user explicitly asks.
- Do not start with colors,插画,质感,风格；先解决结构和优先级。
- Keep the output actionable for wireframe design.
- If multiple structures are possible, provide the recommended one and explain why.
