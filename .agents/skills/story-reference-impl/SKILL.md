---
name: story-reference-impl
description: 从 Story 文件或 Story 描述启动“参考实现研究 → DDD 适配设计 → 分层实现 → Review”的协作流程。适用于技术复杂、需要借鉴开源项目、GitHub 仓库或框架文档实现的后端 Story。
---

# story-reference-impl

用于本仓库中“复杂 Story 需要参考开源实现”的场景。

这个 skill 是一个轻量编排层：
- Story 解析和仓库约束读取，遵循 `vj-work` task 执行的思路（先读 Story AC 与仓库硬约束再动手）
- 参考实现研究和抽象提取：研究方法工具箱见 `references/research-methods.md`（唯一副本）
- 最终目标不是搬运代码，而是产出符合本仓库 DDD 分层的实现

工作流位置：plan-time 的轻量选型**建议**由 `vj-epic-plan` Phase 2 Agent E（external-solutions
scout）产出，三选一结论（直接用 / 改造 / 自研）在其 Phase 3 收口登记 decisions.md（E 的建议
是输入，拍板在 Phase 3）；本 skill 承接其中"改造 / 深度借鉴"路径的实现期深度研究与落地。
也可脱离 epic 流程单独调用。

## 适用场景

当满足任一条件时使用本 skill：
- 用户明确说某个 Story 技术复杂，需要参考开源项目
- 用户提供了 GitHub 仓库、库名或框架名，希望“先研究再实现”
- 用户提到“参考谁的实现比较好”“帮我借鉴某项目的设计”
- 用户希望按固定阶段协作，而不是直接生成代码

不适用：
- 只是简单 CRUD 或小修小补
- 不需要外部参考，直接按现有模式实现即可
- 用户只要某个 API 的文档用法，且不涉及 Story 落地

## 输入识别

优先从用户输入和仓库文件中提取以下信息：
- Story 路径，或 Story 内容
- 目标功能
- 验收标准
- 技术约束和非功能要求
- 参考来源：具体项目 / GitHub URL / 库名 / “尚未确定”
- 参考粒度：整体架构 / 单模块实现 / API 用法 / 只看设计思路
- 用户特别关注的问题：并发、缓存、事件流、权限、回放、幂等、性能等

如果信息不完整，优先从以下位置补全：
- `docs/tasks/epics/`
- `docs/project/architecture.md`
- `docs/project/api/conventions.md` + 相关 `docs/project/api/{module}.md`（如存在，且本次涉及接口契约；旧 api_spec.md 仅 fallback）
- `docs/project/data/overview.md` + 相关 `docs/project/data/{module}.md`（如存在，且本次涉及数据模型 / migration；旧 database_schema.md 仅 fallback）
- 现有代码中的相似模块

只有在无法安全推断时，才向用户提出最少的问题。

## 协作原则

1. 先研究，后设计，再实现。不要一上来写代码。
2. 每个 Phase 结束都要停下，等待用户确认后再继续。
3. Phase 0 必须先做 Scope Challenge，先问“能否缩 scope、能否复用现有实现”，再进入研究。
4. 研究阶段必须包含“不适合直接复用的点”，避免盲目照搬。
5. 适配阶段必须显式映射到本仓库 DDD 分层，并明确 `What already exists` 与 `NOT in scope`。
6. 实现前必须显式列出关键 failure modes 和测试覆盖方式。
7. 实现阶段按层推进：`domain` → `application` → `infrastructure` → `api`。
8. 关键实现可以注明参考来源，但代码必须按本仓库风格重写。

## Workflow

### Phase 0: 初始化与研究策略

目标：确认 Story 边界、参考来源和研究方法。

执行步骤：
1. 读取 Story 文件或用户提供的 Story 内容
2. 读取相关设计文档和仓库约束
3. 解析参考来源和参考粒度
4. 选择研究方法：按 `references/research-methods.md` 的决策树选方法 A–E
   （官方文档 / WebSearch+WebFetch / clone / gh CLI / 多项目选型），操作步骤见该文件
5. 输出研究策略并停下等待确认

Phase 0 输出必须包含：
- 目标功能
- 参考项目或选型方向
- 参考粒度
- 研究方法
- 预期关注点
- Scope Challenge:
  - 现有代码/流程里已经有什么可以复用
  - 达成目标的最小改动是什么
  - 哪些内容属于 scope creep，明确本次不做
  - 如果预计修改 >8 个文件或新增 >2 个服务/抽象，是否需要收缩方案

### Phase 1: 研究参考实现

目标：理解参考实现的设计意图和核心抽象。

硬约束：
- 只做研究，不写实现代码
- 按 Phase 0 选定的方法执行（操作手册：`references/research-methods.md`）
- 聚焦关键文件，不做无边界源码漫游（方法 B ≤5 文件、方法 C ≤10 文件）
- 优先提炼 Why 和 What，不直接抄 How

Phase 1 输出必须包含：

```md
## 研究报告: {参考项目} — {功能名}

### 1. 架构概览
- 整体架构风格
- 该功能所在模块层级
- 模块间依赖关系

### 2. 核心设计决策
| # | 决策点 | 参考项目的选择 | 选择理由 | 备选方案 |
|---|--------|---------------|----------|----------|

### 3. 关键数据结构
- 核心模型 / 事件 / 状态 / 配置对象

### 4. 核心流程
- 用流程图或顺序描述主要业务流

### 5. 接口 / 抽象定义
- 协议、抽象类、扩展点、回调机制

### 6. 值得借鉴的点
- 设计亮点及原因

### 7. 不适合直接复用的点
- 不适合原因
- 在本仓库中的替代思路

### 8. 参考文件索引
| 文件路径 | 作用 | 关键函数/类 | 参考价值 |
|----------|------|-------------|----------|
```

Phase 1 结束后停下，等待用户确认。

### Phase 2: DDD 适配设计

目标：把参考实现映射到本仓库架构。

硬约束：
- 只做设计，不写实现代码
- 明确哪些概念是复用思路，哪些需要重写
- 遵守依赖方向：`API → application → domain ← infrastructure`

Phase 2 输出必须包含：

```md
## 适配方案

### 1. What already exists
- 当前仓库中已存在、可复用的代码/模型/端口/测试模式
- 哪些可以直接复用，哪些只能改造复用

### 2. 概念映射表
| 参考项目概念 | 参考位置 | 本项目 DDD 层 | 本项目文件路径 | 映射方式 |
|--------------|----------|---------------|----------------|----------|

### 3. 架构差异与适配策略
| 差异点 | 参考项目 | 本项目 | 适配策略 |
|--------|----------|--------|----------|

### 4. 文件变更清单
| 操作 | 文件路径 | 说明 | 参考来源 |
|------|----------|------|----------|

### 5. NOT in scope
- 本次明确不做的内容
- 延后到后续 Story / PR 的内容

### 6. 实现顺序
1. domain
2. application
3. infrastructure
4. api

### 7. 关键接口伪代码
- 实体
- 仓储接口
- 应用服务
- API 输入输出 DTO

### 8. Failure modes & test diagram
| Codepath / Interaction | Failure mode | 系统行为 | 用户可见性 | 测试类型 |
|------------------------|--------------|----------|------------|----------|

### 9. 测试策略
- 验收标准到测试用例的映射
- 单元 / 集成 / API 测试边界
```

映射方式使用以下枚举：
- 直接复用
- 改造复用
- 重新设计
- 拆分
- 合并
- 不需要

Phase 2 结束后停下，等待用户确认。

### Phase 3: 实现

目标：按已确认方案分层实现。

执行要求：
- 严格按 `domain` → `application` → `infrastructure` → `api` 推进
- 每完成一层，报告：
  - 改了什么
  - 为什么这样改
  - 还剩什么风险
  - 哪些测试已覆盖，哪些还未覆盖
- 关键函数可标注 `参考: {project} {file}:{symbol}`，但实现必须适配本仓库

仓库约束：
- `domain` 层不得依赖 `infrastructure` / `application` / `api`
- `application` 层负责用例编排，不直接泄漏 ORM 细节
- 日志使用 `core.logging_config.get_logger(__name__)`
- 领域异常使用 `BusinessException`
- 公共函数需要类型提示

### Phase 4: Review

目标：用 code review 视角检查实现质量。

Review 重点：
- DDD 分层是否被破坏
- 是否引入行为回归风险
- 异常处理是否统一
- 边界条件和失败路径是否遗漏
- 测试是否覆盖关键路径
- 优先套用 `docs/reference/guides/review-checklist-python-fastapi.md` 做结构化审查

如果没有发现问题，也要明确说明剩余风险和测试空白。

## 推荐协作句式

适合让用户这样触发：

```text
使用 story-reference-impl，处理 docs/tasks/epics/epic-003.md#story-3.2
参考项目是 https://github.com/All-Hands-AI/OpenHands
我重点关注流式事件传递、断线重连和历史回放
```

```text
使用 story-reference-impl，处理 docs/tasks/epics/epic-002.md#story-2.4
我还没确定参考哪个开源项目，先帮我选型
```

## 失败保护

遇到以下情况时，不要直接写代码，应先停下说明问题：
- Story 边界不清或验收标准缺失
- 参考项目与本仓库架构差异过大
- 研究结论不足以支撑设计决策
- 用户要求直接搬运第三方代码

默认原则：
- 借鉴设计，不照搬实现
- 先缩小问题，再推进实现
