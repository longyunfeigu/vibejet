# run-story Design

这份文档定义一个新的单入口编排 skill 设计，用于把当前分散的 Story 开发链路收敛成一个默认入口。

## 1. 目标

当前仓库的主线已经清楚，但仍然依赖人工切换：

```text
do-story / story-reference-impl
-> story-verify-fix
-> review
-> diff-aware-qa
```

问题不是 skill 本身不清楚，而是：
- 容易漏掉后续 gate
- 高频使用时切换成本高
- 新人不容易记住先后顺序

`run-story` 的目标是提供一个**默认入口**，由它来决定接下来调用哪个子 workflow。

它不是替代已有 skill，而是编排已有 skill。

## 2. 推荐命名

推荐名称：`run-story`

理由：
- 动词开头，意图明确
- 比 `story-pipeline` 更像用户会说的话
- 更适合作为默认入口 skill

不推荐优先使用 `story-pipeline` 的原因：
- 更像内部术语，不像实际触发短语
- 用户更可能说“处理这个 Story”或“跑这个 Story”

如果后续需要更偏系统化的名称，可以把 `story-pipeline` 作为设计概念，而对外入口仍保留 `run-story`。

## 3. 设计原则

### 3.1 单入口，对内复用

`run-story` 只负责编排，不重新实现以下能力：
- Story 实现：`do-story`
- 参考实现研究：`story-reference-impl`
- 验证闭环：`story-verify-fix`
- 代码审查：`review`
- 第二层回归 QA：`diff-aware-qa`

### 3.2 默认不漏步

只要用户说“处理这个 Story”，默认流程应至少走到：

```text
实现
-> verify-fix
-> review
```

如果改动命中高回归风险，再继续进入：

```text
-> diff-aware-qa
```

### 3.3 仍然保留 gate

`run-story` 不是“一路自动跑到底”的黑盒。

以下情况必须停下：
- Story 边界不清
- 需要参考实现但参考源不明确
- 前端源码缺失但用户要求真实前端改动
- verify-fix 超过自动修复上限
- review 出现 blocking
- diff-aware QA 发现高严重度问题

### 3.4 可恢复

`run-story` 应优先复用现有状态文件和 plan，而不是每次从头开始：
- `docs/plans/*.md`
- `.claude/do-story.*.local.md`
- `story-status`（如团队启用）

## 4. 输入契约

`run-story` 至少支持以下输入：

- Story 路径
  - 例如：`path/to/epic.md#story-3.2`
- 或 Story 描述
- 可选参考实现来源
  - GitHub URL / 仓库名 / 官方文档
- 可选后端启动命令
- 可选前端启动命令
- 可选 base URL
- 可选设计图路径或 URL
- 可选运行模式
  - `implement-only`
  - `implement-and-verify`
  - `full`（默认）

默认模式建议：
- `full`

## 5. 决策树

### Step 1: 识别 Story 类型

先判断：
- 是普通 Story，还是复杂 Story？
- 是否需要参考外部实现？
- 是否涉及前端？
- 是否有设计图？
- 是否改 API contract？
- 是否改 schema / migration？

### Step 2: 选择实现入口

规则：

- 普通 Story：
  - 进入 `do-story`

- 复杂 Story，且明确需要参考实现：
  - 进入 `story-reference-impl`

- 如果用户没有给参考实现，但 Story 明显复杂：
  - 停下，先确认是否要进入参考实现研究模式

### Step 3: 选择是否补 delta 文档

规则：

- 改 API contract：
  - 在 plan 中补 `API Contract Delta`
  - 必要时更新 `api-design`

- 改 schema / migration：
  - 在 plan 中补 `Schema / Migration Delta`
  - 必要时更新 `data-model`

注意：
- 当 `docs/api-design.md` / `docs/data-model.md` 不存在时，只能说“需要补 delta”，不能说“违反了文档”

### Step 4: 实现后进入 verify

默认进入：
- `story-verify-fix`

作用：
- 启动后端
- 必要时启动前端
- 执行 Story 验收验证
- 必要时做联调和视觉对齐
- 有错误时进入有限自动修复循环

### Step 5: verify 通过后进入 review

默认进入：
- `review`

作用：
- 结构化代码审查
- 输出 blocking / non-blocking / residual risk

### Step 6: 按条件进入 diff-aware QA

以下情况默认进入：
- 改了前端页面、共享组件、样式、路由
- 改了后端公共接口、认证、上传下载、权限、日志流、WebSocket
- 改动文件较多
- 用户明确要求做回归 QA

否则可以跳过，并在最终报告里说明跳过理由。

## 6. 编排后的完整流程

```text
Phase 0: Intake
  -> 识别 Story / 参考实现 / 前后端 / 设计图 / 风险

Phase 1: Implement
  -> 普通 Story: do-story
  -> 复杂 Story: story-reference-impl

Phase 2: Delta Sync
  -> 如改 API: plan/API contract delta
  -> 如改 schema: plan/schema delta

Phase 3: Verify
  -> story-verify-fix

Phase 4: Review
  -> review

Phase 5: Regression QA
  -> diff-aware-qa（按需）

Phase 6: Final Report
  -> 汇总实现、验证、review、QA 结果
```

## 7. Gate 设计

### Gate A: Intake Gate

以下情况停止，不进入实现：
- Story 输入不足
- 复杂 Story 但参考方向不清
- 真实前端改动需要源码，但仓库里没有前端源码

### Gate B: Verify Gate

以下情况停止，不自动进入 review：
- 服务无法稳定启动
- verify-fix 超过自动修复上限
- Story 核心验收仍不通过

### Gate C: Review Gate

以下情况停止，不自动进入 diff-aware QA：
- review 存在 blocking

### Gate D: QA Gate

以下情况停止并报告：
- diff-aware QA 发现高严重度回归

## 8. 输出契约

`run-story` 的最终输出应统一包含：

### 1. Story 执行摘要
- 使用了哪个实现入口
- 是否补了 plan / API delta / schema delta

### 2. Verify 结果
- 是否通过
- 自动修复轮次
- 剩余失败点

### 3. Review 结果
- blocking 数量
- non-blocking 数量
- 是否可继续

### 4. QA 结果
- 是否执行 diff-aware QA
- 发现的问题
- 残余回归风险

### 5. 总结论
- `done`
- `done with risks`
- `blocked`

## 9. 不做什么

`run-story` 第一版不负责：
- 生成 PRD
- 生成架构文档
- 自动合并分支
- 自动提交 / 发 PR
- 自动决定所有产品级 tradeoff

这些仍由现有上游流程或用户决策处理。

## 10. 第一版实现建议

### V1

先做编排，不做深度自动化：
- 单入口
- 条件选择 `do-story` / `story-reference-impl`
- 默认串上 `story-verify-fix -> review`
- 高风险时再串 `diff-aware-qa`
- 用现有 plan / state 文件，不新造一套状态系统

### V2

再增强：
- 自动识别是否需要参考实现
- 自动识别是否需要 diff-aware QA
- 与 `story-status` 集成
- 更强的 resume 能力

### V3

最后才考虑：
- 自动生成 commit 节点建议
- pre-merge gate
- 与 release / ship 流程连接

## 11. 推荐触发语句

```text
使用 run-story，处理 path/to/epic.md#story-3.2
```

```text
使用 run-story，处理 story 3.2，需要参考 OpenHands 的实现
```

```text
使用 run-story，完成这个 Story 的实现、验证和 review
```

## 12. 为什么这个设计比手动切换更好

它比现在“手动切 skill”的方式更好，原因不是更自动，而是更稳：

- 默认不漏 `verify` 和 `review`
- 仍然保留关键 gate，不会无脑一路跑到底
- 复用现有 skill，不引入第二套重复逻辑
- 对用户只暴露一个默认入口，心智负担更低

这就是 `run-story` 的设计目标。
