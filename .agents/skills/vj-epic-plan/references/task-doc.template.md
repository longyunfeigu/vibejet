<!-- task 文档模板（AI execution packet，机读投影）。
     内容投影自 review pack（design.md + decisions.md）+ catalog + Story AC，不重新发明 HOW；保留 test-first。
     本文件是唯一副本：vj-epic-plan Phase 5 主生成，vj-work 回退生成也读这份。
     人读浏览走 render_doc_html.py 生成的 HTML 视图（task-index 是索引入口，T 文档同样出视图，
     渲染器按文件名 T{NNN}-*.md 判族做人读分层——改动本模板的头部元数据行 / Execution note
     字段名时同步渲染器的 task 族解析）。执行记录（状态、变更叙事、verification 结果）由
     vj-work 写入 _ledger.md（append-only）——本文档不承载执行记录，重跑时整目录覆盖重写是安全的。 -->

# T{NNN} {Task 标题}

**Epic:** [Epic {N} {名称}](../../epics/{epic-file}) · **Unit / Scope:** {U-ID Story 名 或 Screen composition: screen-id 覆盖 U1,U2} · **Depends:** {前置 T-ID 或 无} · **Wave:** {波次}

**Generated from:** Review Pack `{review-pack-path}` · Unit `{U-ID}` · Story `{story-id}` · Design anchors `{design.md#...}` · Decision anchors `{decisions.md#D? / #ACD?}` · Catalog anchors `{docs/project/api|data|ui/...}`
**Task scope:** 本文档是执行投影，不是新需求层，也不是新的 truth source。若与 Story AC、catalog、`design.md` 或 `decisions.md` anchors 冲突，STOP 并报告。若 Unit 被拆为多个 task，本 task 只代表局部 done，Unit done 仍以所有 sibling tasks 完成 + Story AC / Unit Verification 通过为准。若本 task 是 frontend screen composition，必须列 Covered Units、Screen done、每个 Unit 的 UI AC 回指；Screen done 不自动等于所有 Unit done。

## 1. Context
### Source anchors（先看这些，不全文读 review pack）
- Review Pack: `{review-pack-path}` `design.md` anchors + `decisions.md` D/ACD anchors
- Task Index: `task-index.md` wave / sibling / shared-file coordination
- Catalog: `docs/project/api/...`, `docs/project/data/...`, `docs/project/ui/...`
- Story AC: `docs/tasks/epics/...`
### 现状
- 当前存在什么 / 限制是什么（投影自 `design.md` Current Baseline + 前置 task 已交付物）
### 目标态
- 本 task 完成后应存在什么
### 继承假设
- A1 (FEASIBILITY): {引自 `decisions.md` D-ID，如 D1 服务端会话+HttpOnly Cookie}
### Read first
<!-- 这是执行者的默认读集全部：本列表 + Write scope 目标文件。guideline / DESIGN.md 全文不进默认读集。
     pattern file 标 (pattern)，最多 3 个；命中风险面时列 guideline 的具体 resource 精准指针
     （如 `backend-dev-guidelines/resources/transaction-side-effects.md`），不列整份 SKILL.md。 -->
- `path` - 目标文件 / pattern file (pattern) / catalog anchor / 风险面 guideline resource
### Write scope
<!-- May modify 一行一路径（plan_lint R7 逐行查路径；一行塞多路径 = 首个之后全是盲区） -->
- May modify:
  - `path` - 说明（可省）
- Do not modify: `path` / sibling task owner files

## 2. Implementation Plan
> 按 barrier / capability / screen / integration 类型写。不要按 repository/service/route/test 这种技术层拆成无闭环步骤。
### Phase 1: {描述}
- [ ] 步骤
### Phase 2: {描述}
- [ ] 步骤

## 3. Technical Approach
> 投影自 `design.md` / `decisions.md` 对应 anchors；约 200-300 字，给方向不写全量实现。
### 方案
- 框架/库 + 版本 + 标准（RFC/OWASP，若适用）
### 关键 API / 集成点
- `签名` - 用途；Where / How / When 集成
### 集成模式（伪代码，5-10 行）
```pseudocode
{方向性伪代码}
```
### 错误处理
<!-- GFM 表格必须带分隔行（|---|），否则整块渲染成纯文本（plan_lint R12 机检兜底） -->
| Error | HTTP | When | message_key |
|-------|------|------|-------------|
### 日志
| Event | Level | Fields |
|-------|-------|--------|
### 备选（Rejected，引自 `decisions.md`）
- {方案} — 拒因
### Execution note
<!-- task doc 即执行包：以下机读字段必填（plan_lint R13 机检兜底），vj-work 不再二次蒸馏。 -->
- Test policy: {test-first | test-with-implementation | verification-only}（依据：风险类型 / Story AC）
- Risk class: {low | medium | strict-trigger:{触发器名}}（依据：AGENTS.md strict 触发条件 / task-index Required Gates）
- UI class: {none | trivial | functional | critical}（判定规则见 vj-work SKILL.md UI QA policy；非 UI task 填 none）
- System-wide check: {none | direct-neighbors | risk-triggered-two-hop}
- Verification: `{本 task 定向验证命令——只跑本 task 触碰面，不跑全量套件}`（Unit 收口 task 另跑 `bash verify.sh {U-ID}`）
- 复用声明: {必须复用的权威实现 / 官方 API / 标准协议，或"无"}
- Fallback 约束: {仅当 fallback/mock/简化实现会伪造业务真相或绕过信任边界时写"禁止"，并注明范围；否则"允许降级（不得伪装成功）"或"无"}
### Stop conditions
- 需要改出 write scope 之外的文件，且该文件不是本 task owner。
- 发现 task packet 与 Story AC / catalog / `design.md` / `decisions.md` anchors 冲突。
- 发现新的 strict trigger（DB/API/auth/transaction/UI shell 等）但 review pack / task-index 未标记。
- 需要 mock/fallback/简化实现绕过 `decisions.md` / `design.md` 明确禁止的真实业务路径。

## 4. Acceptance Criteria
> 投影自 Story AC（信封 rewrite 后）。若本 task 只覆盖 Unit 的一部分，明确标注"本 task 覆盖 / sibling task 覆盖 / Unit 收口验证覆盖"，不得把局部 AC 当完整 Story done。
- [ ] Given … When … Then …

## 5. Affected Components
### 实现（投影自 task write scope / design anchors / catalog delta）
- `path` - 改动 + 副作用（DB写/事件/HTTP）+ 深度
### 文档（必更）
- `docs/project/...` - 契约同步

## 6. Existing Code Impact
### 需重构
- `path` - 为什么
### 现有测试受影响
- `path` - 为什么（仅列受影响的现有测试）
### 测试新增（test-first，本 task 要写）
> 标了 test-first 的 Unit，先写失败测试再实现。投影自 Story AC、Unit Verification 与 review pack 风险场景。
- {happy / edge / error / integration 场景}

## 7. Definition of Done
- [ ] 本 task 覆盖的 AC / 局部验证满足
- [ ] 按本文档 Execution note 的 Test policy 执行：test-first / test-with-implementation / verification-only
- [ ] 本 task Verification 命令全绿（Unit 收口 task 同时跑 `verify.sh {U-ID}`）；失败修复尝试和结果已由 vj-work 记入 `_ledger.md`
- [ ] 若 Unit 被拆分，已标明 sibling task 和 Unit 收口验证；未把 task done 当作 Story done
- [ ] 若本 task 覆盖整个 Unit，Story AC / Unit Verification 已通过
- [ ] 未引入新决策；若发现 task packet 投影错误，已 STOP 并回到 review pack / catalog 修正
- [ ] 未修改 write scope 之外文件；若必须修改，已更新 owner / Task DAG 或 STOP
- [ ] 无遗留兼容垫片
- [ ] 命中 API / data / design 契约变化时，相关文档已更新
- [ ] 若本 task 是 UI / Screen composition，已按 `docs/project/ui/` catalog 或 `design.md` UI Surface Delta 完成整屏主任务、屏内区域、关键状态、关联 sibling Units 与 Screen done；未把当前 Story 做成孤立 UI 片段
- [ ] 命中 review trigger 时，vj-work Phase 4 review blocking findings 已修复

<!-- ========================================================================
附：UI Unit Design / Screen context 注入块
生成 task 文档时，若该 Unit 的 Files: 含 .tsx，或路径含 routes/ features/ components/
→ 判定为 UI Unit，把下面整块原样复制到「## 3. Technical Approach」段末尾，
  并**只填写 {{...}} 占位**（列锚点、贴原句、勾选适用核对项），其余原样保留。
非 UI Unit（纯后端 / 纯配置 / 纯测试）不注入。

⛔ 反有损改写铁律（RC1）：禁止把 DESIGN.md 的规则压成自己的 bullet 摘要。
  历史事故：epic-1 把 §App Shell 摘成「紧凑应用壳」却丢了「admin 用左 sidebar」，
  实现者照摘要做成顶栏 → 违反设计合同。所以本块**只允许「列锚点 + 逐字摘录关键句(带行号)」**，
  不允许转述/概括/挑着写。实现者执行前**必须打开 DESIGN.md 对应锚点读原文**，
  不得只依赖本 task 文档的句子。
======================================================================== -->
<!--
Design / Screen context（UI Unit 必读 —— DESIGN.md 是视觉合同，docs/project/ui catalog 是整屏体验合同；catalog 未同步时临时看 review pack `design.md` UI Surface Delta）:

【0】开工前先读现有前端 theme / layout / component patterns（优先复用 theme，不另起一套风格）。

【1】设计合同来源（按序）：优先 `docs/project/DESIGN.md`；缺失时 fallback
    `docs/project/design_guidelines.md` 并在 `_ledger.md` 记录标注；两者都缺失 → 暂停 UI 实现，
    先给轻量 Design Read 或补 `DESIGN.md` 草案，不自由发挥。

【2】本 Unit 适用的 DESIGN.md 章节（生成时填锚点+行号；实现者必须逐节读原文）：
    {{例：§App Shell(L209-228)、§Login(L536-540)、§Tables And Lists(L348-358)、
       §Color Tokens(L103-148)、§Typography(L150-207)、§Do/Don't(L505-524) —— 按本 Unit 实际涉及面填}}

【3】从上述章节**逐字摘录**对本 Unit 起决定作用的硬约束句（带行号，禁改写）：
    {{例：- "A front-of-house screen must communicate what the product is before asking the user to act."（DESIGN.md 实际行号）
       - "Do not ship a front-of-house screen as only a centered login form."（DESIGN.md 实际行号）
       - "Every data-backed screen must define loading / empty / error / success states."（DESIGN.md 实际行号）}}

【4】页面体验地图：读并遵循 epic.md `## 页面体验地图` 中本 Unit 对应页面/区域：
    页面职责、屏型、主操作、次操作、关键状态、信息优先级、体验护栏、品牌/富度要求、禁止项。

【5】UI Surface / Route：读并遵循 `docs/project/ui/surfaces.md`、`docs/project/ui/routes.md`；若尚未同步，临时读 review pack `design.md` 的 `UI Surface Delta`。
    {{Screen ID: screen-...}}
    {{Route: /...}}
    {{Screen type: front-of-house / operational / mixed}}
    {{Primary Job / Role: ...}}
    {{本 task lane: backend/API capability | frontend screen composition | e2e polish}}
    {{本 Unit 在该 Screen 中负责: 区域 / 状态 / 操作 / 数据}}
    {{同屏 sibling Units: U...；实现时不得破坏这些区域与主流程}}
    {{Regions / IA: 左/中/右或上下区域、主要列表/表单/分析面板等}}
    {{Information priority: P0 / P1 / P2}}
    {{Richness floor: ...}}
    {{Forbidden patterns: ...}}
    {{API-for-UI / Data Contract: endpoints、关键字段、状态枚举、错误语义、mock/real adapter 切换}}
    {{Catalog source: docs/project/ui/surfaces.md / docs/project/ui/routes.md；若尚未同步，写 design.md UI Surface Delta}}
    {{App shell / 全局导航契约: 该屏套在哪个共享外壳/导航里；source: DESIGN.md §Layout / 共享 layout 组件}}
    {{Reference image: 已批准参考图路径（UI-critical 必填；继承屏型金标准时填 golden 路径；均无则写"待参考图前置闸"）}}
    {{Screen done: 浏览器可验证的整屏完成信号}}

    执行规则：
    - 如果本 task 是 frontend screen composition：一次性实现该 Route 的完整工作流、布局区域、关键状态与关联 UI AC。
    - 如果本 task 只是 backend/API capability：不要顺手发明完整 UI；只维护必要的类型、mock 数据或最小联调探针。
    - 禁止为了当前 Story 单独新增与 Screen Contract 脱节的页面、卡片堆、按钮堆、表单堆。

【6】设计稿：如有 `docs/reference/research/designs/{epic-id}/` 设计稿或提示词，作结构/状态参考；
    不得在 vj-work 执行期临时从 vibeui/awesome-design-md 自动挑新风格。

【7】兜底：仅当本 task Execution note 判定 UI class = critical（front-of-house 屏）或缺少足够项目 pattern 时，加载 design-taste-frontend 防默认风格规范（operational/后台屏不调它，craft 真相源 = `frontend-dev-guidelines/resources/dense-ui-craft.md`）；`DESIGN.md` 优先级更高。
    禁止 AI 默认风格：紫/蓝渐变背景、三等份 feature 卡片、Inter 字体、通用 glassmorphism。

──────────── 出口：DESIGN.md 一致性核对清单（按 UI class 触发）────────────
UI-critical：完成前逐条核对 + 桌面/移动截图佐证。
UI-functional：核对实际相关项 + targeted browser check 或局部截图。
UI-trivial：不强制截图；仍不得违反已列 DESIGN.md 硬约束。
凡【2】列到的章节，下列对应项必须勾选；不适用的标 N/A 并说明。仅"无溢出/五态"不算通过。
  □ 壳形态：符合 Screen Contract / routes catalog 的 shell、导航、角色守卫；不得自造导航 frame
  □ 主色：主操作使用 DESIGN.md 定义的 primary / accent token；状态色只用于状态，不把蓝/紫等任意色当默认主按钮
  □ 背景：使用 DESIGN.md 定义的 canvas / surface / muted token；无默认渐变、blob、暗色整壳或 glassmorphism
  □ 圆角：卡片、面板、输入、按钮遵循 DESIGN.md 的 radius 规则；无混乱半径体系
  □ 字阶：遵循 DESIGN.md 字阶；一屏字号角色不超过 4 档；不随视口缩放
  □ 间距：遵循 DESIGN.md §Spacing Hierarchy；页框、区块、容器、组件四层间距清楚
  □ 数据即界面：operational 屏以表格/列表/统计/筛选等主数据容器为视觉锚点，不把每条记录做成大卡
  □ 语义色：success/warning/destructive/info 仅用于状态；未确认/草稿/AI 暂存内容必须视觉上可区分
  □ 五态完整：空 / 加载 / 错误 / 成功 / 无权限
  □ Screen 合同：当前 Route 的 Screen type、Primary Job、Regions、Information Priority、Richness Floor、Forbidden Patterns、Key States、Screen done 与 `docs/project/ui/` catalog 或 `design.md` UI Surface Delta 一致；同屏 sibling Unit 的主流程未被破坏
  □ API-for-UI：前端只消费合同字段 / 状态 / 错误语义；缺字段时回补 API 合同或 mock adapter，不在 UI 内硬编码临时假数据
  □ 截图/浏览器检查：按 UI class 执行；无文字溢出、无元素重叠、主操作首屏可见，且与 DESIGN.md + 页面体验地图一致
-->
