<!-- task 文档模板（人话书挡 + 执行规格）。
     内容投影自 epic-plan 的 Appendix C，不重新发明 HOW；保留 test-first。
     读者导航：执行前看「摘要」，执行期以 _execution_context.md 的 Unit Context Packet 控制最小上下文，
     执行后看「变更叙事」。中间 1-7 段给 AI 执行/深度纠错。
     主生成方：vj-epic-plan Phase 5（写 plan 时一并生成）。vj-work 仅在 task 文档缺失时回退生成。
     ⚠️ 本文件与另一份 task-doc.template.md 是同步副本，改一处须改两处。 -->

# T{NNN} {Task 标题}

**Epic:** [Epic {N} {名称}](../../epics/{epic-file}) · **Unit / Scope:** {U-ID Story 名 或 Screen composition: screen-id 覆盖 U1,U2} · **Depends:** {前置 T-ID 或 无} · **Wave:** {波次} · **Status:** ☐ pending | ◐ in-progress | ☑ done | ⊘ skipped

**Task scope:** 本文档是执行投影，不是新需求层。默认一个 task 覆盖整个 Unit；若 Unit 被拆为多个 task，本 task 只代表局部 done，Unit done 仍以所有 sibling tasks 完成 + Story AC / Unit Verification 通过为准。若本 task 是 frontend screen composition，必须列 Covered Units、Screen done、每个 Unit 的 UI AC 回指；Screen done 不自动等于所有 Unit done。

## 摘要（人话 · 执行前看，30 秒懂意图）
- **为什么做**：{动机，1 句}
- **做什么**：{核心动作，2-3 句人话，不写库名/伪代码}
- **完成的标志**：{做完后可观察的状态}
- **一句话**：{一句话概括，便于转述}

---
〔以下 1-7 段为执行规格 —— 给 AI 执行 + 深度纠错用，平时可折叠忽略〕

## 1. Context
### 现状
- 当前存在什么 / 限制是什么（投影自 plan Appendix B + 前置 task 已交付物）
### 目标态
- 本 task 完成后应存在什么
### 继承假设
- A1 (FEASIBILITY): {引自 plan §2 决策，如 D1 服务端会话+HttpOnly Cookie}

## 2. Implementation Plan
### Phase 1: {描述}
- [ ] 步骤
### Phase 2: {描述}
- [ ] 步骤

## 3. Technical Approach
> 投影自 plan Appendix C 的 Approach / Patterns；约 200-300 字，给方向不写全量实现。
### 方案
- 框架/库 + 版本 + 标准（RFC/OWASP，若适用）
### 关键 API / 集成点
- `签名` - 用途；Where / How / When 集成
### 集成模式（伪代码，5-10 行）
```pseudocode
{方向性伪代码}
```
### 错误处理
| Error | HTTP | When | message_key |
### 日志
| Event | Level | Fields |
### 备选（Rejected，引自 plan §2）
- {方案} — 拒因

## 4. Acceptance Criteria
> 投影自 Story AC（信封 rewrite 后）。若本 task 只覆盖 Unit 的一部分，明确标注“本 task 覆盖 / sibling task 覆盖 / Unit 收口验证覆盖”，不得把局部 AC 当完整 Story done。
- [ ] Given … When … Then …

## 5. Affected Components
### 实现（投影自 plan Appendix C Files: Create/Modify）
- `path` - 改动 + 副作用（DB写/事件/HTTP）+ 深度
### 文档（必更）
- `docs/project/...` - 契约同步

## 6. Existing Code Impact
### 需重构
- `path` - 为什么
### 现有测试受影响
- `path` - 为什么（仅列受影响的现有测试）
### 测试新增（test-first，本 task 要写）
> 标了 test-first 的 Unit，先写失败测试再实现。投影自 plan 的 Test scenarios。
- {happy / edge / error / integration 场景}

## 7. Definition of Done
- [ ] 本 task 覆盖的 AC / 局部验证满足
- [ ] 按 `_execution_context.md` 的 Test policy 执行：test-first / test-with-implementation / verification-only
- [ ] 本 task Verification 命令全绿；失败修复尝试和结果已记录
- [ ] 若 Unit 被拆分，已标明 sibling task 和 Unit 收口验证；未把 task done 当作 Story done
- [ ] 若本 task 覆盖整个 Unit，Story AC / Unit Verification 已通过
- [ ] 无遗留兼容垫片
- [ ] 命中 API / data / design 契约变化时，相关文档已更新
- [ ] 若本 task 是 UI / Screen composition，已按 `docs/project/ui/` catalog 或 plan §4 UI Surface Delta 完成整屏主任务、屏内区域、关键状态、关联 sibling Units 与 Screen done；未把当前 Story 做成孤立 UI 片段
- [ ] fast mode：收尾统一回写变更叙事 / ledger；strict mode：本 Unit 完成即回写
- [ ] 命中 review trigger 时，vj-work Phase 4 review blocking findings 已修复

---

## 变更叙事（执行后回写 —— 你不用读代码就能转述 AI 做了啥）
> fast mode 可在 Phase 4 统一回写；strict mode 每 Unit 完成即回写。
- **实际做了什么**：{人话 3-5 句：实际建/改了什么、怎么工作的} _(待执行)_
- **怎么满足验收（对应 AC）**：{逐条对应 AC / Verification} _(待执行)_
- **关键权衡 / 偏离规格**：{为什么这么选；实现若偏离上面规格或 Unit Packet，写明原因} _(待执行)_
- **验证结果**：{Verification 命令 + 关键输出摘要} _(待执行)_
- **想深入看代码**：{commit SHA + 关键文件} _(待执行)_

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
Design / Screen context（UI Unit 必读 —— DESIGN.md 是视觉合同，docs/project/ui catalog 是整屏体验合同；catalog 未同步时临时看 plan §4 UI delta）:

【0】开工前先读现有前端 theme / layout / component patterns（优先复用 theme，不另起一套风格）。

【1】设计合同来源（按序）：优先 `docs/project/DESIGN.md`；缺失时 fallback
    `docs/project/design_guidelines.md` 并在变更叙事标注；两者都缺失 → 暂停 UI 实现，
    先给轻量 Design Read 或补 `DESIGN.md` 草案，不自由发挥。

【2】本 Unit 适用的 DESIGN.md 章节（生成时填锚点+行号；实现者必须逐节读原文）：
    {{例：§App Shell(L209-228)、§Login(L536-540)、§Tables And Lists(L348-358)、
       §Color Tokens(L103-148)、§Typography(L150-207)、§Do/Don't(L505-524) —— 按本 Unit 实际涉及面填}}

【3】从上述章节**逐字摘录**对本 Unit 起决定作用的硬约束句（带行号，禁改写）：
    {{例：- "Use a persistent left sidebar for admin workflows."（DESIGN.md L213）
       - "Primary action uses primary, not blue."（DESIGN.md L144）
       - "Never use gradient or blob backgrounds for app screens."（DESIGN.md L148）}}

【4】页面体验地图：读并遵循 epic.md `## 页面体验地图` 中本 Unit 对应页面/区域：
    页面职责、主操作、次操作、关键状态、信息优先级、体验护栏。

【5】UI Surface / Route：读并遵循 `docs/project/ui/surfaces.md`、`docs/project/ui/routes.md`；若尚未同步，临时读 plan §4 `UI Surface Delta` 与 `Frontend Composition Policy`。
    {{Screen ID: screen-...}}
    {{Route: /...}}
    {{Primary Job / Role: ...}}
    {{本 task lane: backend/API capability | frontend screen composition | e2e polish}}
    {{本 Unit 在该 Screen 中负责: 区域 / 状态 / 操作 / 数据}}
    {{同屏 sibling Units: U...；实现时不得破坏这些区域与主流程}}
    {{Regions / IA: 左/中/右或上下区域、主要列表/表单/分析面板等}}
    {{API-for-UI / Data Contract: endpoints、关键字段、状态枚举、错误语义、mock/real adapter 切换}}
    {{Catalog source: docs/project/ui/surfaces.md / docs/project/ui/routes.md；若尚未同步，写 plan §4 UI delta}}
    {{Screen done: 浏览器可验证的整屏完成信号}}

    执行规则：
    - 如果本 task 是 frontend screen composition：一次性实现该 Route 的完整工作流、布局区域、关键状态与关联 UI AC。
    - 如果本 task 只是 backend/API capability：不要顺手发明完整 UI；只维护必要的类型、mock 数据或最小联调探针。
    - 禁止为了当前 Story 单独新增与 Screen Contract 脱节的页面、卡片堆、按钮堆、表单堆。

【6】设计稿：如有 `docs/reference/research/designs/{epic-id}/` 设计稿或提示词，作结构/状态参考；
    不得在 vj-work 执行期临时从 vibeui/awesome-design-md 自动挑新风格。

【7】兜底：仅当 `_execution_context.md` 判定 UI-critical 或缺少足够项目 pattern 时，加载 design-taste-frontend 防默认风格规范；`DESIGN.md` 优先级更高。
    禁止 AI 默认风格：紫/蓝渐变背景、三等份 feature 卡片、Inter 字体、通用 glassmorphism。

──────────── 出口：DESIGN.md 一致性核对清单（按 UI class 触发）────────────
UI-critical：完成前逐条核对 + 桌面/移动截图佐证。
UI-functional：核对实际相关项 + targeted browser check 或局部截图。
UI-trivial：不强制截图；仍不得违反已列 DESIGN.md 硬约束。
凡【2】列到的章节，下列对应项必须勾选；不适用的标 N/A 并说明。仅"无溢出/五态"不算通过。
  □ 壳形态：符合 §App Shell —— admin 工作流=左 sidebar(248px)，员工答题=顶栏；**本页角色对应的壳形态对了吗**
  □ 主色：主操作=深青 primary(`#0F3D3E`)；蓝仅用于链接/焦点/信息；页面无蓝/紫主按钮（§Color L144）
  □ 背景：浅 canvas(`#F8FAFC`)/白 surface；**无渐变/blob/暗色整壳/glassmorphism**（§Color L148, §Do/Don't）
  □ 圆角：卡片/面板 ≤8px、输入 6px（§Radius L282-287）
  □ 字阶：页头 page-title(24/650)、分区 section-title(18)、正文 14/1.55；无 hero 大字、不随视口缩放（§Typography L203-207）
  □ 间距：用 §Spacing 刻度；无 landing 级 96px 大留白（§Spacing L269）
  □ 数据即界面：列表/队列优先表格，不是每条记录一张大卡（§Data-Dense, Don't L524）
  □ 语义色：success/warning/danger/ai 仅用于状态；AI 暂存内容视觉上"未确认"（§Do/Don't L513）
  □ 五态完整：空 / 加载 / 错误 / 成功 / 无权限
  □ Screen 合同：当前 Route 的 Primary Job、Regions、Key States、Screen done 与 `docs/project/ui/` catalog 或 plan §4 UI delta 一致；同屏 sibling Unit 的主流程未被破坏
  □ API-for-UI：前端只消费合同字段 / 状态 / 错误语义；缺字段时回补 API 合同或 mock adapter，不在 UI 内硬编码临时假数据
  □ 截图/浏览器检查：按 UI class 执行；无文字溢出、无元素重叠、主操作首屏可见，且与 DESIGN.md + 页面体验地图一致
-->
