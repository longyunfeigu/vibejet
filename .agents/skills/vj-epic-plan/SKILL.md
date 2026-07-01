---
name: vj-epic-plan
description: 以一个 Epic（含若干 Story）为单元生成适合人工 Review 且可供下游执行的实现计划（HOW），并在命中 API、持久化或 UI Surface/Route 变化时同步维护 docs/project/api/、docs/project/data/ 与 docs/project/ui/ 模块化契约目录。在 vj-epic-story 之后、vj-work 之前使用。用户说"规划 epic X""给 epic 出实现计划""epic plan""epic 详规"时使用。
---

# vj-epic-plan — Epic 级实现计划

把一个已拆好的 Epic（`docs/tasks/epics/` 下的 epic.md + stories）转成一份**可执行的实现计划**。

**职责边界**：
- Epic/Story（**WHAT**，含可执行 `验证:` 命令）由 `vj-epic-story` 产出——本 skill **不重写 AC，只链接**。
- 本 skill 负责 **HOW**，但输出分三层：**Human Review Pack**（给人建立心智模型和做技术 review）、**Task Packets**（给 `vj-work` / subagent 执行的最小上下文投影）、**Project Catalog**（API / Data / UI 的长期合同）。
- **Human Review Pack** 是一个目录，不是一个挤满内容的大文件：`README.md` 是 reviewer 入口，`design.md` 是技术设计主文档，`decisions.md` 是 D/ACD 唯一真相源。它服务 human reviewer，不服务逐步执行。
- **Task Packets**：Phase 5 review pack + catalog 定稿后，一并生成 per-task 执行文档（`work_dir` 下 `task-index.md` + 每 task 一份 7 段文档）。Task 文档是 design/decisions + catalog + Story AC 的执行投影，不是第二套真相源；供 `vj-work` 默认直接装载执行。
- 执行（落地代码）交给 `vj-work`。
- 前端设计生产已纳入主链路。本 skill 消费两类设计输入：产品/品牌方向源（`docs/project/DESIGN.md` + `docs/reference/research/designs/golden/`，通常由产品级 `ui-requirement-brief -> vj-design-md-matcher` 产出）和单屏体验源（`vj-epic-story` 页面体验地图 + 按缺口强制触发的 `ui-page-goal-structure` / `ui-state-coverage` / `ui-user-journey-audit` 产物），生成 Screen Contract 并同步到 `docs/project/ui/`。

**协作链**：
```
vj-product-requirements → vj-architecture → api-design → data-model
        → vj-epic-story (WHAT)
        → vj-epic-plan (Human Review Pack + task packets + catalog delta, 本 skill)
        → vj-work (执行)
```

**铁律**：
- 本 skill 只做计划，**不写实现代码、不跑测试**。模板里的 ERD / 时序图 / 伪代码是方向性指引，不是实现规范。
- 输出按“Human Review Pack + Task Packets + Catalog”分层。Review Pack 是 human review 主线；Task Packets 是 AI 执行入口；Catalog 是长期合同真相源。不要把三者混成一份大上下文。
- 同一决策只在 `decisions.md` 完整写一次。`README.md`、`design.md`、task docs 只引用 `D-ID` / `ACD-ID`，不要复制论证。
- **Unit 是产品语义边界**：`1 Story = 1 Implementation Unit`。不得把 Unit 按“前端 / 后端 / 数据库 / 测试”拆开；技术层只写在 Unit 的 Files / Approach / Implementation Plan 里。
- **Task 是执行投影，不是新需求层**：Unit 仍是验收边界，Task 是可并行执行边界。优先寻找可安全并行的 task，而不是默认把所有 Unit 串行化；拆分必须有稳定合同、隔离写集、独立 done signal 和明确 Unit 收口。
- **Barrier first, fan-out second**：DB schema / public API DTO / shared enum / route shell / Screen Contract / ownership policy / shared registration 等会阻塞多个 task 的内容，应先作为 barrier task 或 owner task 稳定，再按 backend capability / frontend screen fan-out 并行。不要按“repository / service / route / test”这种技术层拆碎。
- **Task done 不等于 Unit done**：task 只能表示局部执行完成；Story AC 的闭环验收仍以 Unit 为准。若 `U2 Depends U1`，只有依赖 U1 特定输出的 task 必须等待该输出稳定；不依赖该输出、写集隔离且合同已明确的 task 可以并行启动，但 Unit done 仍必须等所有 sibling tasks + Story AC / Unit Verification 通过。
- **前端按体验交付，不按 Story 拼 UI**：前端 Epic 必须先在 `design.md` 写清 UI Surface Delta，并同步到 `docs/project/ui/` catalog（Screen/Route、角色任务、区域、状态、覆盖 Unit、API-for-UI、Screen done 信号）。Story/Unit 继续负责验收追踪；UI 执行以 Screen 为组织单位，禁止为当前 Story 临时堆一个孤立按钮、表单、卡片或页面。
- **Screen Contract 是 UI 执行合同**：前端 Epic 的每个 Screen 必须有 `screen type`（front-of-house / operational / mixed）、Route、Primary Job、Role、Regions、Key States、Information Priority、Richness Floor、Forbidden Patterns、Covered Units、API-for-UI、Screen done、Design source pointers。缺任一关键字段，不得生成 frontend-composition task；回到 Story / plan 修正。
- **强制完整度，不强制跑满 skill**：清楚的 Screen 不重复跑 UI skill；但任何 Screen Contract 字段缺失时，必须按缺口补齐对应 skill 或待审批决策，不能让 `vj-work` 实现时自由发挥。
- **先有方向，再有单屏合同**：`DESIGN.md` / golden screens 是产品级品牌与视觉方向；页面体验地图和 Screen Contract 是单屏结构与状态合同。若 `DESIGN.md` 缺失/过期、品牌方向不清、或 login/signup/landing/首个空态缺 golden reference，本 skill 不得靠 plan 文案补审美；必须把“先跑产品级 `ui-requirement-brief -> vj-design-md-matcher`”列为待审批决策或阻塞项。若方向源已稳定，只补单屏结构/状态，不重跑 matcher。
- **front-of-house 特别约束**：login、signup、landing、空首屏、营销页默认 UI-critical。Screen Contract 必须显式要求品牌/产品身份、价值点或信任点、视觉锚点、主 CTA 默认可操作态、三态；明确禁止裸居中表单、左侧/背景纯空白、无品牌概念。
- **operational 特别约束**：dashboard、table-list、detail、form、settings 默认 operational。Screen Contract 必须显式要求主数据容器、工具条/筛选、统计或摘要、行/批量操作、loading/empty/error；明确禁止孤立卡片堆、巨型录入框当主视觉、无主内容锚点。
- **Backend by capability, frontend by experience**：前端质量优先的 Epic 不要求“所有后端 100% 完成后才写前端”，但必须先稳定对应 Screen 的 API / 状态 / 数据合同。执行波次应显式拆成：UI surface/API contract → backend/API capability → frontend screen composition → E2E polish。某个 Screen 依赖的合同稳定后即可进入该 Screen 的整体实现。
- **不预规划 work-time 能现读的（design/task 通用判据）**：一条信息值得进 review pack，必须满足之一——①需要用户拍的**岔路**；②并行 Unit 必须共享的**契约**；③只有站在整个 epic 才看得见的**事实**（迁移顺序、下游消费者、跨模块不变量）；④帮助 human reviewer 建立**心智模型**（问题建模、术语场景、模块边界理由、核心流程）。**单个 Unit 的执行 agent 读代码 / 读 `DESIGN.md` 就能拿到、且无歧义的事实**不要 copy 进 review pack；task docs 只引用 anchor 并摘取执行相关约束。
- **复用优先只做有用声明**：不新增固定 Reuse Scout 章节。Phase 2 codebase-scout 负责发现复用锚点；`design.md` 只写会影响模块边界、风险或 reviewer 判断的复用对象；task docs 的 `Patterns` / `Approach` 只在有明确对象时写“复用什么 / 不重写什么”。优先级：现有业务模块、repo-local shared util、项目已有依赖、官方 SDK / API / 标准协议、成熟开源库，最后才写最小新代码。
- **调研只读、限当前工作树，基线矛盾即停问**：Phase 2 所有调研（含 codebase-scout 等子代理）只读，**范围限当前工作树 / 当前分支**——**禁止 git 跨分支或历史考古**（`git show 其它分支:文件`、`git ls-tree` 别的分支、翻 commit 历史去找“别处可能有”的产物）。若当前分支基线与 epic 引用的产物矛盾（epic 引用 `DESIGN.md` / golden / 前端脚手架等，但当前分支不存在），**这本身就是 STOP-and-ASK 信号**：停下来问用户基线与意图（要基于哪条分支、是否纯后端 epic、是否先恢复基线），不要靠翻分支 / 翻历史替用户兜底调查。无人值守无法提问时，标为“假设待审批 + Confidence”并继续，绝不静默考古。
- **design.md 才是 human 技术设计主面**：它必须包含 Problem Model、Glossary by Scenario、Current Baseline、Target Architecture、Dependency Graph、Core Flows、Data Design、API Design、Invariants/Risks、Reviewer Checklist。不要把这些散落在 Appendix 里让人拼图。
- **术语必须场景化**：不要写“role 是角色”。要写“员工误点管理员资料接口时，role 决定系统放行还是 403”。每个重要术语说明场景、解决的问题、代码归属、放错层的后果、reviewer 重点看什么。
- **两张图承担两种理解任务**：`Target Architecture` 先给 **心智地图图**，只画层和责任流向，不放具体文件名；`Dependency Graph` 再给 **模块依赖图**，放本 Epic 具体模块 / 文件组和允许依赖。不要把心智地图、文件清单、migration、DTO 字段、方法意图都塞进一张图。Mermaid 是 review pack 默认图形；`architecture-diagram` 只在需要对外展示 / 导出 PNG/PDF / 汇报材料时另产出，不作为 design.md 默认产物。
- **模块边界不用大表格做首次解释**：心智地图之后，每个模块必须用叙事小节讲清：在什么真实场景里会碰到它、为什么责任放在这里而不是别处、它和相邻模块怎么协作、哪些判断必须留在外面、reviewer 应该重点看什么。表格只用于 quick check 或 decision matrix。
- **高风险流程才画清**：状态机、并发、计费、权限、判分、AI 评估、事务 / 幂等等流程，必须在 `design.md` 的 Core Flows 中用 decision table、Mermaid sequence/state、failure table 或业务伪代码说清。plan 里写业务算法和不变量，不写方法逐行实现。
- **禁止 fallback 必须显式声明**：只有当 fallback / mock / 简化实现会伪造业务真相或绕过信任边界时，才在 Unit `Execution note` 写“禁止 fallback/mock/简化实现”。允许降级的展示增强、通知重试、只读缓存回源，不要写成禁止 fallback。
- 生成正式 review pack 时删除模板注释、示例行和无关条件段。审批段没有事项时明确写“无”，不要保留空表或模板空壳。
- 项目级稳定契约使用模块化目录：API 放 `docs/project/api/`，数据模型放 `docs/project/data/`，UI Surface / Route 放 `docs/project/ui/`。命中 delta 时在 plan 阶段同步写回，不延后到实现期。
- **上下文所有权分层**：review pack 是人工 review manifest + 本 Epic delta，不是所有上下文的永久仓库。跨 Epic 稳定契约写 catalog：API → `docs/project/api/`，Data → `docs/project/data/`，UI Surface / Route → `docs/project/ui/`。AI 执行上下文写 task docs + `_execution_context.md`。后续 Epic 读取 catalog，不翻旧 review pack / legacy plan。
- 旧单文件 `docs/project/api_spec.md` / `docs/project/database_schema.md` 只作为兼容读取 fallback；新变更不要继续写入旧文件。
- **Execution Policy 取代 Flow 标签**：不再让 reviewer 消费 Flow A/B/C。保留风险触发器，但输出为 `Execution policy: fast | strict`、命中的 strict triggers、required gates（review / migration / screenshot / catalog sync）。`README.md` 放简短 policy 摘要，`task-index.md` 放执行 gate。
- **写作风格（温暖、具体、降低认知负担）**：human review pack 像资深工程师当面讲设计：先给场景，再给边界，再给流程和风险。少用标签式术语堆砌，避免“层间数据边界 / 适配层 / primitive”这类未解释的短词。契约性内容（路径、AC 的 `验证:` 命令、API / Schema / UI Delta、依赖、`D-ID`、T-ID）保持精确——大白话 ≠ 含糊。给机器看的 task docs 保持精确、可执行、少散文。

## 输入

```
vj-epic-plan epic-1                         # 按编号定位
vj-epic-plan docs/tasks/epics/epic-2-knowledge-ingestion   # 按路径
vj-epic-plan                                # 未指定则列出 epics 让用户选
```

## 配置项

```yaml
epic_plan_generator:
  epics_dir: docs/tasks/epics/
  output_dir: docs/tasks/plans/
  output_format: "{date}-epic-{N}-{slug}/"  # review pack directory
  legacy_plan_stub: "{date}-epic-{N}-{slug}-plan.md"  # compatibility入口，只放摘要+链接
  templates:
    readme: .agents/skills/vj-epic-plan/references/plan-pack-readme.template.md
    design: .agents/skills/vj-epic-plan/references/plan-pack-design.template.md
    decisions: .agents/skills/vj-epic-plan/references/plan-pack-decisions.template.md
    legacy_stub: .agents/skills/vj-epic-plan/epic-plan.template.md
  design_docs:
    architecture: docs/project/architecture.md
    design_system: docs/project/DESIGN.md
    legacy_design_guidelines: docs/project/design_guidelines.md
    ui_designs_dir: docs/reference/research/designs/
    api_dir: docs/project/api/
    api_conventions: docs/project/api/conventions.md
    data_dir: docs/project/data/
    data_overview: docs/project/data/overview.md
    ui_dir: docs/project/ui/
    ui_surfaces: docs/project/ui/surfaces.md
    ui_routes: docs/project/ui/routes.md
    legacy_api_fallback: docs/project/api_spec.md
    legacy_data_fallback: docs/project/database_schema.md
  learnings_dir: docs/solutions/     # 优雅可选：存在且非空才检索
  learnings_agent: vj-learnings-researcher
  task_docs:                          # Phase 5 一并生成的 per-task 执行文档（vj-work 直接消费）
    work_dir: docs/tasks/work/epic-{N}-{slug}/   # task-index.md + 每 task 一份 7 段文档
    index_template: .agents/skills/vj-epic-plan/references/task-index.template.md
    template: .agents/skills/vj-epic-plan/references/task-doc.template.md
```

---

## 模块化契约目录

```text
docs/project/
├── api/
│   ├── conventions.md       # 全局 API 约定 + 模块索引
│   └── {module}.md          # 模块端点契约
├── data/
│   ├── overview.md          # 模块索引 + 表索引 + 跨模块关系
│   └── {module}.md          # 模块实体 / 表 / 索引 / migration
└── ui/
    ├── surfaces.md          # Screen / Route / Primary Job / State / owner Unit 合同
    └── routes.md            # 路由、角色、守卫、导航入口与跨 Epic 占位关系
```

最小结构：
- `api/conventions.md`：版本前缀、鉴权、响应 / 错误、分页 / 幂等约定、模块索引。
- `api/{module}.md`：模块范围、端点表、请求 / 响应 schema、错误与鉴权备注。
- `data/overview.md`：模块索引、表索引、跨模块 ERD / 关系、共享持久化约定。
- `data/{module}.md`：模块范围、ERD、表字段、索引 / 约束、一致性、migration / 回滚。
- `ui/surfaces.md`：跨 Epic 稳定 Screen 合同。每个 Surface 记录 route、role、primary job、regions、key states、API-for-UI、screen done、introduced/updated by。
- `ui/routes.md`：路由树、角色守卫、导航入口、占位页面与后续 Epic 填充关系。
- `ui/surfaces.md` 对 front-of-house / operational 都必须记录屏型、富度地板和禁止项；这些字段是 `vj-work` 判断 UI-critical 与截图 gate 的输入。

---

## 工作流（5 Phase）

### Phase 1：初始化与定位 Epic（不询问）

1. 解析输入 → 定位 epic 文件（平铺 `epic-N-<slug>.md` 或展开 `epic-N-<slug>/epic.md` + `stories/`）。未指定则 `ls docs/tasks/epics/` 列出让用户选。
2. 读 epic.md（概述、用户旅程、页面体验地图、Success Criteria、Story 列表、依赖关系图、System-Wide Considerations）+ 全部 story（含 AC 的 `验证:` 三要素）。
3. 读 review pack 模板：`references/plan-pack-readme.template.md`、`references/plan-pack-design.template.md`、`references/plan-pack-decisions.template.md`，以及 task 模板 `references/task-index.template.md` / `references/task-doc.template.md`。`epic-plan.template.md` 仅作为旧单文件兼容入口，不再承载完整设计。
4. **续作判断**：若 `docs/tasks/plans/{date}-epic-{N}-{slug}/` 或旧 `*-plan.md` 已有本 epic 的 plan,问用户「就地更新 / 新建」；更新则只改仍相关的小节，并重新生成 task docs 保持投影一致。

### Phase 2：并行收集上下文

#### 2.0 准备 epic_context（内联，不派代理）

从 Phase 1 读到的 epic.md 提炼一段结构化摘要，供所有研究代理注入：

```
Epic: epic-{N}-{slug}
目标摘要: {1-2 句，来自 epic.md 概述}
业务域 slug（lower-kebab-case）: {逗号分隔，从 epic.md 的 Activity/Domain 推导}
上游依赖 Epic: {epic-N 列表，无则”无”}
是否前端 Epic: {true/false，依据 epic.md 中的技术层判断}
Epic ID（设计稿路径用）: {epic-N}
设计来源候选: docs/project/DESIGN.md（优先）/ docs/reference/research/designs/golden/（屏型金标准）/ docs/project/design_guidelines.md（fallback）/ docs/reference/research/designs/{Epic ID}/
```

#### 2.1 并行派发研究代理

读 `references/research-agents.md` 获取代理模板，然后按当前运行时能力派发以下只读研究任务。优先并行；没有可用 subagent 时退化为主上下文顺序读取，但必须在输出里标注“research inline fallback”。

| 运行时 | 派发方式 | 约束 |
|--------|----------|------|
| Claude Code | `Agent`，`run_in_background: true` | 只读；不改文件 |
| Codex | `multi_agent_v1.spawn_agent`（若工具暴露） | 只读；不要要求 worktree 写入 |
| 无 subagent 能力 | 主上下文顺序执行三个模板 | 保留三份结构化结果，不能省略任一视角 |

研究任务：

- **Agent A — design-context**：注入 `{epic_context}`，收集架构约定与模块化 API / Data / UI 契约
- **Agent B — upstream-contracts**：注入 `{epic_context}`，**从 catalog**（`docs/project/api/`、`docs/project/data/`、`docs/project/ui/`）提取上游契约生成 Consumes（不再挖上游 review pack / legacy plan 的 Provides）
- **Agent C — codebase-scout**：注入 `{epic_context}`，侦察可复用代码与设计上下文
- **Agent D — vj-learnings-researcher**（条件）：仅当 `docs/solutions/` 存在且非空时派发；传 `<work-context>` = 本 Epic 的 Activity/Concepts/Domains；否则记”暂无相关沉淀”

#### 2.2 合并结果

等全部代理完成后，输出一段上下文小结（作为后续 Phase 的输入），覆盖：

- **架构与契约**：Agent A 产出的相关架构约定、现有 API / Data / UI 契约、硬约束清单
- **上游 Consumes**：Agent B 读 catalog 产出的 Consumes 列表，每项真相来源指向 `docs/project/api|data|ui/`；catalog 缺失时声明（可能上游未实现 / 未同步）
- **复用锚点**：Agent C 产出，分”直接复用 / 需改造 / 不应重建”。优先找现有业务模块 / domain service / application use case、repository / DTO / response envelope / shared util、项目已有第三方依赖、官方 SDK / API / 标准协议、成熟开源库；能复用时在 `design.md` 或 task docs 的 `Patterns` / `Approach` 写清复用对象，禁止重写 auth、permission、crypto、payment、scoring、parser、timezone、serialization、route generation、API client、response envelope、migration helper、design-system component 等已有权威实现。
- **设计上下文**（前端 Epic）：项目设计合同来源（优先 `docs/project/DESIGN.md` + `docs/reference/research/designs/golden/`，fallback `docs/project/design_guidelines.md`）、`docs/project/ui/` 既有 surface/route catalog、epic.md 的页面体验地图、Agent C 产出的设计稿文件列表，或”暂无”
- **UI Surface / Screen delta**（前端 Epic）：从既有 UI catalog + epic.md 页面体验地图 + Story AC + API/Data Delta 推导本 Epic 新增/更新的 Screen 列表、每屏屏型、主任务、覆盖 Unit、屏内区域、信息优先级、富度地板、禁止项、数据/操作合同、关键状态与 Screen done 信号；若无法推导，列为待审批决策，不自由发挥。
- **UI workflow skill input**（前端 Epic）：先判轨道。产品/品牌方向缺口（缺 `DESIGN.md`、品牌感不清、front-of-house 无 golden、用户要求整体视觉升级）→ 标记需先跑产品级 `ui-requirement-brief -> vj-design-md-matcher`，不要在 plan 里临时发明风格；单屏结构/状态缺口（已有方向源，但某 Route 的主任务、区域、状态、富度地板或禁止项不清）→ 强制补 `ui-page-goal-structure` / `ui-state-coverage` 的检查口径；命中复杂操作流判定时强制补 `ui-user-journey-audit`。复杂操作流按特征判定，不按页面名白名单：连续 2 步以上、存在权限/资格/库存/余额/次数/审核/风控/依赖数据判断、不可轻易撤销动作、恢复路径，或会改变业务状态/影响下游。结果只进入 Screen Contract，不生成 v0/Lovable 提示词。
- **institutional learnings**：Agent D 产出，或”暂无相关沉淀”
- **隐含约束小结**：综合以上，列出计划阶段需遵守的非显式约束

### Phase 3：Execution Policy + Review Gate

按风险触发器判定执行策略，scope = 本 Epic。不要输出 Flow A/B/C 给 reviewer。

1. 回答风险触发器 → 判 **Execution policy: fast | strict**。任一命中即 strict：改 DB migration/schema、改公共 API contract、改权限/安全/ownership/tenant、引入外部系统/异步任务、复杂状态机/幂等/事务、一处不清会改变行为、跨 BC、UI shell/navigation/design token、预计大 diff。
2. 在 review pack 的 `README.md` 记录 execution policy 与 required gates，在 `task-index.md` 投影执行 gate；不要让 human reviewer 消费 Flow A/B/C。
3. 把 AC 没写也推不出、会改变范围或验收口径的事项集中到 `decisions.md`。有用户在场 → 用当前平台的阻塞提问能力询问（Claude `AskUserQuestion`；Codex/无该工具时列编号选项并等待用户回复），不要猜一个值。**无人值守 / 作为 subagent 运行（无法提问）→ 标为“假设待审批”，写最合理假设与 Confidence，不阻塞**。两种情况都绝不静默跳过。
4. 若技术方案与 Story AC 的 `验证:` 命令冲突，登记到 `decisions.md` 的 AC Deviations，并在 `README.md` 的 Known Conflicts 摘要列出。原则上回改上游 epic.md / story AC；确需保留偏离时等待 reviewer 显式批准。**不得用“等价口径”静默覆盖 AC**。
5. Scope Challenge 四问，挡 scope creep。

> 所有 review pack 都填：`README.md`（review entry + conflicts + execution sketch + catalog touched）、`design.md`（human 技术设计主文档）、`decisions.md`（D/ACD 唯一真相源）。
> Story 依赖与并行与 policy 无关：本 Epic 含 ≥2 个 Story 即在 `task-index.md` 填 Unit DAG + Task DAG / 波次。优先生成可安全并行的 Task DAG，但 Unit done 仍由 Story AC / Unit Verification 闭环。

### Phase 4：结构化（生成 review pack 草稿）

1. **`README.md`（human reviewer 入口）**：
   - 写 One-Screen Summary：本 Epic 解决什么、不解决什么、reviewer 先看哪些文件、catalog touched、execution policy。
   - 写 **Known Conflicts**：story / review pack / catalog / 当前代码基线不一致必须列出；无则写“无”。不能静默用 review pack 覆盖 story AC。
   - 写 Reviewer Reading Path：先冲突，再 design，再 decisions，再 task-index。
   - 写短 Execution Sketch：只放 barrier、可并行、收口、required gates；详细 DAG 放 task-index。
   - 写 Catalog Sync 摘要：目标文件和状态（pending / synced / N/A）。

2. **`decisions.md`（决策与 AC 偏离唯一真相源）**：
   - 待审批事项、AC 偏离、已确认关键决策（带 `Rejected:`）集中写在这里。
   - 技术方案与 Story AC 的 `验证:` 命令冲突时必须列 ACD，并在 README Known Conflicts 摘要引用。
   - 范围偏离（如 FE 延后、真实端点延后、临时探针等）不得只写在 task docs；必须列入 decisions。

3. **`design.md`（human 技术设计主文档）**：
   - 必填 10 段：Problem Model、Glossary by Scenario、Current Baseline、Target Architecture、Dependency Graph、Core Flows、Data Design、API Design、Invariants/Risks、Reviewer Checklist。
   - **Problem Model**：用场景讲清楚此 Epic 真正在解决的问题和明确不做的内容。
   - **Glossary by Scenario**：术语必须有场景、解决的问题、代码归属、放错层后果、reviewer 重点。
   - **Target Architecture**：先给心智地图图，只画层和责任流向，不放文件名；再按模块小节解释边界；不要用大表格作为首次理解载体。
   - **Dependency Graph**：再给模块依赖图，放本 Epic 具体模块 / 文件组、允许依赖和禁止依赖；不要把所有文件细节塞进 Target Architecture。
   - **Core Flows**：权限、状态、事务、幂等、AI 评估、外部调用等高风险流程必须用 decision table、Mermaid sequence/state、failure table 或业务伪代码表达。
   - **Data/API Design**：写 delta、为什么这样设计、为什么不是备选方案、兼容性和错误语义。
   - **Reviewer Checklist**：写人真正该审的风险点，不写执行步骤。

4. **跨 Epic 契约与 catalog sync**：
   - `Consumes` 仍由 Phase 2 Agent B 从 catalog 生成，但放进 `design.md` 或 `README.md` 的引用段即可；不要写旧式 Provides 表。
   - 本 Epic 对下游的稳定契约只写进 catalog：API → `docs/project/api/`，Data → `docs/project/data/`，UI → `docs/project/ui/`。
   - 跨切面义务 / 不变量写入 `docs/project/data/overview.md`、`docs/project/api/conventions.md` 或 `docs/project/ui/surfaces.md`，不要只留在 old plan。

5. **Unit / Task 编排**：
   - 每个 Story → 一个 Unit；Unit 是产品语义边界。
   - 识别 barrier / owner tasks：schema、DTO、shared enum、route shell、Screen Contract、shared registration、ownership policy、catalog sync 等共享输出先稳定。
   - 生成 Task DAG / 波次，但详细表写入 `task-index.md`，README 只写执行概览。
   - 共享文件冲突必须逐一检查（常见序列化点：`unit_of_work.py`、`models/__init__.py`、`main.py`、`dto.py`、`apiClient.ts`、`routeTree.gen.ts`）。
   - 前端 Epic 必须保留 Execution lane / Frontend composition waves：UI surface/API contract → backend/API capability → frontend screen composition → E2E polish。Screen composition 的启动条件是该 Screen 依赖的 API / 状态 / 数据合同稳定，不是所有后端完成。

6. **Test scenarios / fallback / risk**：
   - Story AC 的 `验证:` 命令仍是验收基础。实现涌现型、用户可观测的新行为用例应回流到 story AC 或 decisions ACD，不藏在 task。
   - 纯实现级用例投影到 task docs。
   - 只有 fallback/mock/简化实现会伪造业务真相或绕过信任边界时，才在 task 的 Execution note 写禁止 fallback。

### Phase 5：写盘 + 自检 + 生成 task 文档 + Handoff

1. **写 draft review pack**：先写 `docs/tasks/plans/{date}-epic-{N}-{slug}/README.md`、`design.md`、`decisions.md`。同时写一个旧路径兼容 stub `docs/tasks/plans/{date}-epic-{N}-{slug}-plan.md`（只放摘要与链接，不承载完整设计）。此时 catalog 同步延后到 plan review 之后。
2. **自检清单**:
   - [ ] `README.md` 第一屏能让 human reviewer 5 分钟内知道本 Epic 解决什么、不解决什么、先看哪里、哪些冲突还没清理
   - [ ] `README.md` 的 Known Conflicts 列出了 story / review pack / catalog / 当前代码基线冲突；无冲突时明确“无”
   - [ ] `design.md` 按 10 段结构完整生成：Problem Model、Glossary by Scenario、Current Baseline、Target Architecture、Dependency Graph、Core Flows、Data Design、API Design、Invariants/Risks、Reviewer Checklist
   - [ ] `Target Architecture` 有心智地图图（层和责任流向，少文件名），`Dependency Graph` 有模块依赖图（具体模块 / 文件组 + 禁止依赖），没有把两类图混成一张高密度文件图
   - [ ] `design.md` 的术语解释用了场景，不是平淡定义；每个重要术语有代码归属和 reviewer 重点
   - [ ] `design.md` 的模块边界按叙事小节解释真实场景、归属理由、相邻模块协作和边界风险，没有用大表格作为首次理解主载体
   - [ ] 高风险状态 / 权限 / 事务 / 判分 / AI 评估流程已在 `design.md` 用 decision table、Mermaid state/sequence、failure table 或业务伪代码写清
   - [ ] `decisions.md` 是 D/ACD 唯一真相源；其他文件只引用 ID，不复制完整论证
   - [ ] 待审批项已问用户 **或**（无人值守时）已转为“假设待审批” + Confidence，无未标注的隐性猜测
   - [ ] 每个 Story 都对应一个 Unit；Unit 文件路径均 repo 相对；Unit done 不被 task done 替代
   - [ ] 已生成 Task DAG / 波次；barrier / owner tasks、Unit→Task 映射、共享文件冲突点、每 task done signal 都明确
   - [ ] 未因“前端 / 后端分离”或技术层本身拆 task；拆分理由指向 barrier、capability、screen、文件隔离、验证边界或并行收益
   - [ ] Test scenarios 链到了 Story 的 `验证:` 命令，未静默重写 AC；冲突已登记到 `decisions.md`
   - [ ] (≥2 Story 时) task-index 的 Unit DAG / Task DAG 与 epic.md 的 `**依赖**:` 行一致
   - [ ] Consumes 每项真相来源指向 catalog（`docs/project/api|data|ui/`）；没有旧式 Provides 表
   - [ ] API / Data / UI delta 已列出目标 catalog 文件；无 delta 时未创建空文档
   - [ ] (前端 Epic)Screen Contract 完整度已过 gate；缺目标/结构/状态/复杂操作流时已补对应 UI skill 或列为待审批阻塞
   - [ ] (前端 Epic)每个新增/更新 Screen 有 Route / Screen type / Primary Job / Role / Covered Units / Regions / Information Priority / Richness Floor / Forbidden Patterns / States / API-for-UI / Screen done；无 Screen 合同不得生成 UI task
   - [ ] Execution Policy 与 required gates 一致；无 Flow A/B/C 作为 human-facing 审批口径
   - [ ] 执行细节没有污染 human docs；详细 task 文件范围、write scope、验证命令在 task docs
3. **自动 review pack 审查(vj-plan-review)**:draft review pack 写盘后**自动**按运行时适配器执行 `vj-plan-review`（Claude/Codex 可派只读审查子任务；无 subagent 能力时在主上下文同步执行）做多视角独立审查(一致性/可行性/范围/对抗/依赖并行/UI surface/human-readable design)→ 自主判断采纳 → 修正 review pack;用户可说"跳过审查"中断。**epic-plan 的独立审查走 vj-plan-review,不再走 codex-review**。
4. **定稿写盘 + Catalog Sync**:
   - 收取 `vj-plan-review` 结果并自主采纳后，先重写最终 `README.md` / `design.md` / `decisions.md` / legacy stub。
   - 若命中 API delta，同步写入对应 `docs/project/api/conventions.md`（如需）与 `docs/project/api/{module}.md`；只有全局约定变化时才改 `conventions.md`。
   - 若命中 Schema / persistence delta，同步写入 `docs/project/data/overview.md` 与 `docs/project/data/{module}.md`。
   - 若命中 UI Surface / route delta，同步写入 `docs/project/ui/surfaces.md` 与 `docs/project/ui/routes.md`。
   - 同步后复核：最终 review pack 的 API/Data/UI delta 与 catalog 文档完全一致；不一致则以最终 review pack 的 delta 修正 catalog，不允许留下“后续再同步”。后续 Epic 的跨 Epic 真相源是 catalog，不是旧 review pack / legacy plan。
   - 将 `README.md` 的 Catalog Sync 表更新为 `synced` / `N/A`。
   - 确认 review pack 路径和本次同步的 catalog 文件绝对路径（可点击）。
5. **生成 / 更新 task 文档**（review pack + catalog 定稿后，供 vj-work 直接消费）:
   - 时机:**在 vj-plan-review 修正之后**，确保 task 文档投影自定稿 `design.md` + `decisions.md` + 已同步 catalog。续作 / 重跑时**整目录覆盖重写**(每次写盘都重生成，不做增量 diff)——task 文档是执行投影，不是跨 Epic 稳定上下文的长期真相源，也不是新的决策真相源。
   - 落点:`task_docs.work_dir`(`docs/tasks/work/epic-{N}-{slug}/`),内含 `task-index.md` + 每个 task 一份 `T{NNN}-{slug}.md`(7 段文档)。旧索引文件不再生成；如旧目录存在，重跑时用 `task-index.md` 覆盖执行入口。
   - 拆 task:以 Phase 4 推导并写入 `task-index.md` 的 **Task DAG / 波次** 为准。默认先寻找可并行 task；拆分必须满足：合同稳定、写集隔离或 owner 明确、每 task 有局部 done signal、能缩短 critical path 或降低上下文、不会把 task done 当 Unit done。若 task 太小且无独立验证，就合并进同一 task。
   - Barrier / owner task 优先：schema / migration、public DTO、shared enum、route shell、Screen Contract、shared registration、ownership policy、catalog sync 等共享输出必须先稳定或由单一 owner task 处理，再 fan-out 并行。
   - 不允许的拆法：只因“前端 + 后端”、只因“repository / service / route / test 分层”、或为了凑并行而生成没有独立验证的 task。
   - 生成 **task 级 DAG / 波次 / 共享文件冲突表** 写入 `task-index.md`，标明每个 task 回指哪个 Unit、是否 partial task、sibling tasks、Unit done 信号，并明确 “task done != Unit done”。下游 task 只需等待它实际依赖的上游 contract / artifact 稳定；Unit done 仍需所有 sibling tasks + Story AC / Unit Verification。
   - 生成内容:按 `task_docs.template`(`references/task-doc.template.md`)投影自 `design.md` / `decisions.md` 与 catalog：Goal/Files/Approach/Patterns/Test scenarios/Verification、design anchors、decision anchors、catalog anchors、write scope、read-first source pointers、relevant constraints、non-goals、stop conditions。不重新发明 HOW;「变更叙事」段保留 `_(待执行)_` 占位,由 vj-work 按 fast/strict 记录策略回写（fast 可 Phase 4 统一回写, strict 每 task 回写；Unit 收口 task 记录 Unit Verification）。若 `design.md` 声明高风险业务流程图 / 伪代码、不变量，或 `decisions.md` 声明禁止 fallback/mock/简化实现，必须投影进 task 文档的 Technical Approach / Execution note。
   - **UI Unit 检测 + Design / Screen context 注入**:某 Unit 的 `Files:` 含 `.tsx`、或路径含 `routes/`/`features/`/`components/` → 判为 UI Unit,把模板末尾「附:UI Unit Design / Screen context 注入块」原样复制进该 task 文档的 `## 3. Technical Approach` 段末，并填入本 Epic 对应的 `DESIGN.md` / fallback 来源、`docs/project/ui/` catalog 指针、页面体验地图条目、UI Surface Delta 中的 Screen ID / Route / Screen type / Primary Job / 覆盖 sibling Units / 屏内区域 / 信息优先级 / 富度地板 / 禁止项 / API-for-UI / Screen done / 需覆盖的 UI 状态。非 UI Unit 不注入。
   - **Frontend composition task 投影**:若同一 Screen 覆盖多个 UI Unit，task 文档必须标明这是“Screen composition”还是“backend/API capability”。Screen composition task 可以覆盖多个 Unit 的 UI AC，但 Unit done 仍需回指各自 Story AC / Verification；不得为每个 Story 生成互相割裂的页面片段。
   - 生成 `task-index.md`:波次计划直接来自 Phase 4 推导的 Task DAG；必须保留 Unit DAG、Task DAG、Barrier / owner task 列表、Unit→Task 映射表、共享文件冲突表、Execution Policy。
   - **不提交、不开 worktree**:本 skill 只写盘,与 plan 一样留未提交态。分支决策、`_execution_context.md`、docs-context 提交与 worktree 创建由 vj-work 按 execution mode 负责（fast 不审批,但若执行 worktree 需要读取 task/context 文件则自动提交可见上下文; strict 动代码前提交）。
   - 生成后自检:每个 Unit 都有对应 task 文档或 sibling task 集;每个 task 有 design anchors / decision anchors / catalog anchors / write scope / verification / stop conditions;UI Unit 已注入 Design / Screen context 块;`task-index.md` 波次与 README execution sketch 一致;「变更叙事」段为 `_(待执行)_` 占位。
   - 告知 work_dir 绝对路径(可点击)。
6. **Handoff**:告知 review pack 路径 + task 文档 work_dir 路径,并提供下一步选项:
   - `vj-work` 执行本 review pack:task 文档已在 step 5 生成,vj-work **直接装载 task packets + `task-index.md` 执行**(不重新生成),并生成 `_execution_context.md`;默认不全文读取 review pack，只在 task anchor / strict trigger / 歧义 / 冲突时回读 `design.md` / `decisions.md` 对应章节。分支、worktree 与记录/提交粒度由 vj-work 的 auto/fast/strict 模式决定。
   - 告知本次同步更新的 `docs/project/api/` / `docs/project/data/` / `docs/project/ui/` 文件；后续实现若偏离，下游再报告差异并回写对应模块文档。
   - 进一步打磨 review pack(**改完会触发 step 5 重新生成 task 文档**,保持二者同步)。
   > 定位:epic-plan 是**human review pack + task packet 生成器**。Unit 依赖的真相源仍是 epic.md 的 `**依赖**:` 行——`task-index.md` 的 Unit DAG 必须与其一致。

## Stop Conditions（防死循环）

- 同一用户确认 gate(Phase 3 需确认 / Phase 5 自检)反馈 ≥3 次 → 弹「继续 / 重审上游 epic / 放弃」。
- 实现前发现 Execution Policy 判错(漏了改 DB/契约/权限等 strict trigger)→ 暂停,切 strict,重填受影响小节与 task packets。

## 与学习飞轮的关系

- **读**:Phase 2 调 `vj-learnings-researcher` 检索 `docs/solutions/`。
- **写**:本 skill 不写学习;一个 Story/Epic 实现收尾、踩了坑或定了非平凡决策后,用 `vj-compound` 沉淀,供未来的 vj-epic-plan 复用。
