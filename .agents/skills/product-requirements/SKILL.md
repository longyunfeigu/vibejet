---
name: product-requirements
description: Turn a fuzzy product idea into a structured PRD using EARS syntax, or review/update an existing PRD. Use when the user has a feature or product concept that still needs clarification, product framing, scope challenge, role definitions, epics, testable requirements, architecture handoff, and Story breakdown notes.
---

# Product Requirements

把模糊产品想法收敛成一份可继续进入架构设计和 Story 拆解的 PRD。

这个 skill 不应一上来就套模板开写。先做产品挑战，再做需求澄清，再按 EARS 生成可测试需求。

## 适用场景

- 用户只有产品想法，还没有明确 PRD
- 需求边界不清，需要先澄清用户、问题、核心价值
- 需要产出一份后续可接 `architecture -> epic-story-generator` 的 PRD

不适用：
- 已经有成熟 PRD，只是想拆 Story
- 任务已经进入实现阶段
- 用户要的是技术方案，不是产品需求文档

## 输入

优先从用户输入中提取：
- 工作模式：`create` / `review` / `update`
- 产品或功能想法
- 目标用户
- 核心问题
- 预期结果
- 已知约束

按模式读取同目录下资源：
- `assets/requirements_template.md`：`create` / `update` 生成 PRD 前必须读取
- `references/interview_questions.md`：`create` / `update` 做 Phase 0/1 时必须读取
- `references/quality_rubric.md`：`review` 模式和 Phase 4 质量门必须读取

## 核心原则

1. 先挑战问题定义，再写需求。
2. PRD 关注用户结果和产品边界，不提前滑向技术实现细节。
3. 每条关键需求必须可测试、可验证、可继续拆成 Story。
4. 默认 `Standard` 范围模式，既不过度扩 scope，也不机械压缩；按 stage 与需求体量调整到 `Lightweight` 或 `Deep`。
5. 区分需求来源：用户明确输入、外部调研证据、模型推断，不混为一谈。
6. PRD 不做技术方案，但必须把架构和 Story 拆解需要的产品约束交接清楚。

## 工作模式

先判断本次使用哪种模式。用户显式指定时，以用户指定为准。

| 模式 | 何时使用 | 行为 |
|------|----------|------|
| `create` | 默认模式；没有现成 PRD，或用户明确要新建 PRD | 跑完整 Phase 0-4，写入 `docs/project/requirements.md` |
| `review` | 用户要求审查、评估、找问题、检查已有 PRD | 读取指定 PRD 或 `docs/project/requirements.md`，只输出问题和改进建议；除非用户明确要求，不改文件 |
| `update` | 用户要求修改、补充、追加、重构已有 PRD | 读取现有 PRD，在原文件上更新；保留已有决策、编号和明确非目标 |

模式选择规则：
- 没有现有 PRD 且用户给的是产品想法 → `create`
- 有现有 PRD 且用户说"审查/检查/review" → `review`
- 有现有 PRD 且用户说"修改/补充/新增/更新" → `update`
- 有现有 PRD 但用户意图不清 → 问一个问题确认是基于现有文档更新，还是重新开始

`review` 模式不跑完整澄清流程，只按 `references/quality_rubric.md` 做评分、下游交接检查和风险摘要。`update` 模式只对变更影响范围补问，不重新挑战整份 PRD。

## Workflow

### Phase 0: Triage + Pressure Test

在写 PRD 之前，读取 `references/interview_questions.md` 的 Phase 0：
- 做 Resume Check、Stage Routing、Scope Mode、Gap Lenses 和 Non-Goals。
- 按 stage 只问必要问题，不把所有 lens 机械跑一遍。
- 用户答案暴露真实不确定性时，记入 `[未验证假设]`，不要绕过。
- Pressure Test 是为 PRD 收敛服务，不是产品论证大会。

### Phase 0.5: External Landscape Scan（可选）

在问题挑战完成、范围模式确定后，根据 `research_mode` 决定是否做外部调研。

#### research_mode 规则

| 范围模式 | 默认 research_mode | 可覆盖 |
|----------|-------------------|--------|
| `Deep` | `light` | 用户可升级为 `deep` 或降级为 `none` |
| `Standard` | `none` | 用户可升级为 `light` 或 `deep` |
| `Lightweight` | `none` | 用户可升级为 `light` |

用户也可以在任何时候直接指定 research_mode，覆盖默认值。

#### 三种模式

**`none`（跳过调研）**
- 内部系统、保密项目、用户已非常清楚市场情况
- 直接进入 Phase 1

**`light`（轻量扫描，5-10 分钟）**
- 用 WebSearch 搜索 3-5 个相邻产品/解决方案
- 快速浏览官网、核心功能页、定价页
- 产出：

| 维度 | 内容 |
|------|------|
| Table Stakes | 同类产品都有、用户默认期望的基线功能 |
| Differentiators | 各竞品的差异化卖点 |
| Gaps | 用户常见抱怨、未被满足的需求 |
| Risks | 市场集中度、定价压力、平台依赖等风险信号 |

- 不要抄功能清单，提炼模式和洞察
- 每条结论附来源链接

**`deep`（深度调研，仅在用户明确要求时）**
- 在 `light` 基础上扩展：
  - 搜索用户评价（App Store / G2 / Reddit / 知乎等）
  - 分析竞品定价模型和商业模式
  - 识别技术壁垒和护城河
  - 搜索行业报告或趋势分析
- 产出完整竞品对比矩阵 + 机会分析

#### 调研纪律

- 调研是为了给 PRD 提供证据支撑，不是为了写竞品分析报告
- 调研结果不直接变成需求，而是作为 Phase 1 澄清和 Phase 2 Epic 划分的输入
- 明确标注哪些是"调研发现"vs"用户明确说的"vs"模型推断"
- 保密项目（用户声明或明显可判断）自动设为 `none`，不做联网搜索

### Phase 1: Structured Clarification

读取 `references/interview_questions.md` 的 Phase 1，按 6 个维度澄清：
1. Target User
2. Core Pain
3. Target Outcome
4. Core Workflow
5. Boundaries and Constraints
6. Product Quality Details

每个 turn 只问一个问题。进入下一维度前，先把当前答案收敛成能写入 PRD 的具体陈述。

### Phase 2: PRD Skeleton

基于澄清结果，先形成 PRD 骨架：
- 产品概览
- 角色定义
- Epic 划分
- 非功能需求
- 假设、依赖与约束
- Architecture Handoff
- Epic Decomposition Notes
- （如果做了调研）市场与替代方案摘要

要求：
- Epic 按用户目标和业务能力分组
- 不按技术模块分组
- 每个 Epic 都应可继续拆成 Story
- 如果 Phase 0.5 识别了 Table Stakes，确保 Epic 覆盖这些基线能力
- Architecture Handoff 只写产品约束、风险和开放问题，不写技术选型或实现方案
- Epic Decomposition Notes 只写拆解边界、优先级、依赖和不可拆散的能力，不替代 Story 生成

### Phase 2.5: Synthesis Summary

PRD 骨架完成后，**先 surface 一份三桶总结给用户确认**，再进入 Phase 3 写 EARS 需求。这是文档落地前最后一次修正 scope 的机会，比 Phase 4 质量门更早、更便宜。

三桶分类：

- 🟢 **Stated**（用户明确说的）
  - Phase 0/1 对话中用户原话级确认的事实和决策

- 🟡 **Inferred**（AI 基于上下文推断、需用户确认）
  - 例："你说要支持权限分级，我推断管理员可以查看所有用户的记录，对吗？"
  - 用户回答后，转入 Stated 或 Out of scope

- ⚪ **Out of scope**（明确不做）
  - Phase 0 的非目标
  - Phase 1 用户主动剔除的边界

输出格式：

```text
## Synthesis Summary

### 🟢 Stated
- ...

### 🟡 Inferred（待确认）
- ...

### ⚪ Out of scope
- ...
```

用户确认或修正后，进入 Phase 3。如果用户对 Inferred 项有大幅调整，回到对应的 Phase 1 子项重新澄清。

**纪律**：Synthesis Summary 不写实现细节（表名、API 路径、文件结构），那是 architecture 阶段的事。

### Phase 3: EARS Requirement Drafting

将每个 Epic 下的关键需求写成 EARS 句式。

优先使用：
- `When`
- `If`
- `Scenario`
- `Ubiquitous`

要求：
- 每条需求都要有明确角色
- 每条需求都能被测试验证
- 避免"系统应支持""系统应允许"这类空泛表述，除非补足上下文

### Phase 4: PRD Quality Gate

生成草案后，读取 `references/quality_rubric.md` 并执行质量门：
- 先跑 mechanical checks。
- 按 100 分 rubric 打分。
- 低于 75 分时，不进入 `architecture`；先修复或继续澄清。
- 有 critical blocker 时，即使总分 >= 75 也不能进入 `architecture`。
- `review` 模式使用同一 rubric 输出审查报告，不默认改文件。

## 输出要求

### `create` / `update` 输出

输出必须严格遵循：
- `assets/requirements_template.md`

最终产物至少包括：
1. 产品概览
2. 角色定义
3. 按 Epic 分组的 EARS 需求
4. 非功能需求
5. 假设、依赖与约束
6. Architecture Handoff
7. Epic Decomposition Notes

默认写入路径：
- `docs/project/requirements.md`

当 research_mode 为 `light` 或 `deep` 时，还必须包括：
8. 市场与替代方案
9. 证据与来源
10. 待验证假设

建议额外明确：
- 本次 stage：`新产品 0→1 / 已有产品加功能 / 内部工具 / 纯技术债`
- 本次范围模式：`Lightweight / Standard / Deep`
- research_mode：`none / light / deep`
- 明确的非目标

#### Architecture Handoff 写法

用于交接给 `architecture`，只记录架构设计必须接住的产品事实：
- 非功能约束：性能、安全、合规、可用性、审计、数据保留
- 数据和权限边界：敏感数据、角色访问范围、跨租户/跨组织边界
- 外部依赖：第三方平台、人工流程、上游/下游系统
- 开放问题：会影响架构但 PRD 阶段无法决定的问题
- 未验证假设：如果假设错误，会导致架构方向变化的事项

不要在这里写数据库表、API 路径、框架选择、部署拓扑。

#### Epic Decomposition Notes 写法

用于交接给 `epic-story-generator`，只记录拆 Story 需要的产品边界：
- 建议的 Epic 顺序和 MVP 优先级
- Epic 之间的依赖关系
- 不应拆散的端到端用户能力
- 可延后的能力和明确不做的能力
- 每个 Epic 的主要验收风险或测试重点

不要把 Epic 拆成前端/后端/数据库任务。

### `review` 输出

`review` 模式输出审查报告，不默认写文件：
- Score / Gate：按 `references/quality_rubric.md` 给出总分和是否可进入 `architecture`
- Findings：按严重程度列 PRD 问题、歧义、缺口
- Missing Decisions：缺失但必须由用户决定的产品问题
- Handoff Readiness：是否足够交给 `architecture` 和 `epic-story-generator`
- Suggested Edits：建议修改点；只有用户要求时才落到 `docs/project/requirements.md`

## 后置步骤：Codex 审查

**`create` / `update` 模式 PRD 生成完毕后，自动执行 `codex-review`**：
1. 调用 `codex-review` skill，传入刚生成的 PRD 文档
2. Claude Code 自主判断 Codex 建议的采纳，修改文档后输出摘要
3. 用户可说"跳过审查"跳过此步骤

## 与其他 skill 的关系

- `codex-review`
  - PRD 生成完毕后自动触发，做独立审查闭环
- `architecture`
  - PRD 明确产品目标与约束后，再进入技术架构
- `epic-story-generator`
  - PRD 稳定后，再拆成 Epic / Story
- `run-story`
  - 不是本 skill 的下游；`run-story` 处理的是已存在 Story 的交付

## 示例触发

```text
使用 product-requirements，帮我把这个产品想法整理成 PRD
```

```text
我想做一个个人财务记账 App，使用 product-requirements
```

```text
使用 product-requirements，先 challenge 一下这个需求，再输出 EARS 格式 PRD
```

```text
使用 product-requirements，research_mode=deep，先做竞品调研再出 PRD
```

```text
使用 product-requirements，mode=review，审查 docs/project/requirements.md
```

```text
使用 product-requirements，mode=update，把邀请协作功能补进现有 PRD
```
