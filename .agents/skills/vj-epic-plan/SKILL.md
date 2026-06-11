---
name: vj-epic-plan
description: 以一个 Epic（含若干 Story）为单元生成适合人工 Review 且可供下游执行的实现计划（HOW），并在命中 API、持久化或 UI Surface/Route 变化时同步维护 docs/project/api/、docs/project/data/ 与 docs/project/ui/ 模块化契约目录。在 vj-epic-story 之后、vj-work/run-epic 之前使用。用户说"规划 epic X""给 epic 出实现计划""epic plan""epic 详规"时使用。
---

# vj-epic-plan — Epic 级实现计划

把一个已拆好的 Epic（`docs/tasks/epics/` 下的 epic.md + stories）转成一份**可执行的实现计划**。

**职责边界**：
- Epic/Story（**WHAT**，含可执行 `验证:` 命令）由 `vj-epic-story` 产出——本 skill **不重写 AC，只链接**。
- 本 skill 负责 **HOW**：人工 Review 摘要、待审批决策、Triage 分级、跨 Story 共享设计（ERD/流程/本 Epic UI Surface delta）、跨 Epic 契约（Consumes；对下游契约写入 catalog 而非 plan）、每个 Story 的实现单元、**Story/Unit 依赖图、可选 task 执行投影与并行波次**、关键决策（带 Rejected），以及项目级 API / Data / UI catalog 同步。
- **产出执行投影**：Phase 5 plan 定稿后，一并生成 per-task 执行文档（`work_dir` 下 7 段文档 + `_ledger.md`），供 `vj-work` 直接装载执行——避免执行期重做投影。
- 执行（落地代码）交给 `vj-work` / `run-epic`。

**协作链**：
```
vj-product-requirements → vj-architecture → api-design → data-model
        → vj-epic-story (WHAT)
        → vj-epic-plan (HOW + task 文档, 本 skill)
        → vj-work / run-epic (执行)
```

**铁律**：
- 本 skill 只做计划，**不写实现代码、不跑测试**。模板里的 ERD / 时序图 / 伪代码是方向性指引，不是实现规范。
- 输出按“人工 Review 主线 + 执行 Appendix”组织。流程图、ERD、API / Schema / UI Delta、跨 Epic 契约、Unit DAG 留在正文；文件级清单、复用锚点、冲突表、提交步骤下沉到 Appendix。
- 同一决策只在 `## 2. 决策与 AC 偏离` 完整写一次。其他章节引用 `D-ID`，不要复制论证。
- **Unit 是产品语义边界**：`1 Story = 1 Implementation Unit`。不得把 Unit 按“前端 / 后端 / 数据库 / 测试”拆开；技术层只写在 Unit 的 Files / Approach / Implementation Plan 里。
- **Task 是执行投影，不是新需求层**：默认 `1 Unit = 1 task`。只在依赖、文件隔离、验证边界和并行收益都清楚时拆 task；“这个 Unit 同时有前端和后端”不是拆分理由。前端 Epic 只有在 UI Surface Delta / catalog 明确要求按 Screen/Route 聚合实现时，才允许生成 Screen composition task；该 task 必须列 Covered Units、Screen done 与每个 Unit 的 UI AC 回指，不能变成新需求层。
- **Task done 不等于 Unit done**：task 只能表示局部执行完成；Story AC 的闭环验收仍以 Unit 为准。若 `U2 Depends U1`，U2 的任一 task 不得早于 U1 全部 task 完成后启动，避免技术层半成品越过产品依赖。
- **前端按体验交付，不按 Story 拼 UI**：前端 Epic 必须先在 §4 写清 UI Surface Delta，并同步到 `docs/project/ui/` catalog（Screen/Route、角色任务、区域、状态、覆盖 Unit、API-for-UI、Screen done 信号）。Story/Unit 继续负责验收追踪；UI 执行以 Screen 为组织单位，禁止为当前 Story 临时堆一个孤立按钮、表单、卡片或页面。
- **Backend by capability, frontend by experience**：前端质量优先的 Epic 不要求“所有后端 100% 完成后才写前端”，但必须先稳定对应 Screen 的 API / 状态 / 数据合同。执行波次应显式拆成：UI surface/API contract → backend/API capability → frontend screen composition → E2E polish。某个 Screen 依赖的合同稳定后即可进入该 Screen 的整体实现。
- **不预规划 work-time 能现读的（§4 / Appendix B / C 通用判据）**：一条信息值得进 plan，必须满足之一——①需要用户拍的**岔路**；②并行 Unit 必须共享的**契约**；③只有站在整个 epic 才看得见的**事实**（迁移顺序、下游消费者）。**单个 Unit 的执行 agent 读代码 / 读 `DESIGN.md` 就能拿到、且无歧义的事实**（现有 pattern、DESIGN.md 约束原文、单文件现状）**不要 copy 进 plan**——vj-work 现读更新鲜，也避免与真相源漂移、避免把残缺子集当完整 spec。plan 唯一不可替代之处，是“一个脑子同时看所有 Unit”把共享决策与冲突钉死，免得并行隔离子代理各读各的、各判各的。
- **复用优先只做有用声明**：不新增固定 Reuse Scout 章节。Phase 2 codebase-scout 负责发现复用锚点；Appendix C 的 `Patterns` / `Approach` 只在有明确对象时写“复用什么 / 不重写什么”。优先级：现有业务模块、repo-local shared util、项目已有依赖、官方 SDK / API / 标准协议、成熟开源库，最后才写最小新代码。
- **高风险流程才画清**：状态机、并发、计费、权限、判分、AI 评估、事务 / 幂等等 Unit，必须在 §4 或 Appendix C 用业务伪代码、Mermaid state / sequence 图或不变量把状态、分支、失败策略说清。普通 CRUD、DTO、字段映射、局部 UI binding 不加这层。
- **禁止 fallback 必须显式声明**：只有当 fallback / mock / 简化实现会伪造业务真相或绕过信任边界时，才在 Unit `Execution note` 写“禁止 fallback/mock/简化实现”。允许降级的展示增强、通知重试、只读缓存回源，不要写成禁止 fallback。
- 生成正式 plan 时删除模板注释、示例行和无关条件段。审批段没有事项时明确写“无”，不要保留空表或模板空壳。
- 项目级稳定契约使用模块化目录：API 放 `docs/project/api/`，数据模型放 `docs/project/data/`，UI Surface / Route 放 `docs/project/ui/`。命中 delta 时在 plan 阶段同步写回，不延后到实现期。
- **上下文所有权分层**：plan 是人工 review manifest + 本 Epic delta，不是所有上下文的永久仓库。跨 Epic 稳定契约写 catalog：API → `docs/project/api/`，Data → `docs/project/data/`，UI Surface / Route → `docs/project/ui/`。AI 执行上下文写 task docs + `_execution_context.md`。后续 Epic 读取 catalog，不翻旧 plan。
- 旧单文件 `docs/project/api_spec.md` / `docs/project/database_schema.md` 只作为兼容读取 fallback；新变更不要继续写入旧文件。
- **Appendix A 只做风险审计**：保留 Flow 分级、强制升级触发、影响范围、关键约束来源索引与 Scope Challenge。不要在 Appendix A 展开硬约束 / 隐含约束长清单；执行期硬约束投影到 Appendix C、task docs 与 `_execution_context.md`，稳定契约留在 catalog。
- **写作风格（说人话，且只花在该花的地方）**：人工 review 主面是 **§4 共享设计**（ERD / 流程图 / 模块边界 / 术语表）——说人话的预算花在这里：图注、术语解释、字段含义用大白话，像当面指着图讲这个 epic 怎么搭。`§0` 只是 thin 审批门（链 §2 决策），不写散文摘要。给机器看的章节（§3 / §5 / §6 / Appendix / task 文档）保持精确即可，**不需要散文润色**。契约性内容（文件路径、AC 的 `验证:` 命令、API / Schema / UI Delta、依赖、`D-ID`）保持精确——大白话 ≠ 含糊，不能借说人话把 AC 写松、文件清单写漏。砍掉 AI 腔：空话套话（"赋能 / 打通闭环 / 实现统一"）、形容词堆砌（"强大 / 灵活 / 优雅 / 健壮"）、学术腔（把"先建表再写接口"说成"基于领域驱动的持久化层先行构建"）、强行对仗排比与"首先 / 其次 / 最后"凑结构、破折号和"不仅…而且…"上瘾。自检：每段念一遍，不像在跟人口头讲就改。

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
  output_format: "{date}-epic-{N}-{slug}-plan.md"
  template: .agents/skills/vj-epic-plan/epic-plan.template.md
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
    work_dir: docs/tasks/work/epic-{N}-{slug}/   # 与 vj-work 一致：_ledger.md + 每 task 一份 7 段文档
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

---

## 工作流（5 Phase）

### Phase 1：初始化与定位 Epic（不询问）

1. 解析输入 → 定位 epic 文件（平铺 `epic-N-<slug>.md` 或展开 `epic-N-<slug>/epic.md` + `stories/`）。未指定则 `ls docs/tasks/epics/` 列出让用户选。
2. 读 epic.md（概述、用户旅程、页面体验地图、Success Criteria、Story 列表、依赖关系图、System-Wide Considerations）+ 全部 story（含 AC 的 `验证:` 三要素）。
3. 读模板 `epic-plan.template.md`,理解输出结构。
4. **续作判断**：若 `docs/tasks/plans/` 已有本 epic 的 plan,问用户「就地更新 / 新建」;更新则只改仍相关的小节。

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
设计来源候选: docs/project/DESIGN.md（优先）/ docs/project/design_guidelines.md（fallback）/ docs/reference/research/designs/{Epic ID}/
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
- **Agent B — upstream-contracts**：注入 `{epic_context}`，**从 catalog**（`docs/project/api/`、`docs/project/data/`、`docs/project/ui/`）提取上游契约生成 Consumes（不再挖上游 plan 的 Provides）
- **Agent C — codebase-scout**：注入 `{epic_context}`，侦察可复用代码与设计上下文
- **Agent D — vj-learnings-researcher**（条件）：仅当 `docs/solutions/` 存在且非空时派发；传 `<work-context>` = 本 Epic 的 Activity/Concepts/Domains；否则记”暂无相关沉淀”

#### 2.2 合并结果

等全部代理完成后，输出一段上下文小结（作为后续 Phase 的输入），覆盖：

- **架构与契约**：Agent A 产出的相关架构约定、现有 API / Data / UI 契约、硬约束清单
- **上游 Consumes**：Agent B 读 catalog 产出的 Consumes 列表，每项真相来源指向 `docs/project/api|data|ui/`；catalog 缺失时声明（可能上游未实现 / 未同步）
- **复用锚点**：Agent C 产出，分”直接复用 / 需改造 / 不应重建”。优先找现有业务模块 / domain service / application use case、repository / DTO / response envelope / shared util、项目已有第三方依赖、官方 SDK / API / 标准协议、成熟开源库；能复用时在 Appendix C `Patterns` / `Approach` 写清复用对象，禁止重写 auth、permission、crypto、payment、scoring、parser、timezone、serialization、route generation、API client、response envelope、migration helper、design-system component 等已有权威实现。
- **设计上下文**（前端 Epic）：项目设计合同来源（优先 `docs/project/DESIGN.md`，fallback `docs/project/design_guidelines.md`）、`docs/project/ui/` 既有 surface/route catalog、epic.md 的页面体验地图、Agent C 产出的设计稿文件列表，或”暂无”
- **UI Surface / Screen delta**（前端 Epic）：从既有 UI catalog + epic.md 页面体验地图 + Story AC + API/Data Delta 推导本 Epic 新增/更新的 Screen 列表、每屏主任务、覆盖 Unit、数据/操作合同、关键状态与 Screen done 信号；若无法推导，列为待审批决策，不自由发挥。
- **institutional learnings**：Agent D 产出，或”暂无相关沉淀”
- **隐含约束小结**：综合以上，列出计划阶段需遵守的非显式约束

### Phase 3：Triage + Review Gate

按 `docs/tasks/plans/TEMPLATE.md` 的 Triage 规则,scope = 本 Epic:

1. 回答 8 问 → 判 **Flow A / B / C**(强制升级条件:改 DB migration、改公共 API 契约、改权限/安全、引入外部系统/异步、复杂状态机/幂等/事务、需求不清、跨 BC → 至少 Flow B)。
2. 在 `Appendix A. Triage 审计` 填**风险审计 + 来源索引**：Flow 分级、强制升级触发、影响范围、关键约束来源、Scope Challenge。不要展开硬约束 / 隐含约束长清单；执行相关约束在 Appendix C / task docs / `_execution_context.md` 中按 Unit 投影。
3. 把 AC 没写也推不出、会改变范围或验收口径的事项集中到 `## 2. 决策与 AC 偏离`。有用户在场 → 用当前平台的阻塞提问能力询问（Claude `AskUserQuestion`；Codex/无该工具时列编号选项并等待用户回复），不要猜一个值。**无人值守 / 作为 subagent 运行（无法提问）→ 标为“假设待审批”，写最合理假设与 Confidence，不阻塞**。两种情况都绝不静默跳过。
4. 若技术方案与 Story AC 的 `验证:` 命令冲突，登记到 `### AC 偏离`。原则上回改上游 epic.md / story AC；确需保留偏离时等待 reviewer 显式批准。**不得用“等价口径”静默覆盖 AC**。
5. Scope Challenge 四问，挡 scope creep。

> 所有 Flow 都填：§0 审批门（目标 + 待拍板决策链接）、目标与范围、决策与 AC 偏离、Unit 概览、Triage 审计（风险审计 + 来源索引）、Unit 执行详情、执行步骤、Sources。
> §4 共享设计是**人工 review 主面，与 Flow 无关**：只要有持久化模型 / 流程 / 状态流转 / 外部调用 / 前端页面，就把 ERD / 时序图 / 术语 / 边界画清楚，并把 §2 决策内联到图里。
> Flow B/C 另加：跨 Epic 契约、上下文与复用、风险与回滚。API / Schema / UI Delta 按 Triage 命中填写。
> Story 依赖与并行与 Flow 无关：本 Epic 含 ≥2 个 Story 即填写 §6 DAG + Appendix D（多 Story 编排是本 skill 核心价值，Flow A 也不跳过）。

### Phase 4：结构化（填模板主体）

1. **§0 审批门**（所有 Flow，thin）：**不是 Reviewer Summary**。只写：目标一句话、“设计与方向看 §4”、需要用户拍板的决策（只列 `D-ID` 链 §2，且这些决策已内联标注到 §4 图注）、API / Schema / UI catalog 是否受影响（链 §5）。**砍掉范围 / 顺序 / 下游表和 Review Checklist**——范围在 §1、顺序在 §6 DAG、契约在 §3 / §5，不在 §0 重复。
2. **决策与 AC 偏离**（§2，所有 Flow）：这是决策真相源。待审批事项、AC 偏离、已确认关键决策（带 `Rejected:`）集中写在这里。
3. **跨 Epic 契约（§3，Flow B/C）——单一真相源 = catalog，不在 plan 写 Provides 表**：
   - `Consumes`：本 Epic 依赖的上游契约子集，**真相来源 = catalog**（`docs/project/api|data|ui/{module-or-file}.md`），由 Phase 2 Agent B 读 catalog 生成。
   - **不写 Provides 表**：本 Epic 对下游的稳定契约只写进 catalog（§5 Catalog Sync 列出目标文件，catalog 文档以「契约状态 / introduced by Epic N」标出处）；**跨切面义务 / 不变量**（如 R1.x：某类记录必须经某机制关联某字段，读代码 / 读单模块 catalog 不一定看得出）写进 `docs/project/data/overview.md` 跨模块段、`docs/project/api/conventions.md` 或 `docs/project/ui/surfaces.md`。避免 plan 与 catalog 双写漂移、下游不必翻旧 plan。
4. **共享设计**（§4，**人工 review 主面**——用户唯一逐图看的章节，与 Flow 无关）：术语表（5+ 新概念时）、跨 Story 数据模型 ERD（只画本 Epic 拥有 + Consumes 子集，字段内联 `约束→需求`）、核心流程时序图（participant=代码落点、关键步骤内联 R-ID、AI / 外部调用失败用 `✋ + alt / else`、覆盖跨 Story 接力与状态交接）、设计上下文（前端 Epic：**指针 + 现状冲突 / 契约**——“UI Unit 以 DESIGN.md + docs/project/ui 为准”一行、与现状的冲突、跨 UI Unit 要统一的设计契约、来自 epic.md 的页面体验约束；**不复制 DESIGN.md 约束原文**，执行时 vj-work 直接读）、**UI Surface Delta**（前端 Epic 必填：本 Epic 新增/更新的 Screen/Route、角色主任务、覆盖 Unit、屏内区域、关键状态、API-for-UI、Screen done；稳定版本同步到 `docs/project/ui/`）。**把 §2 的已定关键决策内联标注到对应图**（ERD 字段注 / 时序图步骤注，如 `status "无 exp → D1"`），让用户“扫图 = 看见并批准方向”。**这些内容保留在正文，不能下沉或删除**；说人话的预算优先花在这里的图注与术语；字段名 / prompt 可在实现时微调。
   - **高风险流程补充规则**：命中状态机、并发、计费、权限、判分、AI 评估、事务 / 幂等等风险时，§4 或对应 Unit 的 Appendix C `Approach` 必须写业务伪代码、Mermaid `stateDiagram` / `sequenceDiagram` 或不变量。目的先是给人 Review 业务真相，其次才是给 vj-work 执行上下文；不要把它写成语言级实现伪代码。
5. **API / Schema / UI Delta + Catalog Sync 计划**（§5）：
   - API contract 有变化：填写 API Delta；列出将同步的 `docs/project/api/conventions.md`（仅全局约定变化时）与每个受影响模块的 `docs/project/api/{module}.md`。
   - DB schema / persistence contract 有变化：填写 Schema Delta；列出将同步的 `docs/project/data/overview.md` 与每个受影响模块的 `docs/project/data/{module}.md`。
   - UI Surface / route contract 有变化：填写 UI Surface Delta；列出将同步的 `docs/project/ui/surfaces.md` 与 `docs/project/ui/routes.md`。
   - 没有对应 delta：不要为了凑目录创建空模块文档；在 §5 明确写“无需同步”。
   - Phase 4 只把 delta 与目标文档写清楚；**真正写回 catalog 必须在 Phase 5 的 vj-plan-review 修正之后**，避免项目级契约和最终 plan 漂移。
6. **Implementation Units**（§6 + Appendix C）：**每个 Story → 一个 Unit**。§6 只放人工 Review 所需的 Goal / 主要交付 / Depends / Verification；Appendix C 放 Files（repo 相对路径）/ Approach / Patterns / Test scenarios。**Test scenarios 直接链接 Story AC 里已写好的 `验证:` 命令，不重写**，仅补 AC 未覆盖的用例——按来源分两类处理：
   - **实现涌现型行为用例**（并发 / 回滚 / 缓存失效 / 幂等等：选了 HOW 才浮现，但**用户可观测**）→ 属契约缺口，**回流改 Story AC**（走 `## 2. 决策与 AC 偏离`），不留在 plan。
   - **纯实现级用例**（内部分支 / 私有函数覆盖等用户不可观测的）→ 留 Appendix C Test scenarios，不回流。
   - **复用优先**：Appendix C `Patterns` / `Approach` 只在有明确对象时写复用声明，格式是“复用 `<path or module>` 做 `<purpose>`；不重写 `<capability>`”。没有明确复用对象时不要为了凑内容发明 Reuse Scout。
   - **Fallback policy 按需声明**：当 Unit 触及权限 / tenant / ownership、支付 / 余额 / 订单 / 库存 / 配额 / 判分 / 权益发放、核心算法 / AI 评估 / 风控、DB migration / 回填 / 事务 / 幂等、公共 API contract、安全审计 / 合规日志时，判断 fallback 是否会在未知真实状态下继续做信任判断或写副作用。会则在 `Execution note` 写“禁止 fallback/mock/简化实现；失败时 fail closed / STOP / 返回明确错误”。纯展示增强、非关键通知重试、只读缓存回源、UI 局部错误态允许降级，但必须不伪装成功。
   - Unit 内若需要多个技术阶段、多个提交或先后顺序，把它们写进该 Unit 的 `Approach` / `Execution note` / 后续 task 文档 `Implementation Plan`；不要因此新增 T 文档。
7. **Story 依赖与并行**（§6 + Appendix D，本 skill 重点，**≥2 Story 即必填，与 Flow 无关**）：
   - **真相源对齐**：run-epic 只读 epic.md 的 `**依赖**:` 行，不读本 plan。Unit DAG **必须与 epic.md 一致**；推导出更优依赖结构时先回改 epic.md 再同步本 plan，否则 run-epic 按 epic.md 跑。
   - 从 epic.md 的 story 依赖 + 各 unit `Depends` 画**依赖 DAG**。
   - 拓扑分层成**并行波次**:同波次内无相互依赖 = 逻辑上可并行。
   - **共享文件冲突点**:逐一检查同波次 unit 是否改同一文件(常见序列化点:`unit_of_work.py` 两处、`models/__init__.py`、`main.py`、`dto.py`、`apiClient.ts`、`routeTree.gen.ts`)。逻辑独立但改同文件的 unit **标为序列化点**(串行或一次性合并改动)。
   - 若启用 task 级拆分，Appendix D 必须同时保留 **Unit DAG** 与 **Task DAG / 波次**。Task 波次不得违反 Unit 依赖：依赖下游 Unit 的 task 只能在上游 Unit 全部 task 完成后进入后续波次。
   - 前端 Epic 必须额外保留 **Execution lane / Frontend composition waves**：先列 UI surface/API contract wave，再列 backend/API capability wave，再列按 Screen/Route 聚合的 frontend composition wave，最后列 E2E polish。Frontend composition wave 的启动条件是该 Screen 依赖的 API / 状态 / 数据合同稳定，不是“所有后端全部完成”。
   - §6 给出人工 Review 所需的并行结论；Appendix D 保存波次、共享文件冲突、Screen composition 顺序与启动条件明细。
8. **风险、回滚与执行步骤**（Appendix E）：所有 Flow 保留执行步骤；Flow B/C 补 Failure Modes 表与回滚 / 撤销策略；命中时补并发 / 幂等 / 事务 / 缓存细节。

### Phase 5：写盘 + 自检 + 生成 task 文档 + Handoff

1. **写 draft plan**：先只写 `docs/tasks/plans/{date}-epic-{N}-{slug}-plan.md`，不写 API / Data catalog。此时 plan 仍可能被 `vj-plan-review` 修正，catalog 同步延后到 step 4。
2. **自检清单**:
   - [ ] §0 是 thin 审批门（目标 + 待拍板 `D-ID` 链 §2），无范围 / 顺序 / 下游表、无 Review Checklist、无重复论证
   - [ ] §4 是人工 review 主面：有设计内容就画清 ERD / 时序 / 术语 / 边界，且 §2 已定决策已内联标注到对应图（扫图 = 批准方向）
   - [ ] 已删除模板注释、示例行、空表和无关条件段
   - [ ] 每个 Story 都对应一个 Unit；Unit 文件路径均 repo 相对
   - [ ] 默认 `1 Unit = 1 task`；若拆了 task，已写明拆分理由、Unit→Task 映射、task DAG / 波次、共享文件冲突点，且 task 波次未越过 Unit 依赖
   - [ ] 未因“前端 / 后端分离”本身拆 task；拆分理由指向依赖、文件隔离、验证边界或并行收益
   - [ ] 每个被拆分 Unit 都有 Unit 级闭环验收；task done 没被当成 Story done
   - [ ] Test scenarios 链到了 Story 的 `验证:` 命令，未静默重写 AC；冲突已登记到 §2“AC 偏离”
   - [ ] (≥2 Story 时)§6 DAG / 并行结论与 Appendix D 波次 / 共享文件冲突点都填了，且依赖**与 epic.md 的 `**依赖**:` 行一致**
   - [ ] Appendix A 只保留风险分级、影响范围、关键来源索引与 Scope Challenge；未复制 catalog / DESIGN.md / 代码约束长清单
   - [ ] `Consumes` 每项真相来源指向 catalog（`docs/project/api|data|ui/`）；**§3 未列 Provides 表**——本 Epic 对下游的契约已写入 catalog（§5 列出目标文件），跨切面不变量已写进 overview / conventions / UI catalog
   - [ ] API delta 已列出目标 catalog 文件；无 API delta 时未创建空文档
   - [ ] Schema / persistence delta 已列出目标 catalog 文件；无 data delta 时未创建空文档
   - [ ] UI Surface / route delta 已列出目标 catalog 文件；无 UI delta 时未创建空文档
   - [ ] (5+ 新概念)§4 术语表已填；(前端 Epic)§4 设计上下文只留指针 + 现状冲突 / 契约（**未复制 DESIGN.md 约束原文**），页面体验约束已关联到 UI Unit
   - [ ] (前端 Epic)§4 已填写 UI Surface Delta：每个新增/更新 Screen 有 Route / Primary Job / Role / Covered Units / Regions / States / API-for-UI / Screen done；无 Screen 合同不得生成 UI task
   - [ ] (改 schema 或多 Story 交付)Appendix E 回滚 / 撤销策略已填
   - [ ] 待审批项已问用户 **或**（无人值守时）已转为“假设待审批” + Confidence，无未标注的隐性猜测
   - [ ] Triage Flow 与填写深度一致
   - [ ] origin(epic.md/PRD)各 Success Criteria 都被某 unit/test 覆盖或显式延后
   - [ ] Appendix C 的复用声明只在有明确对象时出现；已有 auth / permission / payment / scoring / parser / API client / response envelope / design-system component 等权威实现未被重写
   - [ ] 高风险状态 / 权限 / 事务 / 判分 / AI 评估流程已在 §4 或 Appendix C 写清业务伪代码、Mermaid state / sequence 图或不变量；低风险 Unit 未被强行加重
   - [ ] 禁止 fallback/mock/简化实现只在会伪造业务真相或绕过信任边界时声明；允许降级的展示增强、通知重试、只读缓存回源没有被误标为 forbidden
3. **自动 plan 审查(vj-plan-review)**:plan 写盘后**自动**按运行时适配器执行 `vj-plan-review`（Claude/Codex 可派只读审查子任务；无 subagent 能力时在主上下文同步执行）做多视角独立审查(一致性/可行性/范围/对抗/依赖并行/UI surface)→ 自主判断采纳 → 修正本 plan;用户可说"跳过审查"中断。**epic-plan 的独立审查走 vj-plan-review,不再走 codex-review**(codex-review 仍负责 PRD/架构/API/数据模型);两者互不重叠。
4. **定稿写盘 + Catalog Sync**:
   - 收取 `vj-plan-review` 结果并自主采纳后，先重写最终 plan。
   - 若 §5 命中 API delta，同步写入对应 `docs/project/api/conventions.md`（如需）与 `docs/project/api/{module}.md`；只有全局约定变化时才改 `conventions.md`。
   - 若 §5 命中 Schema / persistence delta，同步写入 `docs/project/data/overview.md` 与 `docs/project/data/{module}.md`。
   - 若 §5 命中 UI Surface / route delta，同步写入 `docs/project/ui/surfaces.md` 与 `docs/project/ui/routes.md`。
   - 同步后复核：最终 plan §5 的本 Epic delta 与 catalog 文档完全一致；不一致则以最终 plan §5 的 delta 修正 catalog，不允许留下“后续再同步”。后续 Epic 的跨 Epic 真相源是 catalog，不是旧 plan。
   - 确认 plan 路径和本次同步的 catalog 文件绝对路径（可点击）。
5. **生成 / 更新 task 文档**（plan + catalog 定稿后，供 vj-work 直接消费）:
   - 时机:**在 vj-plan-review 修正之后**，确保 task 文档投影自定稿 plan + 已同步 catalog。续作 / 重跑时**整目录覆盖重写**(每次写盘都重生成，不做增量 diff)——task 文档是执行投影，不是跨 Epic 稳定上下文的长期真相源。
   - 落点:`task_docs.work_dir`(`docs/tasks/work/epic-{N}-{slug}/`),内含 `_ledger.md`(总账/索引) + 每个 task 一份 `T{NNN}-{slug}.md`(7 段文档)。
   - 拆 task:**默认 `1 Implementation Unit = 1 task = 1 T{NNN}`**。若一个 Unit 内需要多个小步骤、多个技术阶段或多个提交，把它们写进该 task 的 `## 2. Implementation Plan` 清单，不另拆 T 文档。
   - 只有同时满足以下条件时，才允许 `1 Unit → 多 task`：
     - 存在清楚的内部依赖或可独立执行的子目标；
     - 子 task 文件集互斥，或共享文件冲突点能明确串行；
     - 每个子 task 有局部验证，且 Unit 仍保留 Story AC 闭环验收；
     - 拆分能明显降低执行上下文或带来安全并行收益；
     - 拆分不是只因为“有前端和后端”。
   - 启用 task 级拆分时，必须同步生成 **task 级 DAG / 波次 / 共享文件冲突表** 写入 `_ledger.md`，标明每个 task 回指哪个 Unit，并明确 “task done != Unit done”。Task 波次不得越过 Unit 依赖。
   - 不满足上述条件时禁止拆分，避免 Unit 级 Appendix D 与 task 执行波次错位。
   - 生成内容:按 `task_docs.template`(`references/task-doc.template.md`)**投影自 Appendix C**(Goal/Files/Approach/Patterns/Test scenarios/Verification),不重新发明 HOW;「变更叙事」段保留 `_(待执行)_` 占位,由 vj-work 按 fast/strict 记录策略回写（fast 可 Phase 4 统一回写, strict 每 Unit 回写）。若 Appendix C 声明复用对象、高风险业务流程图 / 伪代码或禁止 fallback/mock/简化实现，必须原样投影进 task 文档的 Technical Approach / Execution note，不新增字段。
   - **UI Unit 检测 + Design / Screen context 注入**:某 Unit 的 `Files:` 含 `.tsx`、或路径含 `routes/`/`features/`/`components/` → 判为 UI Unit,把模板末尾「附:UI Unit Design / Screen context 注入块」原样复制进该 task 文档的 `## 3. Technical Approach` 段末，并填入本 Epic 对应的 `DESIGN.md` / fallback 来源、`docs/project/ui/` catalog 指针、页面体验地图条目、UI Surface Delta 中的 Screen ID / Route / 覆盖 sibling Units / 屏内区域 / API-for-UI / Screen done / 需覆盖的 UI 状态。非 UI Unit 不注入。
   - **Frontend composition task 投影**:若同一 Screen 覆盖多个 UI Unit，task 文档必须标明这是“Screen composition”还是“backend/API capability”。Screen composition task 可以覆盖多个 Unit 的 UI AC，但 Unit done 仍需回指各自 Story AC / Verification；不得为每个 Story 生成互相割裂的页面片段。
   - 生成 `_ledger.md`:默认波次计划直接来自 §6/Appendix D，且 T-ID 与 Unit 一一对应；若启用 task 级拆分，则 `_ledger.md` 必须改用 task 级波次，并保留 Unit→Task 映射表。
   - **不提交、不开 worktree**:本 skill 只写盘,与 plan 一样留未提交态。分支决策、`_execution_context.md`、docs-context 提交与 worktree 创建由 vj-work 按 execution mode 负责（fast 不审批,但若执行 worktree 需要读取 task/context 文件则自动提交可见上下文; strict 动代码前提交）。
   - 生成后自检:每个 Unit 都有对应 task 文档;UI Unit 已注入 Design / Screen context 块;`_ledger.md` 波次与 §6/Appendix D 一致;「变更叙事」段为 `_(待执行)_` 占位。
   - 告知 work_dir 绝对路径(可点击)。
6. **Handoff**:告知 plan 路径 + task 文档 work_dir 路径,并提供下一步选项:
   - `vj-work` 执行本计划:task 文档已在 step 5 生成,vj-work **直接装载执行**(不重新生成),并生成 `_execution_context.md`;分支、worktree 与记录/提交粒度由 vj-work 的 auto/fast/strict 模式决定。
   - `run-epic` 批量编排：**依赖图来自 epic.md 的 `**依赖**:` 行，不读本 plan**——执行前确认 §6 / Appendix D 与 epic.md 一致。
   - 告知本次同步更新的 `docs/project/api/` / `docs/project/data/` / `docs/project/ui/` 文件；后续实现若偏离，下游再报告差异并回写对应模块文档。
   - 进一步打磨本 plan(**改完会触发 step 5 重新生成 task 文档**,保持二者同步)。
   > 定位:epic-plan 是**人类阅读 + 喂给下游的 context 协调产物**;它额外产出 task 文档作为 vj-work 的执行投影。机械执行(run-epic)的依赖真相源仍是 epic.md。

## Stop Conditions（防死循环）

- 同一用户确认 gate(Phase 3 需确认 / Phase 5 自检)反馈 ≥3 次 → 弹「继续 / 重审上游 epic / 放弃」。
- 实现前发现 Triage 判错(漏了改 DB/契约)→ 暂停,升级 Flow,重填受影响小节。

## 与学习飞轮的关系

- **读**:Phase 2 调 `vj-learnings-researcher` 检索 `docs/solutions/`。
- **写**:本 skill 不写学习;一个 Story/Epic 实现收尾、踩了坑或定了非平凡决策后,用 `vj-compound` 沉淀,供未来的 vj-epic-plan 复用。
