---
name: prd-generator-ears
description: Turn a fuzzy product idea into a structured PRD using EARS syntax. Use when the user has a feature or product concept that still needs clarification, product framing, scope challenge, role definitions, epics, and testable requirements before architecture or Story breakdown.
---

# prd-generator-ears

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
- 产品或功能想法
- 目标用户
- 核心问题
- 预期结果
- 已知约束

生成 PRD 前必须读取同目录下的：
- `prd_template.md`

## 核心原则

1. 先挑战问题定义，再写需求。
2. PRD 关注用户结果和产品边界，不提前滑向技术实现细节。
3. 每条关键需求必须可测试、可验证、可继续拆成 Story。
4. 默认 `Standard` 范围模式，既不过度扩 scope，也不机械压缩；按 stage 与需求体量调整到 `Lightweight` 或 `Deep`。
5. 区分需求来源：用户明确输入、外部调研证据、模型推断，不混为一谈。

## Workflow

### Phase 0: Triage + Pressure Test

在写 PRD 之前，先做轻量分流（Triage）和盲区逼问（Pressure Test）。这一步不能跳。

#### Resume Check

如果用户引用了已有 PRD，或 `docs/` 下存在同名 PRD 文件：
- 读取文件
- 向用户确认："找到已有 PRD `<path>`，要在此基础上继续，还是重新开始？"
- resume 时，简述当前状态、保留已有决策与未决问题，**更新原文件而不是新建**

#### Stage Routing

判断当前需求所处阶段，跑不同深度的挑战：

| Stage | 判定信号 | Pressure Test 重点 |
|-------|----------|--------------------|
| **新产品 0→1** | 还没有产品/用户/付费 | 全 4 lens：Evidence + Specificity + Counterfactual + Attachment |
| **已有产品加功能** | 产品已运行、有用户 | Counterfactual + Attachment（已有用户即证据，跳过 Evidence/Specificity） |
| **内部工具 / 管理系统** | 服务团队内部、非外部商业用户 | Counterfactual + Specificity（角色 + 频率） |
| **纯技术债 / 合规改造** | 不直接改用户行为，改技术约束 | 仅 Counterfactual + 影响半径 |

不清楚 stage 时，用一个问题向用户确认（AskUserQuestion）。

#### Scope Mode

根据 stage 和需求体量，选择/确认范围模式：

- `Lightweight`
  - 最小可交付范围，剔除次要内容
- `Standard`（默认）
  - 聚焦合理范围，形成可执行 PRD
- `Deep`
  - 更完整、有产品野心的版本，额外触发 Durability lens

#### Gap Lenses Pressure Test

按 stage 路由结果，使用 4-5 个 gap lens 逼问需求盲区。**目标是把模糊命题逼成可写入 PRD 的具体陈述**，不是吓退用户。

**Evidence Gap（证据缺失）— 仅 0→1 stage 必问**
> 用户已经为这个问题做过什么具体行为？付过钱、搭过手工流程、抱怨过、绕过过？不是"觉得有用"是"已经发生过的事"。

**Specificity Gap（具体性缺失）**
> 真实使用人是哪个角色（运营 / 客服 / 管理员 / 外部合作伙伴）？这个事件多久发生一次？说不出角色或频率，对象就还没收敛。

**Counterfactual Gap（反事实缺失）— 所有 stage 必问**
> 现在没有这个功能，用户怎么扛？手工 Excel？跨系统切换？同事帮忙？这个 workaround 的真实成本是什么（时间 / 出错率 / 沟通成本）？

**Attachment Gap（方案附着缺失）**
> 把"必须做成这个形态"的执念剥掉。能交付同样价值的最小版本是什么？例：是真的需要"全功能管理后台"，还是一个邮件通知 + 一个查询接口就够？

**Durability Gap（耐久缺失）— 仅 `Deep` 范围模式必问**
> 12 个月内可预见的变化（团队结构、外部依赖、合规规则、上游平台）会让这个押注失效吗？

#### 非目标

明确本次 PRD 不解决什么、什么内容延后到后续版本。这一步不能省。

#### 挑战纪律

- 用户答案暴露真实不确定性时，记入 Phase 4 的 `[未验证假设]`，不要绕过
- 不要把整套重型 review 机制搬进来（CEO review / 战略推演不在本 skill 范围）
- Pressure Test 是**为 PRD 收敛服务**的，不是产品论证大会

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

按以下 6 个维度做澄清。**纪律**（硬规则）：

- **每个 turn 只问一个问题**，不要把多个子问题堆在一起
- **优先 single-select 多选**（用 `AskUserQuestion` 工具），让用户从选项中选 + free-text 兜底
- **multi-select 仅用于天然可共存的集合**（目标、约束、非目标）；如果选项之间有优先级，再追问"哪个最关键"
- **完全开放式提问只在答案天然是叙述时用**（如"讲讲你怎么走到这一步的"）
- 进入下一维度前，对当前维度收敛到能明确写入 PRD 的具体陈述

按以下顺序：

1. 目标用户
   - 核心用户是哪个角色？
   - 他们在什么场景下会用这个产品？

2. 核心痛点
   - 现在最痛的问题是什么？
   - 当前替代方案是什么？为什么不够好？
   - （Phase 0 Counterfactual lens 已问过的，补足量化成本）
   - （Phase 0.5 调研已执行的，调研发现的 Gaps 是否和用户感知一致？）

3. 核心结果
   - 用户使用后最关键的成功结果是什么？
   - 业务上希望看到什么指标变化？

4. 核心流程
   - 用户完成核心任务的主路径是什么？
   - 流程里最容易失败或流失的是哪一步？

5. 关键边界
   - 哪些角色会参与？
   - 权限、合规、性能、外部依赖有哪些限制？

6. 产品质量加分项
   - 哪些"用户会觉得被认真思考过"的体验值得写进 PRD？
   - 只保留真正有价值的 2-3 个，不要堆功能清单

### Phase 2: PRD Skeleton

基于澄清结果，先形成 PRD 骨架：
- 产品概览
- 角色定义
- Epic 划分
- 非功能需求
- 假设、依赖与约束
- （如果做了调研）市场与替代方案摘要

要求：
- Epic 按用户目标和业务能力分组
- 不按技术模块分组
- 每个 Epic 都应可继续拆成 Story
- 如果 Phase 0.5 识别了 Table Stakes，确保 Epic 覆盖这些基线能力

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

生成草案后，必须做一次质量检查。**先做机械检查，机械检查不通过不进入内容质量检查**。

#### 0. 机械检查（先做）

- **Placeholder 扫描**：搜索 `TBD` / `TODO` / `[填写]` / `<待定>` / `未定` 等占位符 → 必须补完或显式删除
- **内部一致性**：Epic 之间是否相互矛盾？需求与角色错配？非功能需求与功能需求冲突？
- **歧义检查**：同一条需求能否被两种合理方式解读？如果是，选一种并显式说明
- **范围一致性**：Phase 2.5 Synthesis Summary 里的 Stated / Out of scope 是否在 PRD 文档里得到落实？

机械检查不通过的项，必须先修复，再进入内容质量检查。

#### 1. 问题与目标
- 是否清楚写明用户问题和目标结果？
- 是否有明显的代理问题或伪需求？

#### 2. Scope
- 是否写明本次不做什么？
- 是否存在明显 scope creep？

#### 3. 可测试性
- 每条关键需求是否可验证？
- 是否存在模糊词，如"友好""快速""智能"，但没有可操作定义？

#### 4. Epic 质量
- Epic 是否围绕用户价值组织？
- 是否存在"按页面/按技术层拆 Epic"的问题？

#### 5. 需求溯源
- 每条需求的来源是否可追溯？
- 标注分类：
  - `[用户]` — 用户在对话中明确提出
  - `[调研]` — 来自 Phase 0.5 外部调研，附来源
  - `[推断]` — AI 基于上下文推断，需用户确认
- 存在 `[推断]` 标记的需求，必须在质量门禁中提醒用户确认

#### 6. 继续向下游传递的可用性
- 这份 PRD 是否足够支持 `architecture`
- 是否足够支持 `epic-story-generator`

如果质量不足，不要急着交付，先做一轮精简或补充。

## 输出要求

输出必须严格遵循：
- `prd_template.md`

最终产物至少包括：
1. 产品概览
2. 角色定义
3. 按 Epic 分组的 EARS 需求
4. 非功能需求
5. 假设、依赖与约束

当 research_mode 为 `light` 或 `deep` 时，还必须包括：
6. 市场与替代方案
7. 证据与来源
8. 待验证假设

建议额外明确：
- 本次 stage：`新产品 0→1 / 已有产品加功能 / 内部工具 / 纯技术债`
- 本次范围模式：`Lightweight / Standard / Deep`
- research_mode：`none / light / deep`
- 明确的非目标

## 后置步骤：Codex 审查

**PRD 生成完毕后，自动执行 `codex-review`**：
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
使用 prd-generator-ears，帮我把这个产品想法整理成 PRD
```

```text
我想做一个个人财务记账 App，使用 prd-generator-ears
```

```text
使用 prd-generator-ears，先 challenge 一下这个需求，再输出 EARS 格式 PRD
```

```text
使用 prd-generator-ears，research_mode=deep，先做竞品调研再出 PRD
```
