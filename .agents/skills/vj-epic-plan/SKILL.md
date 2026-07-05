---
name: vj-epic-plan
description: 以一个 Epic（含若干 Story）为单元生成适合人工 Review 且可供下游执行的实现计划（HOW），并在命中 API、持久化或 UI Surface/Route 变化时同步维护 docs/project/api/、docs/project/data/ 与 docs/project/ui/ 模块化契约目录。在 vj-epic-story 之后、vj-work 之前使用。用户说"规划 epic X""给 epic 出实现计划""epic plan""epic 详规"时使用。
---

# vj-epic-plan — Epic 级实现计划

把一个已拆好的 Epic（`docs/tasks/epics/` 下的 epic.md + stories）转成可执行的实现计划。

**协作链**：`vj-product-requirements → vj-architecture → api-design → data-model → vj-epic-story (WHAT) → vj-epic-plan (本 skill) → vj-plan-review → vj-work (执行)`

## 三层输出与受众

| 层 | 产物 | 受众 | 生命周期 |
|----|------|------|----------|
| Human Review Pack | `plans/{date}-epic-{N}-{slug}/` 的 `README.md`（review 入口）、`design.md`（技术设计）、`decisions.md`（D/ACD 唯一真相源） | 人 | 本 Epic |
| Task Packets | `work_dir` 的 `task-index.md` + 每 task 一份 7 段文档 + `verify.sh` | AI（vj-work 直接装载） | 本 Epic，可整目录重写 |
| Project Catalog | `docs/project/api\|data\|ui/` | 人 + AI，长期合同 | 跨 Epic 永久 |

各产物的写作要求住在对应模板里（`references/`），不在本文件复述。执行记录（状态、变更叙事、verification 结果）住 vj-work 生成的 `_ledger.md`（append-only），**不**住 task 文档——因此 task 文档重跑时安全整目录覆盖。

## 铁律

- 只做计划：不写实现代码、不跑测试。模板里的图/伪代码是方向性指引，不是实现规范。
- WHAT 归 `vj-epic-story`：不重写 AC，只链接。技术方案与 Story AC 的 `验证:` 冲突时登记 `decisions.md` ACD 并在 README Known Conflicts 摘要，原则上回改上游；**不得用"等价口径"静默覆盖 AC**。
- 同一决策只在 `decisions.md` 写一次；其他文件只引 `D-ID`/`ACD-ID`。
- **1 Story = 1 Unit**（产品语义边界）；Task 是执行投影（可并行边界），不是新需求层。不得按"前端/后端/repository/service/route/test"技术层拆 Unit 或 task。
- **Barrier first, fan-out second**：schema / public DTO / shared enum / route shell / Screen Contract / ownership policy / shared registration 先作为 barrier/owner task 稳定，再按 backend capability / frontend screen fan-out。
- **不预规划 work-time 能现读的**：一条信息进 review pack 必须满足之一——①需用户拍板的岔路；②并行 Unit 共享的契约；③只有站在整个 epic 才看得见的事实；④帮 reviewer 建立心智模型。执行 agent 读代码/读 `DESIGN.md` 就能拿到且无歧义的事实不要 copy。
- 复用优先：Phase 2 codebase-scout 找锚点；`design.md` 只写影响边界/风险/判断的复用对象；禁止重写 auth、permission、crypto、payment、scoring、parser、serialization、API client、response envelope、migration helper、design-system component 等已有权威实现。
- 调研只读、限当前工作树，**禁止 git 跨分支/历史考古**（约束原文在 `references/research-agents.md`）。当前分支基线与 epic 引用产物矛盾 = STOP-and-ASK；无人值守时标"假设待审批 + Confidence"继续，绝不静默考古。
- UI 规划合同（屏型判定、双轨、Screen Contract 字段与完整度）按 `.agents/skills/_shared/ui-planning-contract.md` §1/§2/§3/§4/§6 执行，本 skill 不复述。Screen Contract 缺关键字段不得生成 frontend-composition task。`DESIGN.md`/golden 缺失或品牌方向不清时，不得靠 plan 文案补审美——列"先跑产品级 `ui-requirement-brief -> vj-design-md-matcher`"为待审批决策或阻塞项。
- **Backend by capability, frontend by experience**：执行波次显式拆 UI surface/API contract → backend capability → frontend screen composition → E2E polish；Screen 依赖的合同稳定即可进入该 Screen 实现，不等所有后端完成。
- 禁止 fallback/mock/简化实现的声明只在其会伪造业务真相或绕过信任边界时写（写进 task 的 Execution note）；允许降级的展示增强/通知重试/只读缓存回源不要写成禁止。
- 生成正式产物时删除模板注释、示例行与无关条件段；无内容的审批段明确写"无"，不留空壳（`plan_lint.py` 机检兜底）。
- 跨 Epic 稳定契约只写 catalog；命中 delta 在 plan 定稿时同步，不延后。后续 Epic 读 catalog，不翻旧 review pack。

## 输入

```
vj-epic-plan epic-1                                        # 按编号
vj-epic-plan docs/tasks/epics/epic-2-knowledge-ingestion   # 按路径
vj-epic-plan                                               # 未指定则列出 epics 让用户选
```

## 配置项

```yaml
epic_plan_generator:
  epics_dir: docs/tasks/epics/
  output_dir: docs/tasks/plans/
  output_format: "{date}-epic-{N}-{slug}/"     # review pack directory
  templates:
    readme: references/plan-pack-readme.template.md
    design: references/plan-pack-design.template.md
    decisions: references/plan-pack-decisions.template.md
  task_docs:
    work_dir: docs/tasks/work/epic-{N}-{slug}/  # task-index.md + T{NNN}-{slug}.md + verify.sh
    index_template: references/task-index.template.md
    template: references/task-doc.template.md   # 唯一副本；vj-work 回退生成也用这份
    verify_template: references/verify.template.sh
  lint: .agents/skills/_shared/scripts/plan_lint.py
  design_docs:
    architecture: docs/project/architecture.md
    design_system: docs/project/DESIGN.md
    ui_designs_dir: docs/reference/research/designs/
    api_dir: docs/project/api/            # conventions.md + {module}.md
    data_dir: docs/project/data/          # overview.md + {module}.md
    ui_dir: docs/project/ui/              # surfaces.md + routes.md
    legacy_api_fallback: docs/project/api_spec.md        # 只读兼容
    legacy_data_fallback: docs/project/database_schema.md # 只读兼容
  learnings_dir: docs/solutions/          # 存在且非空才检索
```

catalog 各文件的最小结构以现存文件为准；首次创建时：`api/conventions.md`=全局约定+模块索引，`api/{module}.md`=端点表+schema+错误/鉴权，`data/overview.md`=模块/表索引+跨模块关系，`data/{module}.md`=ERD+字段+索引+migration，`ui/surfaces.md`=Screen 合同（含屏型、富度地板、禁止项——vj-work 截图 gate 的输入），`ui/routes.md`=路由树+守卫+导航。

## 工作流（5 Phase）

### Phase 1：定位 Epic

1. 解析输入定位 epic（平铺 `epic-N-<slug>.md` 或 `epic-N-<slug>/epic.md` + `stories/`）；未指定则列出让用户选（无人值守 → 取最新 epic 并记录假设）。
2. 读 epic.md 全部内容 + 全部 story（含 AC `验证:` 三要素，定义见 `vj-epic-story/SKILL.md` Phase 4）。
3. 读三份 review pack 模板 + task 模板（见配置）。
4. **续作判断**：`plans/` 下已有本 epic 的 review pack → 问用户「就地更新 / 新建」（无人值守 → 默认就地更新，记入 decisions.md 假设待审批）；更新则只改仍相关小节，并重新生成 task docs 保持投影一致。

### Phase 2：并行收集上下文

1. 内联提炼 `epic_context`（格式见 `references/research-agents.md` 开头）。
2. 按 `references/research-agents.md` 派发只读研究代理：A design-context、B upstream-contracts（**从 catalog 生成 Consumes**，不挖旧 plan）、C codebase-scout、D learnings（条件）。无 subagent 能力时主上下文顺序执行并标注 "research inline fallback"。
3. 合并为上下文小结：架构与硬约束 / Consumes（真相源指向 catalog，缺失要声明）/ 复用锚点（直接复用·需改造·不应重建）/ 设计上下文与 UI Surface delta（前端 Epic；推不出的列待审批决策，不自由发挥）/ institutional learnings / 隐含约束。

### Phase 3：Execution Policy + 决策收口

1. 按 strict triggers 判 **Execution policy: fast | strict**（触发器清单以 AGENTS.md「Plan 规范」为准）。写进 README frontmatter + task-index Required Gates。不输出 Flow A/B/C。
2. AC 没写也推不出、会改变范围或验收口径的事项集中到 `decisions.md`。有用户在场用阻塞提问（Claude `AskUserQuestion`）；**无人值守 → 标"假设待审批"+ 最合理假设 + Confidence，不阻塞**。两种情况都绝不静默跳过。
3. Scope Challenge 四问挡 scope creep：真问题还是过度设计？成功判据？可复用什么？影响半径？

### Phase 4：生成 review pack 草稿

按三份模板填 `README.md` / `decisions.md` / `design.md`。模板槽位自带写作要求；**design.md 是三区制**——叙事区（自由结构大白话，5 个必答问题）→ 合同区（刚性块：术语表/API/Data/UI Delta/Must Hold/Risks/Checklist，命中才写）→ 深潜附录（按需）。必答问题清单与写作规则在 `references/plan-pack-design.template.md`，金样例在 `references/design-golden-sample.md`。**task 文档的 design anchors 只允许指向合同区块与 decisions.md 的 D/ACD**；叙事区标题自由，不承载锚点。此处只定一件事：

**Unit / Task 编排**（结果写入 task-index，README 只留 Execution Sketch 概览）：

- 每 Story 一个 Unit；识别 barrier/owner tasks；生成 Task DAG / 波次。
- **默认 1 Unit = 1 task**；拆多 task 必须同时满足：合同稳定、写集隔离或 owner 明确、独立 done signal、能缩短 critical path 或降低上下文。无并行收益或太小无独立验证就不拆。
- 共享文件冲突逐一检查（常见序列化点：`unit_of_work.py`、`models/__init__.py`、`main.py`、`dto.py`、`apiClient.ts`、`routeTree.gen.ts`）。
- 前端 Epic 保留 Execution lanes / Frontend composition waves。
- 实现涌现型、用户可观测的新行为用例回流 story AC 或 decisions ACD；纯实现级用例投影到 task docs。

### Phase 5：写盘 + 机检 + 审查 + task 文档 + Handoff

1. **写 draft review pack**（README / design / decisions）。catalog 同步延后到审查之后。
2. **判断题自检**（机器可查的交给 lint，这里只留判断）：
   - [ ] README 第一屏 5 分钟内能让人知道解决什么、不解决什么、先看哪、冲突在哪
   - [ ] design.md 叙事区 5 个必答问题都有实质回答（不是格子话）；每节导读行是实质主线；关键机制有具体场景走查；术语首现带白话同位语（读者画像=懂编程但未必啃过 DDD 黑话）
   - [ ] design.md 合同区命中的块齐全无空壳；术语表与叙事互链；高风险行为用决策表/failure table 进了合同区，不变量进了 Must Hold
   - [ ] 待审批项已问用户或已标"假设待审批 + Confidence"，无未标注的隐性猜测
   - [ ] 拆 task 的理由指向 barrier / capability / screen / 隔离 / 并行收益，而非技术分层
   - [ ] （前端 Epic）每个新增/更新 Screen 的 Contract 完整度已过 `_shared/ui-planning-contract.md` §6 gate
3. **自动审查**：draft 写盘后自动执行 `vj-plan-review`（多视角只读审查 → 自主采纳 → 修正 review pack）；用户可说"跳过审查"。
4. **定稿 + Catalog Sync**：采纳审查结果重写终稿；命中 delta 同步写 `docs/project/api|data|ui/` 对应文件并复核与终稿一致（不留"后续再同步"）；更新 README Catalog Sync 表为 synced/N-A；跑 `python3 .agents/skills/_shared/scripts/render_doc_html.py <review-pack-dir>` 生成人读 HTML（失败不阻塞）；strict epic 默认再用全局 `archify` skill 生成展示级交互图（架构图 + 最高风险流程/状态机图）到 `<review-pack-dir>/diagrams/`，design.md/README 链接引用（Mermaid 源为真相，archify 图为派生视图；archify 不可用不阻塞）。
5. **生成 task 文档 + verify.sh**（投影自定稿 design/decisions + 已同步 catalog；续作/重跑整目录覆盖重写）：
   - `task-index.md`：Required gates、Unit DAG（与 epic.md `**依赖**:` 行一致）、Task DAG/波次、barrier/owner 表、Unit→Task 映射、共享文件冲突表。
   - 每 task 一份 `T{NNN}-{slug}.md`：按 `references/task-doc.template.md` 投影（anchors / write scope / stop conditions 等必填字段见模板）。UI Unit（Files 含 `.tsx` 或路径含 `routes/`/`features/`/`components/`）注入模板附录的 Design/Screen context 块。
   - `verify.sh`：按 `references/verify.template.sh` 把每个 Unit 的 Story AC `验证:` 命令物化成可执行入口（`bash verify.sh U1` / `bash verify.sh all`）；按 kind 物化规则见模板头注释（pytest/API/DB 可执行，Browser 记 MANUAL；全 MANUAL 的 Unit exit 3 不算通过）。命令与 story 冲突时以 story 为准并回改 story 或登记 ACD。
6. **机检**：跑 `python3 .agents/skills/_shared/scripts/plan_lint.py <review-pack-dir>`。exit != 0 时修复后重跑；**lint 不过 = 本 skill 未完成**，不得 handoff。
7. **Handoff**：告知 review pack 与 work_dir 绝对路径（可点击）+ 本次同步的 catalog 文件；下一步选项：`vj-work` 执行（直接装载 task packets，不重新生成）或继续打磨 review pack（改完重跑 step 5-6 保持投影一致）。

## Stop Conditions

- 同一确认 gate 反馈 ≥3 次不收敛 → 弹「继续 / 重审上游 epic / 放弃」。
- 实现前发现 Execution Policy 判错（漏 strict trigger）→ 暂停切 strict，重填受影响小节与 task packets。

## 学习飞轮

读：Phase 2 Agent D 检索 `docs/solutions/`。写：本 skill 不写学习；收尾踩坑/非平凡决策用 `vj-compound` 沉淀。
