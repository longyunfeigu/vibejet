---
name: diff-aware-qa
description: 基于当前分支、工作区或指定 diff 推导受影响页面、路由和交互，执行 focused regression QA。适用于实现完成后的第二层质量检查，输出结构化问题报告、截图证据和剩余回归风险；默认使用 git diff + playwright-interactive，不负责 Story 验收闭环。
---

# diff-aware-qa

用于当前仓库的第二层 QA。

这个 skill 关注的是：**这次改动影响了哪些页面、路由、接口和相邻功能，是否引入了回归。**

它不是 `story-verify-fix` 的替代品。

- `story-verify-fix`
  - 回答当前 Story 自己是否通过验收，失败时是否需要继续修
- `diff-aware-qa`
  - 回答这次 diff 还可能影响了什么，哪里出现了回归或隐藏问题

## 适用场景

- 用户刚完成一个分支的实现，想做回归 QA
- 用户要求“像真人一样点一遍受影响页面”
- 用户想根据当前 diff 自动推导要测哪些路由或页面
- 用户希望输出结构化 QA 结果，而不是只说“我测过了”

## 不适用场景

- 当前任务还没有明确实现完成
- 用户要做 Story 验收或自动修复闭环，此时优先用 `story-verify-fix`
- 仓库没有运行中的应用，也无法确定启动方式或目标 URL
- 用户只是想 review 代码结构，不需要运行层 QA

## 默认范围

如果用户未指定范围，按以下顺序确定 diff 基线：

1. 当前分支相对 `origin/main`
2. 如果没有 `origin/main`，则使用本地 `main`
3. 如果都不可用，则使用当前工作区未提交改动

## 输入要求

优先从仓库和用户请求中自动提取；不足时再补最少信息。

至少识别以下信息：

- diff 范围
- 前端 Base URL
- 后端 Base URL
- 是否需要认证
- 用户特别关注的页面 / 路由 / 风险点

如果用户没有提供 URL，可以尝试从本地运行中的服务推断；仍然无法确定时再停下询问。

## 核心原则

1. diff 决定范围，不做无界全站探索。
2. 优先覆盖受影响页面，再覆盖相邻高风险页面。
3. 证据是必须的：截图、控制台错误、失败请求、复现步骤至少保留其一；严重问题最好同时保留多种证据。
4. 默认只读。发现问题后先报告，不自动修代码，除非用户明确要求继续修复。
5. 如果前端源码不存在，不要编造页面映射；改从运行中的应用、Story、设计图、导航结构和后端接口反推。

## Impact Mapping Heuristics

根据 diff 推导影响面时，优先使用这些规则：

- `backend/api/routes/*`
  - 直接映射为对应 HTTP 端点与相关页面流程
- `backend/application/services/*`
  - 映射为调用该服务的路由、关键用户流和状态变化
- `backend/infrastructure/repositories/*`
  - 映射为相关列表页、详情页、创建/更新流程和数据可见性
- 前端页面 / 组件 / 样式文件
  - 映射为直接页面和所有复用该组件或样式的相邻页面
- 共享布局、表格、表单、按钮、主题样式
  - 额外增加一层相邻回归检查
- 认证、权限、上传、下载、预签名、WebSocket、日志流
  - 默认提高风险等级

如果仓库缺少前端源码：

- 从运行中的页面导航结构推断
- 从 Story / 设计图 / 用户给定 URL 推断
- 从后端接口变化反推最可能受影响的页面

## Workflow

### Phase 0: Scope the Diff

1. 获取当前 diff 范围。
2. 列出 changed files。
3. 判断这是：
   - backend-only regression QA
   - full-stack regression QA
   - visual regression QA（如果改动涉及 UI / 样式 / 设计相关）

### Phase 1: Infer Affected Surfaces

输出一个简短影响面清单，至少包括：

- 改动文件
- 推导出的受影响页面 / 路由 / 接口
- 需要额外覆盖的相邻页面
- 重点风险点

如果无法把 diff 映射到任何可测试表面，应停止并报告原因，不要假装 QA。

### Phase 2: Ensure Targets Are Reachable

1. 确认前端和后端目标可访问。
2. 如果需要浏览器交互，优先使用 `playwright-interactive`。
3. 如果需要认证，先处理登录或会话导入。

如果目标不可访问：

- 优先尝试用户已提供的 URL 或本地常见端口
- 仍然失败则停止，不进入伪 QA

### Phase 3: Focused Regression Checks

对每个受影响表面至少执行：

- 打开页面或调用接口
- 检查是否正常加载
- 检查控制台错误或失败请求
- 检查关键操作链路
- 记录截图或关键证据

如果改动是交互型的，应执行端到端动作，而不是只看静态页面。

重点检查：

- 表单提交流程
- loading / empty / error / success 状态
- 数据列表和详情页一致性
- 共享组件在多个页面上的表现
- 认证与权限边界

### Phase 4: Adjacent Regression Checks

当 diff 命中这些高波及面时，额外检查相邻页面：

- 共享布局
- 共享表格 / 表单组件
- 样式 / 主题
- 路由守卫
- API client / request wrapper
- 权限与鉴权

这一阶段的目标不是全站巡检，而是控制成本地扩一圈，优先找最可能被顺手带坏的地方。

### Phase 5: Structured QA Report

输出必须至少包括：

- QA 范围
- changed files 数量
- 受影响页面 / 路由 / 接口
- 实际测试了哪些表面
- 发现的问题
- 每个问题的严重级别
- 证据
- 未覆盖或仍有风险的区域

建议格式：

```md
Diff-Aware QA: N findings

Scope:
- changed files: ...
- affected surfaces: ...

Findings:
- [severity] [surface] 问题
  Evidence: screenshot / console / request / repro

Residual risk:
- ...
```

## Evidence Rules

1. 每个问题至少有一个可复现证据。
2. 交互 bug 优先保留“操作前 + 操作后”证据。
3. 静态布局问题至少保留截图。
4. 控制台错误和失败请求属于有效问题，即使页面表面上还能继续使用。

## 与其他 skills 的关系

- `story-verify-fix`
  - 先确认 Story 自己通过，再用本 skill 看 diff 是否带来回归
- `review`
  - 本 skill 看运行层问题，`review` 看结构性问题；两者互补，不替代

推荐顺序：

1. 实现
2. `story-verify-fix`
3. `review`
4. `diff-aware-qa`

## 示例

对当前分支做默认 diff-aware QA：

```text
使用 diff-aware-qa，检查当前分支相对 main 的受影响页面和回归风险。
前端地址是 http://127.0.0.1:3000
后端地址是 http://127.0.0.1:8000
```

聚焦某个高风险页面：

```text
使用 diff-aware-qa，重点检查当前 diff 对文件列表页、上传页和权限相关流程的影响。
```

在 Story 验证后继续做第二层 QA：

```text
story-verify-fix 已通过。
继续使用 diff-aware-qa，检查这次改动是否影响了相邻页面或共享组件。
```
