# UI 规划合同（规划期单一真相源）

> 本文件是 `vj-feature` / `vj-epic-story` / `vj-epic-plan` 在**规划期**共用的 UI 合同规则真相源。
> 各 skill 只引用本文件 + 声明自己的产物字段，不逐字复述规则；规则演进只改这里。
> 分工：**实现期**出口闸（富度 R0–R4、工艺 C1–C5、A/B 轨截图审查）真相源 = `.claude/rules/frontend.md`；
> 样式 token 数值真相源 = `docs/project/DESIGN.md`。三者冲突时按"数值看 DESIGN.md、
> 实现闸看 frontend.md、规划合同看本文件"分治。

## 1. 屏型判定（每个 UI Screen 必判）

`front-of-house | operational | mixed`

| 屏型 | 默认命中 | 定位 |
|------|----------|------|
| front-of-house | login、signup、landing、onboarding、未登录/首个空首屏、营销页 | 承载产品身份与信任，默认 UI-critical |
| operational | dashboard、table-list、审核台、detail、form、settings、admin 后台 | 承载高频操作与数据密度 |

不确定时标 `⚠️ 推断`，在各 skill 的用户确认环节让用户定。

## 2. 双轨触发（先方向，后单屏）

- **产品/品牌方向轨（低频）**：`docs/project/DESIGN.md` 缺失/明显过期、品牌方向不清、
  front-of-house 屏无 golden reference、或用户要求整体视觉升级 → 先产品级
  `ui-requirement-brief` → `vj-design-md-matcher`（产出 `DESIGN.md` + golden screens）。
  不得在 plan / story 文案里临时发明风格。
- **单屏体验轨（高频）**：方向源已稳定、只是新增/重做具体 Screen → 检查页面体验地图完整度；
  缺单屏目标/结构 → `ui-page-goal-structure`；缺状态覆盖 → `ui-state-coverage`；
  命中复杂操作流判定（§3）→ `ui-user-journey-audit`。
- 两轨可以都需要（如新产品第一次做登录页：先定 DESIGN.md/golden，再做单屏结构与状态）。
- **强制的是完整度，不是跑满 skill**：字段能填满就不重复跑；任何字段缺失不得写
  "后续实现时再看"跳过。

## 3. 复杂操作流判定（命中任一 → 强制 `ui-user-journey-audit`）

不按页面名枚举，按流程特征判定：

1. 用户需连续完成 2 步以上
2. 中途有权限 / 资格 / 库存 / 余额 / 次数 / 审核 / 风控 / 依赖数据判断
3. 有提交 / 保存 / 发布 / 支付 / 删除 / 审批等不可轻易撤销动作
4. 需要 retry / rollback / cancel / back / resume 等恢复路径
5. 操作结果会改变业务状态，或影响其他用户 / 下游流程

登录、注册、提交、审核、支付、上传、发布、导入、开通、邀请、删除等只是常见示例，不是白名单。

## 4. 屏型规划要求与禁止项

**front-of-house**（默认 UI-critical）：
- 必须写清：产品身份/品牌区、≥2 个价值点或信任点、视觉锚点、主 CTA 默认可操作态、
  错误/loading/disabled 三态
- 禁止：裸居中表单卡、左侧/背景大面积纯空白、只有表单无品牌概念
- 不得把"可提交表单"当完成标准；AC 必须包含"页面体验地图对齐 / 设计合同对齐 / 截图审查"类
  Browser 验证，不允许只断言表单字段存在

**operational**：
- 必须写清：主数据容器、工具条/筛选、统计或摘要、行/批量操作、loading/empty/error 三态、
  信息密度要求
- 禁止：孤立卡片堆、巨型录入框当主视觉、无主内容锚点（无数据表或无主内容锚）
- AC 至少一条 Browser 验证覆盖"主数据容器 + 工具条/筛选/三态之一存在"，
  不能只验证一个卡片或表单存在

## 5. 页面体验地图字段（vj-feature / vj-epic-story 产出，完整度 BLOCKING）

每个 UI Screen 必须覆盖：**屏型、Route/入口、主任务、区域、信息优先级、关键状态、
富度地板、禁止项、设计来源**。缺任一字段 → 回对应 ui-* skill 或用户确认环节补齐，
不得写"实现时确定"。

状态覆盖使用 `ui-state-coverage` 的检查口径：默认、loading、empty、error、disabled、
permission、内容过长、重复提交等真实状态，必须映射到 Story AC、前端 AC 或 Assumptions。

## 6. Screen Contract 字段（vj-epic-plan 产出，缺字段不得生成 frontend-composition task）

**Screen ID、Route、screen type、Primary Job、Role、Regions、Key States、
Information Priority、Richness Floor、Forbidden Patterns、Covered Units、API-for-UI、
Screen done、Design source pointers**。缺任一关键字段回到 Story / plan 修正，
不能让执行期自由发挥。

## 7. 前端 AC 写法

- 前端 AC 只写可 Browser 断言的元素、状态和交互；控件细节不进 Story 主体
- 品牌 / 布局 / 富度要求写入 Epic `## 页面体验地图`，由 `vj-epic-plan` 投影为
  Screen Contract，由 `vj-work` 按 `.claude/rules/frontend.md` 出口闸截图验证
- 具体布局和样式不写成控件脚本
