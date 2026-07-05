# Interview Questions

Use these questions for `create` and `update` modes before drafting or changing a PRD.

Rules:
- Serial mode: ask one question per turn. Fast-draft mode (routing criteria live in
  SKILL.md Phase 1, not here): batch the remaining gaps into one round of at most 4
  single-select questions.
- Prefer single-select options with a free-text fallback.
- Use multi-select only for naturally combinable sets such as goals, constraints, or non-goals.
- Do not ask questions already answered by the user or the existing PRD.
- Convert answers into concrete PRD statements before moving to the next dimension.

## Phase 0: Triage + Pressure Test

### Resume Check

If the user references an existing PRD, or `docs/project/requirements.md` exists:
- Read the file.
- If mode is `review` or `update`, use it directly.
- If mode is unclear, ask whether to update the existing PRD or start fresh.
- When updating, preserve existing decisions, requirement IDs, explicit non-goals, and unresolved questions unless the user changes them.

### Stage Routing

Classify the request before choosing pressure-test questions.

| Stage | Signals | Ask |
|-------|---------|-----|
| New product 0->1 | No existing product, users, or paid workflow | Evidence + Specificity + Counterfactual + Attachment |
| Existing product feature | Existing product or users | Counterfactual + Attachment |
| Internal tool / admin system | Internal team workflow | Counterfactual + Specificity |
| Technical debt / compliance | Does not directly change user behavior | Counterfactual + impact radius |

If stage is unclear, ask:

```text
这个需求更接近哪一种？
1. 新产品 0->1
2. 已有产品加功能
3. 内部工具 / 管理系统
4. 纯技术债 / 合规改造
```

### Scope Mode

Choose or confirm one scope mode:

| Mode | Use when | Question |
|------|----------|----------|
| Lightweight | User wants the smallest useful version | "这次是先做最小可交付版本吗？" |
| Standard | Default | "我会按 Standard 范围收敛：可执行但不过度扩 scope，可以吗？" |
| Deep | Strategic or high-risk product work | "这次是否需要更完整地覆盖长期演进和市场风险？" |

### Gap Lenses

Use only the lenses required by stage.

#### Evidence Gap

Use for new product 0->1.

Ask:
- 用户已经为这个问题做过什么具体行为？
- 是否付过钱、搭过手工流程、抱怨过、绕过过？
- 这个问题是"觉得有用"，还是"已经发生且造成成本"？

PRD output:
- Convert answers into evidence, assumptions, or validation tasks.
- If evidence is weak, mark the need as `[未验证假设]`.

#### Specificity Gap

Use for new products and internal tools.

Ask:
- 真实使用人是哪个角色？
- 这个事件多久发生一次？
- 谁触发流程，谁审批，谁消费结果？

PRD output:
- Convert answers into role definitions, usage frequency, and core workflow triggers.

#### Counterfactual Gap

Use for every stage.

Ask:
- 现在没有这个功能，用户怎么处理？
- 是手工 Excel、跨系统切换、找同事、还是放弃处理？
- 当前 workaround 的真实成本是什么：时间、错误率、沟通成本、合规风险，还是收入损失？

PRD output:
- Convert answers into problem statement, success metrics, and non-functional constraints.

#### Attachment Gap

Use for new products and existing product features.

Ask:
- 如果不做成用户最初设想的形态，还能交付同样价值吗？
- 最小有价值版本是什么？
- 哪些功能只是方案偏好，不是用户结果必须？

PRD output:
- Convert answers into MVP scope, non-goals, and deferred capabilities.

#### Durability Gap

Use only in `Deep` scope mode.

Ask:
- 12 个月内哪些变化会让这个需求失效？
- 团队结构、上游平台、合规规则、数据规模或商业模式会怎么变？

PRD output:
- Convert answers into architecture handoff constraints and risks.

### Non-Goals

Always ask for non-goals before drafting:

```text
这次 PRD 明确不解决什么？可以是用户群体、流程步骤、平台、权限、集成、报表、自动化能力或后续版本能力。
```

## Phase 1: Structured Clarification

Use these dimensions in order. Skip a question only when the answer is already explicit.

### 1. Target User

Ask:
- 核心用户是哪个角色？
- 他们在什么场景下会用这个产品？
- 谁是次要用户或受影响角色？

Write into:
- Product overview
- Role definitions
- Permission and data boundaries

### 2. Core Pain

Ask:
- 现在最痛的问题是什么？
- 当前替代方案是什么？为什么不够好？
- 这个痛点发生频率是多少？
- 如果已经做过 research，调研发现的 gaps 是否和用户感知一致？

Write into:
- Core value
- Success metrics
- Evidence and assumptions

### 3. Target Outcome

Ask:
- 用户使用后最关键的成功结果是什么？
- 业务上希望看到什么指标变化？
- 什么结果出现时可以判断 V1 成功？

Write into:
- Product vision
- Core value
- Success metrics

### 4. Core Workflow

Ask:
- 用户完成核心任务的主路径是什么？
- 流程里最容易失败或流失的是哪一步？
- 哪些步骤必须在 V1 端到端闭环？

Write into:
- EARS scenario requirements
- Epic decomposition notes
- Story acceptance focus

### 5. Boundaries and Constraints

Ask:
- 哪些角色会参与？
- 权限、合规、性能、外部依赖有哪些限制？
- 哪些数据敏感，谁可以看，谁可以改？

Write into:
- Non-functional requirements
- Architecture handoff
- Assumptions, dependencies, and constraints

### 6. Product Quality Details

Ask:
- 哪些体验会让用户觉得这个产品被认真思考过？
- 哪些异常状态、空状态、失败状态必须被处理？
- 如果只能保留 2-3 个质量细节，应该是哪几个？

Write into:
- Functional requirements
- Non-functional requirements
- Story acceptance focus

## Synthesis Summary Prompt

Before writing EARS requirements, summarize:

```text
## Synthesis Summary

### Stated
- User-confirmed facts and decisions.

### Inferred
- AI assumptions that need confirmation.

### Out of Scope
- Explicit exclusions and deferred capabilities.
```

If the user changes inferred items substantially, return to the relevant Phase 1 dimension before drafting.
