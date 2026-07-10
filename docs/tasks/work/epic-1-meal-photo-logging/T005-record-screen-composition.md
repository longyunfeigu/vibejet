# T005 /record 整屏 composition

**Epic:** [Epic 1 拍照记录一餐](../../epics/epic-1-meal-photo-logging/epic.md) · **Unit / Scope:** Screen composition: screen-meal-record 覆盖 U1,U2,U3,U4,U5（U3 全部 + 其余 Unit 的 FE AC） · **Depends:** T002,T003,T004（API 合同稳定） · **Wave:** 3

**Generated from:** Review Pack `docs/tasks/plans/2026-07-05-epic-1-meal-photo-logging/` · Unit `U1-U5` · Story `1.1-1.5` · Design anchors `design.md#ui-surface-delta` `design.md#api-delta` · Decision anchors `decisions.md#D4 #D8 #D9` · Catalog anchors `docs/project/ui/surfaces.md` `docs/project/ui/routes.md`
**Task scope:** 本文档是执行投影。本 task 是 frontend screen composition：一次性实现 `/record` 完整工作流、布局区域、全部关键状态与关联 UI AC。Covered Units: U1-U5；Screen done 不自动等于所有 Unit done——各 Unit 仍以 Story AC / Unit Verification 收口（T006）。

## 1. Context
### Source anchors
- Review Pack: design.md 合同区 UI Surface Delta / Screen Contract（本 task 的执行合同全文）+ API Delta 识别行为决策表（前端状态分支依据）
- Task Index: Wave 3；启动条件 = W2 三端点合同稳定 + 参考图前置闸
- Catalog: `docs/project/ui/surfaces.md` `routes.md`（plan 已同步）
- Story AC: 5 个 story 文件的 `#### 前端验收标准` + Story 1.3 全部行为 AC
### 现状
- 无任何 meal 前端；canonical 参考：`features/home`（useSuspenseQuery+SuspenseLoader 数据流）、`features/auth`（RHF+Zod+helpers+测试）、`components/layout/AppShell.tsx`、`routes/index.tsx`（beforeLoad 守卫）
### 目标态
- `features/meal-record/`（api/ hooks/ components/ helpers/ types/）+ `routes/record/index.tsx`；单屏状态机全状态可达；营养重算纯函数 + vitest
### 继承假设
- A1 (D4): 重算是前端比例纯函数；A2 (D9): 确认区生成 Idempotency-Key，重试沿用
### Read first
- `frontend/src/features/home/` - canonical 数据流 (pattern)
- `frontend/src/features/auth/` - RHF+Zod+helpers+测试结构 (pattern)
- `frontend/src/components/layout/AppShell.tsx` - 壳与导航契约
- `frontend/src/lib/apiClient.ts` - 信封/错误处理接法
- `docs/reference/research/designs/prd-suishou-shiji/ui-mock-board.html` - 结构/状态参考（D8）
- `.agents/skills/frontend-dev-guidelines/resources/dense-ui-craft.md` - operational 屏工艺真相源（UI class=critical 命中）
### Write scope
- May modify:
  - `frontend/src/features/meal-record/`（新建）
  - `frontend/src/routes/record/`（新建）
  - `frontend/src/routeTree.gen.ts`（pnpm dev 再生成）
- Do not modify: `backend/`、既有 feature/组件/AppShell、`src/index.css`（token 不动）

## 2. Implementation Plan
### Phase 1: 合同与骨架
- [ ] types + api wrapper（3 端点 + AI_UNAVAILABLE/unrecognized 错误分支）；重算 helpers + vitest（test-first：纯函数先测）
### Phase 2: screen composition（整屏一次成型）
- [ ] 区域①拍摄/上传区 → ②识别状态区 → ③明细确认区 → ④文本补录区（仅失败态）→ ⑤首次发送授权确认（一等态，非 toast；确认后本地持久化不再出现）；状态机全部 13 态接线（含上传失败态）<!-- vj-plan-review: applied [human-design/2][scope/2] -->
### Phase 3: 出口闸
- [ ] 桌面+移动截图 → B 轨闸（独立判定，非自评）

## 3. Technical Approach
### 方案
- React19 + TanStack Router/Query + RHF + Zod + shadcn（缺的组件 `npx shadcn add`）；状态机集中在 feature hook
### 关键 API / 集成点
- `POST /meal-photos|meal-recognitions|meal-records` - 合同见 `docs/project/api/meal-log.md`；错误分支用 `error.message_key`/`code`，禁止断言字符串
### 错误处理
| Error | HTTP | When | 前端行为 |
|------|------|------|------|
| AI_UNAVAILABLE | 503 | 识别/补录 | 服务不可用态：保留照片缩略 + 重试 + 补录双入口 |
| status=unrecognized | 200 | 识别 | 补录态：原因 + 文本入口 |
### 备选（Rejected，引自 `decisions.md`）
- 服务端重算接口 — D4
### Execution note
- Test policy: test-first（重算 helpers）+ test-with-implementation（组件）
- Risk class: medium（不动 shell/导航/design token；UI 面风险由 UI class 承载）
- UI class: critical（operational 首屏型第一张屏——参考图前置闸 + B 轨截图闸，见注入块【前置闸】）
- System-wide check: none（前端独占写集；`routeTree.gen.ts` 由 pnpm dev 再生成）
- Verification: `cd frontend && pnpm vitest run src/features/meal-record`（Screen done / B 轨闸由 UI QA gate 独立判定，不计入本命令）
- 复用声明: 必须复用 AppShell / SuspenseLoader / apiClient / shadcn 组件与既有 token；禁止新建风格体系
- Fallback 约束: 禁止用 mock 数据伪装识别成功路径；开发期联调探针不得进 done 判定
### Stop conditions
- 三端点任一合同与 `api/meal-log.md` 不符（回报 T002-T004）
- 参考图前置闸未过（见下方注入块【前置闸】）
- 需改 write scope 之外文件

## 4. Acceptance Criteria
> 投影：Story 1.3 行为 AC 全部 6 条 + 5 个 story 的 FE AC（1.1×4、1.2×3、1.3×1、1.4×2、1.5×1）；逐条见各 story 文件，本 task 不复制全文
- [ ] Screen done：浏览器完整走通 拍照(或选图)→识别→修正→保存，design.md Screen Contract 全部 13 态逐一可达（含首次发送授权确认，PRD §5.3 Must Hold 的验证落点）<!-- vj-plan-review: applied [scope/2] -->
- [ ] Story 1.3 全部行为 AC（Browser）通过；重算 vitest 绿

## 5. Affected Components
### 实现
- 见 Write scope；无后端副作用
### 文档（必更）
- 无（ui catalog 已同步；实现偏离 Screen Contract 时报告）

## 6. Existing Code Impact
### 需重构
- 无
### 现有测试受影响
- 无
### 测试新增（test-first）
- `features/meal-record/helpers/` 重算纯函数 vitest（比例重算/删项扣减/边界 0/负数）

## 7. Definition of Done
- [ ] `pnpm vitest run src/features/meal-record` 绿（= `verify.sh U3` 可执行部分）
- [ ] Screen done + 全部 FE AC 通过，桌面+移动截图留证
- [ ] B 轨截图闸 pass（判定权独立：orchestrator 看截图或独立 auditor，实现者自评不算）
- [ ] 未做孤立 UI 片段；同屏各区域与主流程完整
- [ ] strict 记录入 `_ledger.md`；未修改 write scope 之外文件

<!--
Design / Screen context（UI Unit 必读 —— DESIGN.md 是视觉合同，docs/project/ui catalog 是整屏体验合同）:

【0】开工前先读现有前端 theme / layout / component patterns（优先复用 theme，不另起一套风格）。

【1】设计合同来源（按序）：`docs/project/DESIGN.md`（存在，v0.2）；无需 fallback。

【2】本 Unit 适用的 DESIGN.md 章节（实现者必须逐节读原文）：
    §调色板·全局 UI 系(L31-53)、§字阶(L73-83)、§圆角(L85-88)、§间距层级(L91-100)、
    §组件规则(L102-113)、§Richness Floor(L115-119，注意：表内暂无 operational 行，
    本屏富度地板以 review pack design.md §7 Screen Contract 为准——见 README Known Conflicts)

【3】从上述章节**逐字摘录**对本 Unit 起决定作用的硬约束句（带行号，禁改写）：
    - "**状态表达 = 颜色 + 图标 + 文案**三件套,不只靠颜色(无障碍)。"（DESIGN.md:71）
    - "每屏字号 ≤ 4 档。"（DESIGN.md:75）
    - "数值唯一来源。全屏 gap/padding ≤ 4 种,全部 4px 刻度。**页框必须呼吸,密度只压数据核心。**"（DESIGN.md:93）
    - "每屏实心 accent ≤ 1。"（DESIGN.md:106）
    - "operational 屏维持描边输入 + `--ring` 焦点环。"（DESIGN.md:109）
    - "**图标**:lucide-react,`strokeWidth={1.5}`。"（DESIGN.md:110）
    - "**三态**:加载(按钮内 spinner + 禁用 / `SuspenseLoader` 骨架);空(图标+说明+引导);错误(原因 + 重试 / `sonner` toast,语义色)。"（DESIGN.md:112-113）
    - "`--primary` | `#5046E5` | 品牌强调(首要按钮、链接)"（DESIGN.md:42）

【4】页面体验地图：读并遵循 epic.md `## 页面体验地图` 两行（拍摄/上传区 + 识别结果确认区）：
    页面职责、屏型 operational、主/次操作、关键状态、信息优先级、体验护栏、禁止项。

【5】UI Surface / Route：读 `docs/project/ui/surfaces.md`、`docs/project/ui/routes.md`（plan 已同步）。
    Screen ID: screen-meal-record
    Route: /record
    Screen type: operational
    Primary Job / Role: 30 秒内完成"拍照→识别→修正→保存"一餐 / 记录者
    本 task lane: frontend screen composition
    本 Unit 在该 Screen 中负责: 整屏（U1-U5 全部 UI 面）
    同屏 sibling Units: U1-U5 全部由本 task 承载，无外部 sibling
    Regions / IA: ①拍摄/上传区 ②识别状态区 ③明细确认区(紧凑列表+总热量锚+餐次+保存) ④文本补录区(仅失败态)
    Information priority: 默认态 拍照入口>说明；结果态 总热量>明细>餐次>保存
    Richness floor: 13 态全可达（含首次发送授权确认、上传失败一等态）、各有三件套；失败态保留照片缩略+双恢复入口；不空屏
    Forbidden patterns: 裸居中表单；每道菜大卡堆；纯 toast 传达失败；默认态出现文本输入框
    API-for-UI / Data Contract: docs/project/api/meal-log.md 三端点；AI_UNAVAILABLE→服务不可用态；status=unrecognized→补录态
    Catalog source: docs/project/ui/surfaces.md / routes.md
    App shell / 全局导航契约: 套现有 AppShell（frontend/src/components/layout/AppShell.tsx）；本 Epic 不新增导航项
    Reference image: 待参考图前置闸——golden/ 不存在，候选参考 docs/reference/research/designs/prd-suishou-shiji/ui-mock-board.html（D8）；
      【前置闸】本屏 UI class=critical（operational 首屏型第一张屏）：开工前按 vj-work Frontend composition gate 用 Screen Contract + DESIGN.md token 渲染一次性 HTML 截图作参考图候选，落 docs/reference/research/designs/epic-1/screen-meal-record.png，STOP 给人批后再进 composition
    Screen done: 浏览器完整走通 拍照(或选图)→识别→修正→保存 且 13 个关键状态逐一可达（清单以 design.md Screen Contract 为准）

    执行规则：
    - 本 task 是 frontend screen composition：一次性实现该 Route 的完整工作流、布局区域、关键状态与关联 UI AC。
    - 禁止为了当前 Story 单独新增与 Screen Contract 脱节的页面、卡片堆、按钮堆、表单堆。

【6】设计稿：docs/reference/research/designs/prd-suishou-shiji/ui-mock-board.html 作结构/状态参考（D8）；
    不得执行期临时从 vibeui/awesome-design-md 自动挑新风格。

【7】兜底：admin/operational 屏不调 design-taste-frontend；craft 真相源 = frontend-dev-guidelines/resources/dense-ui-craft.md；
    禁止 AI 默认风格：紫/蓝渐变背景、三等份 feature 卡片、通用 glassmorphism。

──────────── 出口：DESIGN.md 一致性核对清单（UI-critical：完成前逐条核对 + 桌面/移动截图佐证）────────────
  ☑ 适用项按【2】所列章节逐条核对；本屏为 operational：走 frontend.md B 轨客观硬线（B1-B5 含 C1-C5）
  □ 壳形态：套 AppShell，不自造导航 frame
  □ 主色：主操作用 --primary #5046E5；状态色只用于状态
  □ 背景：--background/--card/--muted token；无渐变/blob/glassmorphism
  □ 圆角：输入/卡片 lg、大容器 xl+（DESIGN.md:88）
  □ 字阶：≤4 档；数字用 Geist Mono 右对齐（营养数值，DESIGN.md:83）
  □ 间距：≤4 种、4px 刻度、页框呼吸（DESIGN.md:93）
  □ 数据即界面：明细用紧凑列表，总热量为视觉锚，不做大卡堆
  □ 语义色：success/warning/destructive 仅用于状态；AI 暂存明细（未确认）与已保存记录视觉可区分
  □ 五态完整：空/加载/错误/成功/无权限（+本屏特有：识别中/无法识别/服务不可用/重算中/保存中）
  □ Screen 合同：与 docs/project/ui/surfaces.md 一致；主流程不破坏
  □ API-for-UI：只消费合同字段/状态/错误语义；缺字段回补合同，不硬编码假数据
  □ 截图/浏览器检查：桌面+移动；无溢出/无重叠/主操作首屏可见
-->
