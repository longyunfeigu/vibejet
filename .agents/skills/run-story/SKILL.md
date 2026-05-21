---
name: run-story
description: Single-entry Story orchestration for this repo. Use when the user wants to handle a Story end-to-end without manually switching skills, including implementation routing, optional reference research, verification, and review. Regression QA is opt-in via `full+qa` mode.
---

# run-story

默认的 Story 单入口编排 skill。

这个 skill 不重新实现已有能力。它只负责：
- 识别当前 Story 类型
- 选择合适的子 workflow
- 默认把实现、验证、review 串起来，QA 仅在用户明确要求时执行
- 在关键 gate 停下，而不是无脑一路跑到底

## 适用场景

- 用户说“处理这个 Story”“跑这个 Story”“完成这个 Story”
- 用户不想手动切换 `do-story -> story-verify-fix -> review`
- 用户希望按仓库默认流程完成 Story

不适用：
- 还没有 Story，只是模糊产品想法
- 任务不是 Story 交付，而是单独做 PRD / 架构 / review / QA

如果还没有 Story，应先走：
- `vj-feature` — 给已有项目加功能，从想法到 Epic/Story 生成，再路由到实现
- `vj-product-requirements` — 从零写 PRD（全新项目）
- `vj-architecture` — 架构设计
- `vj-epic-story` — 从 PRD 全量拆解 Epic/Story

## 内部路由关系

`run-story` 只编排这些已有 skill：

- `do-story`
- `story-reference-impl`
- `story-verify-fix`
- `review`
- `diff-aware-qa`

执行时必须按需打开对应 skill 文件并遵循其 workflow，而不是凭记忆重写一套流程。

## 输入

优先识别以下输入：
- Story 路径，例如 `docs/tasks/epics/epic-003.md#story-3.2`
- 或 Story 描述
- 可选参考实现来源
- 可选前端 / 后端启动命令
- 可选 base URL
- 可选设计图路径或 URL
- 可选运行模式：
  - `implement-only`
  - `implement-and-verify`
  - `full`（默认：实现 + 验证 + review，不含 QA）
  - `full+qa`（full + 回归 QA）

默认模式：
- `full`

## Workflow

### Phase 0: Intake

先判断：
- 是普通 Story 还是复杂 Story
- 是否需要参考外部实现
- 是否涉及前端
- 是否有设计图
- 是否可能改 API contract
- 是否可能改 schema / migration

如果缺少关键输入，先做最少补全：
- 从 Story / Epic / plan / 现有代码中补
- 只有在无法安全推断时才问用户

### Phase 1: Route to Implementation Workflow

路由规则：

- 普通 Story
  - 读取并执行 `do-story`

- 复杂 Story，且用户明确需要参考实现
  - 读取并执行 `story-reference-impl`

- Story 明显复杂，但参考方向不清
  - 停下，先确认是否要进入参考实现研究模式

### Phase 2: Delta Sync Gate

实现阶段完成后，检查本次 Story 是否引入：

- API Contract Delta
  - 新端点
  - 请求/响应变化
  - 错误码 / 鉴权 / 分页过滤变化

- Schema / Migration Delta
  - 表、字段、索引、约束变化
  - migration
  - 一致性 / 事务 / 幂等相关持久化变化

如果命中：
- 优先要求在 plan 中补对应 delta section
- 如已有 `docs/project/api_spec.md` / `docs/project/database_schema.md`，再决定是否同步更新

重要边界：
- 当独立设计文档不存在时，只能说“需要补 delta”
- 不能说“违反了这些文档”

### Phase 3: Verify

除非用户明确要求 `implement-only`，否则默认进入：
- `story-verify-fix`

目标：
- 启动服务
- 执行 Story 验收验证
- 必要时做前后端联调
- 必要时做轻量视觉对齐
- 有错误时进入有限修复循环

### Phase 4: Review

只要 verify 阶段通过，默认进入：
- `review`

目标：
- 找 blocking 问题
- 找结构性回归风险
- 找缺失测试

### Phase 5: Regression QA（可选，默认跳过）

**默认不执行**。仅在用户明确要求时进入：
- 用户说"做回归 QA""跑 QA""run QA"
- 用户在运行模式中指定 `full+qa`

满足条件时，进入：
- `diff-aware-qa`

未执行时在最终结果里说明"QA 已跳过（默认关闭，如需执行请指定 `full+qa` 或明确要求）"。

## Gates

### Gate A: Intake Gate

以下情况停止，不进入实现：
- Story 不清楚
- 复杂 Story 但参考方向不清
- 用户要求真实前端改动，但仓库没有前端源码且也没有给正确 workspace

### Gate B: Verify Gate

以下情况停止，不自动进入 review：
- 服务无法稳定启动
- verify-fix 超过自动修复上限
- Story 核心验收仍不通过

### Gate C: Review Gate

review 完成后默认流程结束。仅当用户指定 `full+qa` 模式或明确要求 QA 时才进入 Phase 5。

### Gate D: QA Gate（仅 full+qa 模式）

以下情况停止并报告：
- diff-aware-qa 发现高严重度回归

## 输出契约

最终输出至少包含：

### 1. Story 路由结果
- 使用了哪个实现入口
- 为什么这样路由

### 2. Delta 结果
- 是否补了 API Contract Delta
- 是否补了 Schema / Migration Delta

### 3. Verify 结果
- 是否通过
- 自动修复轮次
- 剩余问题

### 4. Review 结果
- blocking 数量
- non-blocking 数量

### 5. QA 结果
- 是否执行 diff-aware-qa
- 发现的问题
- 残余风险

### 6. 最终结论
- `done`
- `done with risks`
- `blocked`

## 默认顺序

```text
run-story
-> do-story 或 story-reference-impl
-> story-verify-fix
-> review
-> diff-aware-qa（仅 full+qa 模式或用户明确要求）
```

## 触发示例

```text
使用 run-story，处理 docs/tasks/epics/epic-003.md#story-3.2
```

```text
使用 run-story，处理 story 3.2，需要参考 OpenHands 的实现
```

```text
使用 run-story，完成这个 Story 的实现、验证和 review
```

```text
使用 run-story full+qa，处理 story 3.2
```
