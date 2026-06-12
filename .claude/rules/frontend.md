---
paths:
  - "frontend/**/*.tsx"
  - "frontend/**/*.ts"
---

# 前端铁律（碰前端代码必守）

> 这些是**非协商**的硬规则，按路径自动注入，不依赖 skill 是否加载。
> 详细 how-to（剧本 A/B、参考技法）见 `.agents/skills/frontend-dev-guidelines/SKILL.md`；
> 密屏工艺细则见 `frontend-dev-guidelines/resources/dense-ui-craft.md`。
> **数值唯一来源 = `docs/project/DESIGN.md`**（间距层级、token、字阶）；本文件只定义"闸怎么过"，不复制具体数字——数值冲突时以 DESIGN.md 为准。

## 富度（避免"像 demo"）

- **R0 先分屏型，再定富度地板**：动手前先归类——**front-of-house**（login / landing / 空首屏 / 营销页）还是 **operational**（dashboard / table-list / 审核台 / detail / form / 设置）。两类的富度地板、间距节奏、taste 工具都不同（见出口闸 A/B 轨）。**admin / 后台几乎都是 operational**。
- **R1 按「页面体验地图」建整屏**：照 epic 里该屏的 `职责/主操作/次操作/关键状态/信息优先级/体验护栏` 把**整屏建出来**。FE AC 只是可机检子集，不是实现上限——**不许只做到刚好过 AC 的最薄版本**。
- **R2 评审不许空屏**：屏上必须有逼真且有代表性的数据再算完成。后端先行 → 接真接口（dev 库有 seed）；后端没好 → `features/<x>/mock*.ts` 占位，**接口落地即删**。
- **R3 富度走参考**：按**屏类型**参考贴切的外部高级作品的「组成 / 密度 / 交互范式」，用 DESIGN.md token **重新皮肤化**——抄骨架与密度，不抄品牌皮。operational 屏找**密集后台**参考（Linear / Airtable / Retool / Carbon），别拿落地页参考表格。无外部参考 → DESIGN.md §Richness Floor + §Reference Skeletons 对应屏型。
- **R4 不许孤零零的卡片堆**：有数据就上表格/统计/筛选；补齐三态（加载/空/错误）与次操作。

## 工艺（避免"像 Excel"）——与富度同等牙齿

> 富度规则防"空"，本节防"挤"。塞满组件但没有间距层级、没有字阶层次 = 照样不过闸。

- **C1 间距分层**：按 DESIGN.md §Spacing Hierarchy 执行——密度只压**数据核心**（组件内节奏、表行），**页面框架必须呼吸**（页级 padding、区块间 gap 各有硬下限，见该表）。把组件内间距用到页框/区块层（wall-to-wall 挤死）与 marketing 大死白**同罪**。
- **C2 间距纪律**：全屏 gap/padding 值 ≤ 4 种，全部来自 4px 刻度，无随手值。
- **C3 层次靠字重与色阶，不靠堆字号**：每屏字号 ≤ 4 档（按 DESIGN.md 字阶表取）；数值/ID/时间 mono、数字右对齐。
- **C4 边框克制**：禁止卡内嵌卡的双重边框；分区优先 `--surface` 色块或单条 1px 边框（borders-not-shadows ≠ 处处加框）。
- **C5 accent 克制**：每屏实心 accent 按钮 ≤ 1（首要操作）；其余操作用 secondary/ghost。颜色只表状态，不做装饰。

## 出口闸：品味（done 前置条件，和功能 AC 同等牙齿）

> 历史教训：登录屏塌成 AC 最小居中卡；资料管理屏巨型空 dropzone 占半屏死白还自评 "passes"。根因 = 闸门全靠主观自检、没有客观牙齿。所以 B 轨全是可量化硬线，主观自检只许在 A 轨用。

**先判屏型（R0），走对应轨；缺一不过，并在变更叙事留证据。**

### A 轨 · front-of-house（login / landing / 空首屏 / 营销页）

- **A1 品味 skill 已真跑**：实现前已调 `design-taste-frontend`（或 `high-end-visual-design`），变更叙事**写明应用了哪几条**启发式，不是空喊"调了"。
- **A2 建到富度地板**：按 DESIGN.md §Richness Floor（front-of-house 行）+ §Reference Skeletons 建整屏（产品身份/版面结构/层次/三态），显式不做 AC 最小薄屏。
- **A3 截图对照 + 主观三问**：桌面+移动截图，与一个同类参考**并排对照**版面结构与层次；再自问「像被设计过的产品还是 demo？」「资深设计师直接发版还是打回？」「有无刻意的组成与视觉锚？」任一"否"→迭代。

### B 轨 · operational（dashboard / table-list / 审核台 / detail / form / 设置）— 客观硬线

> `design-taste-frontend` / `high-end-visual-design` 对 operational 屏 **OUT OF SCOPE**（前者 §13 明确排除 dashboards / admin）。B 轨真相源 = DESIGN.md §Richness Floor + §Reference Skeletons + §Spacing Hierarchy + `dense-ui-craft.md` + 一个密集后台参考。

标 done 前**逐条勾对照、缺一不过**，变更叙事**列出每条对应的实际组件名 / `data-testid` / 实测值**（只写"做了"不算）：

- **B1 组成按 primary job 配齐**：以 DESIGN.md §Richness Floor / §Reference Skeletons 该屏型的默认组成为基线（如 table-list = slim 工具条 + 统计带 + 密表[行 36–40px、列 meta 优先级、行操作] + 三态）。基线组件**默认必有**；省略任何一个必须在变更叙事写一行理由、绑定该屏 primary job（"统计带对此屏无可统计指标"算，"时间不够"不算）。禁止静默缺，也禁止为凑数硬塞无意义组件。
- **B2 死白上限**：单个空容器（dropzone / 空卡 / 空 banner）首屏占比 **≤ ~1/3**。超了 → 压扁或与数据并排。
- **B3 工艺线全过**：C1–C5 逐条核对；其中 C1 要求在截图上**量出**页级 padding 与最小区块 gap 的实测像素值并写进叙事，对照 DESIGN.md §Spacing Hierarchy 的硬范围。
- **B4 数据即界面**：主视觉锚是密表/统计/筛选，不是巨型录入框 + 一张小表；主操作压进工具条按钮。
- **B5 截图 + 参考对照 + 判定权独立**：桌面 + 移动各一张；与选定密集后台参考**并排对照**，逐项比组成、密度、页框呼吸感；在截图里**量出**首屏最大空容器（dropzone/空卡）高度占比、页框 padding、最小区块 gap 的实测像素并写进叙事（**量截图，不是读 Tailwind class 值**——读 class 会把"过"合理化）。**判定不得由编写该屏的同一 agent 自评**：必须人/orchestrator 亲自看截图，或一个只拿到「截图 + 本屏 B 轨 checklist + 同类密集后台参考、**不拿实现代码与小结**」的独立 auditor 出具。**无独立截图判定 = 未过闸；不接受无对照、无实测的自评 "passes"**。
- **B6 参考图对照（有则必用，A 轨同理）**：该屏存在已批准参考图（`docs/reference/research/designs/{epic-id}/{screen-id}.png` 或屏型金标准 `designs/golden/{archetype}.png`）时，独立审计输入升级为「实现截图 ↔ 参考图**并排对照** + B1–B5 硬线实测」，偏差清单按"参考图里有而实现里没有/走样"逐项列——审计从主观判美丑降级为客观找图差。A 轨的 A3 对照参考同样优先用已批准参考图。无参考图的屏维持 B1–B5 现状。

铁律：**没有设计参考图 ≠ 没有品味标准。operational 屏的标准 = 客观富度地板（B1–B5）+ 工艺硬线（C1–C5），不是"我觉得还行"；主观自检只在 A 轨用，且 A 轨也必须先对照参考再自问。任何轨的最终判定都要有人真看截图——实现者自评不算数。**

> 翻车实证（2026-06-10 epic-2 资料管理屏）：巨型 dropzone 占半屏 + vanity 统计卡（"本页上传 N / 本次粘贴 N" 会话级计数），实现 subagent 自评 B2/B4 "passes"（报 `h-[132px]`，实则渲染近半屏），orchestrator 仅凭文字小结就 commit → 上线即丑。**规则本就精确**（B2 死白 ≤1/3、B4 数据即界面），洞在**自评 + 没人看像素**。故 B5 判定权必须独立且量截图；另：list/table 屏的录入控件（dropzone/大输入框）不得当视觉主角，收成工具条动作或扁条，数据表才是首屏主角。

## 样式与栈（与 frontend-dev-guidelines 一致）

- **S1** 样式 token 唯一来源 = `docs/project/DESIGN.md` → 编译进 `src/index.css`。**不写裸 hex，不用 MUI/emotion/`sx`**；用 Tailwind class + shadcn 组件 + `cn()`。
- **S2** 数据用 `useSuspenseQuery` + `<SuspenseLoader>`，不写 early-return loading。
