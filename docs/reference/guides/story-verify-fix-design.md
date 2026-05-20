# Story Verify-Fix Skill Design

## 1. Goal

设计一个仓库专用的 `story-verify-fix` workflow，使 AI 能围绕一个 Story 执行如下闭环：

1. 读取 Story、验收标准和设计参考
2. 启动后端与可选前端
3. 执行 Story 级验证
4. 如果有 UI 设计图，执行视觉对齐检查
5. 发现问题后修改代码并重试
6. 最终输出“通过 / 未通过 + 证据 + 剩余风险”

这不是通用 QA skill，而是一个 **Story-driven full-stack verify-fix harness**。

---

## 2. Why This Skill

当前仓库已经具备：
- Story / Epic 文档
- DDD 分层约束
- `story-reference-impl` 这种“先研究后实现”的设计型 workflow
- `docs/reference/guides/review-checklist-python-fastapi.md` 这种审查型 checklist

但还缺“实现之后如何自动证明真的工作”的执行闭环。

`story-verify-fix` 要补的是：
- 后端 Story 验证
- 前后端联调验证
- 设计图对齐验证
- 自动修复循环

---

## 3. Scope

### In Scope

- 后端-only Story 验证
- 前后端联调 Story 验证
- Story 中存在设计参考图时的视觉对齐检查
- 按失败证据进行有限轮次的自动修复
- 最终生成结构化验证报告

### Out of Scope

- 任意站点的开放式 exploratory QA
- 像素级视觉回归平台
- 无边界地自动重构整个前后端工程
- 一键发版 / PR 自动化

---

## 4. Usage Scenarios

### Scenario A: Backend Story

示例：

```text
使用 story-verify-fix，处理 path/to/backend-epic.md#story-3.2
只启动后端，验证该 Story 的 API 和持久化行为
```

目标：
- 跑 API/集成验证
- 失败则修后端

### Scenario B: Full-Stack Story

示例：

```text
使用 story-verify-fix，处理 path/to/fullstack-epic.md#story-3.5
启动前后端，验证该 Story 的关键用户流
```

目标：
- 跑前后端联调
- 验证 UI 操作确实驱动后端状态变化
- 失败则修前后端

### Scenario C: Full-Stack + Design Reference

示例：

```text
使用 story-verify-fix，处理 path/to/ui-epic.md#story-1.3
启动前后端，并按 Story 中的设计参考图检查 UI 对齐
```

目标：
- 跑联调验证
- 结合设计图做视觉对齐检查
- 失败则修行为或视觉实现

---

## 5. Skill Trigger Contract

建议 skill 名称：

```text
story-verify-fix
```

建议 description：

```text
从 Story 文件启动“环境启动 → Story 验证 → 前后端联调 → 设计图对齐检查 → 自动修复重试”的 workflow。适用于需要同时验证后端、前端、集成行为和 UI 对齐的复杂 Story。
```

触发条件：
- 用户说“验证这个 Story”“做 e2e”“联调测试”“自己修到通过”
- 用户明确要求启动前后端进行集成验证
- 用户提到“有设计图，要验证 UI 是否对齐”

---

## 6. Input Contract

`story-verify-fix` 需要尽量从 Story 和仓库中自动补全输入，用户只提供最少信息。

### Required Inputs

- Story 路径或 Story 内容

### Optional Inputs

- 是否启动后端
- 是否启动前端
- 后端启动命令
- 前端启动命令
- 后端 base URL
- 前端 base URL
- 是否执行设计图对齐
- 是否限制为 quick / full / regression 验证
- 最大自动修复轮次

### Auto-discovered Inputs

优先自动发现：
- Story 验收标准
- Story 的“设计参考”表格
- 后端默认健康检查 URL
- 默认前后端本地端口
- Story 关联页面、路由、关键用户流

---

## 7. Operating Modes

### Mode 1: Backend Verify-Fix

只启动后端，执行：
- API 验证
- 应用层 / 集成验证
- 限定范围的修复循环

### Mode 2: Full-Stack Verify-Fix

启动前后端，执行：
- 后端验证
- 浏览器级联调验证
- 失败后修前后端

### Mode 3: Full-Stack Verify-Fix + Visual

在 Full-Stack 模式基础上增加：
- Story 设计参考图解析
- 页面截图
- 关键布局/结构/状态对齐检查

---

## 8. Workflow

### Phase 0: Intake

目标：解析 Story，确定验证范围。

动作：
1. 读取 Story 文件
2. 提取验收标准
3. 提取设计参考图路径
4. 判断是后端-only、full-stack 还是 full-stack + visual
5. 输出验证计划

输出：
- Story ID
- 验收标准列表
- 影响层级
- 需要启动的服务
- 是否执行视觉对齐
- 验证模式

### Phase 1: Environment Bring-Up

目标：启动需要的运行环境并确认 ready。

动作：
1. 启动后端服务
2. 如需要，启动前端服务
3. 等待健康检查通过
4. 确认前端请求的 API 指向正确后端

后端默认检查：
- `/health/live`
- `/health`

前端默认检查：
- 首页可打开
- 若 Story 指定页面存在，目标页面可打开

失败策略：
- 环境启动失败时，不进入修代码循环，先报告环境问题

### Phase 2: Deterministic Story Verification

目标：先用稳定、可重复的方式验证 Story 行为。

动作：
1. 根据 AC 生成验证步骤
2. 优先执行后端 API / 集成验证
3. 记录断言结果

典型验证：
- API 成功返回
- 数据状态变更正确
- 错误路径返回预期业务错误
- 幂等/并发场景至少有一个关键断言

原则：
- 先 deterministic，再 exploratory
- 尽量少依赖“AI 主观理解页面”

### Phase 3: Full-Stack Integration Verification

目标：验证前端与后端真实联通。

动作：
1. 打开 Story 对应页面
2. 按用户流执行操作
3. 检查页面状态变化
4. 检查网络请求是否成功
5. 检查前端展示与后端状态是否一致

必须覆盖：
- loading
- success
- error
- 空状态（如适用）

### Phase 4: Visual Alignment Verification

触发条件：
- Story 含设计参考图

目标：验证 UI 是否与设计图关键结构对齐。

动作：
1. 读取设计参考图路径
2. 打开对应页面
3. 采集当前截图
4. 对照设计图检查：
   - 页面结构
   - 组件层级
   - 关键按钮位置
   - 主要间距与对齐
   - 空状态 / 错误态 / loading 态
   - 响应式关键断点（如设计图提供）

第一版策略：
- 不做像素级 diff
- 做“结构 + 关键视觉要素”比对

输出等级：
- aligned
- partially aligned
- misaligned
- needs human confirmation

### Phase 5: Fix Loop

目标：发现问题后自动修复并重试。

循环逻辑：
1. 收集失败证据
2. 判断失败类型
3. 修改代码
4. 重跑相关验证
5. 达到通过或超过轮次上限

失败类型分类：
- environment
- backend behavior
- frontend integration
- visual mismatch
- flaky/unclear test

### Phase 6: Final Report

输出必须包含：
- Story 基本信息
- 启动的服务
- 后端验证结果
- 前后端联调结果
- 视觉对齐结果
- 自动修复轮次
- 剩余失败项
- 证据摘要

---

## 9. Verification Matrix

### Backend Story

- Health endpoint
- Story 相关 API
- 关键业务状态断言
- 至少一个失败路径

### Full-Stack Story

- Backend Story 全部验证
- 页面加载
- 关键交互
- 前端状态与后端状态一致
- console / network error 检查

### Full-Stack + Visual Story

- Full-Stack Story 全部验证
- 设计图结构比对
- 关键视觉偏差识别

---

## 10. Fix Loop Policy

### Auto-fix Allowed

适合自动修复：
- API 字段映射错误
- 路由接线错误
- 前端调用路径错误
- 状态展示遗漏
- 局部视觉偏差
- 断言失败但原因明确

### Stop and Report

以下情况应停止自动修复：
- 启动命令或运行环境不明确
- Story 验收标准与设计图冲突
- 设计图缺失或不可读
- 修复 3 轮后仍同类失败
- 错误涉及大范围架构缺口
- 前端源码不可用或不可构建

建议默认：
- 最大修复轮次：3
- 同类错误连续 2 次无进展：停止

---

## 11. Integration With Existing Workflows

推荐串联方式：

1. 先用 `story-reference-impl` 做复杂 Story 的研究与设计
2. 完成实现
3. 用 `story-verify-fix` 做 Story 级验证与自动修复
4. 最后用 `docs/reference/guides/review-checklist-python-fastapi.md` 做结构化 review

即：

```text
研究/设计 -> 实现 -> verify-fix -> review
```

---

## 12. Repository-Specific Constraints

### Current Backend

当前后端入口清晰：
- `main.py`

因此第一版可以稳定支持后端启动与 API 验证。

### Current Frontend

当前仓库内 `frontend/` 目录看不到明确的源码和启动脚本入口，只看到：
- `.env`
- `dist/`
- `node_modules/`
- `public/`

这意味着第一版设计必须允许：
- 后端-only 模式先落地
- full-stack 模式在用户提供前端启动命令时启用

换句话说，`story-verify-fix` 的 first version 应该支持：
- backend verify-fix: 默认稳定可用
- full-stack verify-fix: 条件启用
- visual verify-fix: 在设计图和页面可访问时启用

---

## 13. First-Version Implementation Strategy

### V1

先实现最小闭环：
- Story 解析
- 后端启动
- 后端 API 验证
- 可选前端启动
- 基本联调验证
- 有限自动修复循环

### V1.5

补充：
- 设计参考图解析
- 页面截图与结构化视觉对齐检查

### V2

补充：
- diff-aware 验证
- baseline / regression 模式
- 更强的失败证据归档

---

## 14. Example Output Contract

```md
## Story Verify-Fix Report

### Story
- Story: 3.5 Agent 控制台前端
- Mode: full-stack + visual

### Environment
- Backend: started on http://127.0.0.1:8000
- Frontend: started on http://127.0.0.1:3000

### Verification
- Backend API: passed
- Full-stack integration: passed after 2 fix loops
- Visual alignment: partially aligned

### Fix Loops
1. 修复前端调用错误 API 路径
2. 修复 loading 状态未结束的问题

### Remaining Issues
- 页面顶部工具栏间距与设计图不一致
- 空状态插图缺失

### Decision
- Story behavior: accepted
- Visual parity: needs follow-up
```

---

## 15. Recommended Next Step

如果进入实现阶段，建议下一步不是直接写 `SKILL.md`，而是先做下面两个产物：

1. 一个 `docs/reference/guides/story-verify-fix-playbook.md`  
   写具体命令、环境变量、服务启动和验证入口约定。

2. 一个第一版 `story-verify-fix/SKILL.md`  
   只覆盖 V1 范围，避免一开始做成大而全 workflow。

第一版成功标准不是“万能验证”，而是：

**AI 能围绕一个 Story，把服务拉起来，跑验证，发现错误，修 1 到 3 轮，并给出可信结论。**
