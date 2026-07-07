# vj-mock-board 设计 spec

**日期**：2026-07-08
**状态**：设计已确认，待出实现计划
**发起**：用户需要一个 skill——输入 PRD，匹配 `docs/project/DESIGN.md`，批量生成 mock HTML，
在写代码前看到产品长什么样。

## 1. 背景与调研结论

外部生态没有能直接对上本仓库 DESIGN.md 体系的现成 skill：

- **PRD-to-Mockup**（mcpmarket）：概念最接近（Lean PRD → 单文件可导航 wireframe + 业务规则标注），
  但无公开源码，只能借鉴思路。
- **alchaincyf/huashu-design**（36K 安装）：设计执行引擎最强，明确支持接入已有 design system，
  但无 PRD 解析、无批量多页编排；自带 40 风格库与本仓库"token 唯一来源 DESIGN.md"纪律有张力。
- **Magdoub/claude-wireframe-skill**：并行 subagent 分区生成、共享 HTML 换 CSS 的机制可借鉴。

仓库内已有手工先例：`docs/reference/research/designs/prd-suishou-shiji/ui-mock-board.html`
（PRD v1.0 → 单文件 mock board，390px 手机框平铺、按 Epic 分区、每屏带
"这块 UI 逼出来的 API/设计决策"注记），且被 `docs/project/ui/surfaces.md` 引用为 Design source。
**本 skill 本质是把这次手工实践产品化。**

落地方式（用户已确认）：自建薄编排 vj 系 skill，只借外部机制不装外部本体。

## 2. 已确认的关键决策

| 决策点 | 结论 | 被拒方案与拒因 |
|---|---|---|
| 产物形态 | 单文件 Mock Board（沿用 ui-mock-board.html 形态） | 多文件可点击原型：状态变体难平铺对比、文件多维护重；板内锚点跳转：暂不需要 |
| DESIGN.md 缺失时 | 先路由 `vj-design-md-matcher`，产出 DESIGN.md 后再出板 | 降级中性线框为常规分支：气质不可见；临时自选风格：违反规划合同"不得临时发明风格" |
| 状态粒度 | 分层：P0 屏（核心旅程）按 `ui-state-coverage` 必补清单画全；其余屏只画默认态 | 全屏全态：板轻易 30+ 框，生成与阅读成本双高；仅默认态+PRD 点名异常态：空/加载等通用态易漏 |
| 生命周期 | PRD 快照：板头标注来源 PRD 版本+生成日期；PRD 变更整板幂等重跑 | 按 Epic 局部重生成：分区拼接一致性成本 > 重跑成本；一次性不维护：板与 PRD 半新半旧 |
| 生成架构 | 骨架 + golden 屏定语法 + 按 Epic 并行 subagent + 装配机检；≤6 屏降级顺序单 agent | 单 pass 直写：大 PRD 撑爆上下文、后段质量退化；脚本模板渲染：千屏一面，为单一场景引入渲染引擎属过度工程 |

## 3. 定位与边界

**skill 名**：`vj-mock-board`（repo-local，`.agents/skills/vj-mock-board/`）。

工作流位置：PRD 定稿后、`vj-epic-story` 之前；对已有 PRD 可随时跑。

```text
vj-product-requirements → vj-mock-board → vj-epic-story → vj-epic-plan → vj-work
                             ↑ 缺 DESIGN.md 时先路由 vj-design-md-matcher
```

**做**：PRD → Screen Inventory → 按 DESIGN.md 双轨 token 生成单文件 mock board。

**不做**：
- 不是可点击多页原型，不产 React/生产代码
- 不更新 `docs/project/ui/surfaces.md`（vj-epic-plan 的职责；它可反向引用板作结构参考）
- 不发明风格：token 唯一来源 `docs/project/DESIGN.md`，缺失即路由，不自选
- 不在 vj-work / story 实现期使用（那时以 surfaces.md Screen Contract 为准）

## 4. 产物合同

- **路径**：`docs/reference/research/designs/prd-{slug}/ui-mock-board.html`（沿用现有先例目录约定）
- **快照语义**：板头标注「来源 PRD 版本 + 生成日期 + 用法说明」；PRD 变更后整板重跑覆盖（幂等）
- **单文件自包含**：无 CDN、无外链字体（不假设网络可用）；共享 CSS 类在板内定义
- **设备框**：手机框 390px 或桌面浏览器框，按 PRD 使用场景判定；不确定标 `⚠️ 推断` 由用户在
  Inventory gate 定
- **分区**：按 Epic 分区平铺，每区标题 + 来源条目索引
- **每屏标配**：屏名 + 状态标签 + 注记框（"这块 UI 逼出来的 API/设计决策"，用于反查架构与
  接口设计遗漏）
- **状态粒度**：P0 屏按 `ui-state-coverage` 必补清单（默认/加载/空/失败/禁用/完成/异常按需裁剪）
  画全；其余屏只画默认态

## 5. Phase 骨架

- **P0 前置检查**：PRD 缺失 → 路由 `vj-product-requirements`（或用户给描述+标低置信）；
  `docs/project/DESIGN.md` 缺失或明显过期 → 路由 `vj-design-md-matcher`
- **P1 Screen Inventory**：解析 PRD（EARS 条目 / 用户旅程 / NFR）→ 清单表：
  屏名 / 来源条目 / 屏型（按 `.agents/skills/_shared/ui-planning-contract.md` §1 判定，
  本 skill 不复述规则）/ P0 判定 / 状态集 / 设备框 → **用户确认 gate**
  （无人值守 fallback：最合理假设 + `Confidence: H/M/L`，标"假设待审批"，不阻塞）
- **P2 骨架 + golden 屏**：从 DESIGN.md 抽双轨 token（front-of-house / operational）编译进板内
  `:root`；写板头、共享 CSS 类（phone frame / note 框 / 状态标签等）；精做 1 个 P0 屏做
  golden 样例定视觉语法（借 huashu-design "先定语法再批量"机制）
- **P3 并行分区生成**：每 Epic 一个 subagent，输入 = 共享 CSS 类清单 + golden 屏 HTML +
  本 Epic 清单行 + PRD 相关条目 + 注记要求；输出 = 该分区 HTML 片段。
  总屏数 ≤6 时降级为主 agent 顺序生成，不派 subagent
- **P4 装配 + 机检**：拼装后跑 `scripts/validate_mock_board.py`（exit code 拦截）：
  1. Inventory 中每个屏×状态在板内有对应 DOM 锚点（id 约定）
  2. 正文颜色只允许 `var(--token)` 引用；`:root` 变量值必须 ∈ DESIGN.md 色值集合
     （rgba 阴影白名单例外）
  3. 单文件自包含（无 `http(s)://` 资源引用）
  4. 每屏有注记框
  机检 fail → 对应分区回炉
- **P5 收尾**：`web-access` 打开截图自查（反 AI-slop / 富度）→ 后置审查钩子跑
  `ui-visual-consistency-audit`（用户可说"跳过审查"）→ 报告产物路径与打开方式

## 6. 失败模式与兜底

| 场景 | 一线处理 | 仍失败兜底 |
|---|---|---|
| DESIGN.md 缺失且 matcher 跑不了（无网络/用户拒绝） | 降级中性灰线框板，板头标"风格待 DESIGN.md 定稿后重染" | 交付线框板并标注 |
| 屏数 >20 | 提示裁剪（P1 屏减态 / 只画核心 Epic），用户确认 | 无人值守自动裁到核心旅程屏 + 板头标注裁剪范围 |
| subagent 片段机检 fail | 该分区回炉一次 | 主 agent 亲自修该分区 |
| `web-access` 不可用 | 跳过截图自查 | 板头标"未做浏览器视觉验证" |
| PRD 无 Epic 结构（自由格式需求） | 按用户旅程聚类自建分区，标 `⚠️ 推断` | Inventory gate 让用户定分区 |

**Stop condition**：Inventory 确认 gate ≥3 轮不收敛 → 弹"继续 / 重审 PRD / 放弃"。

## 7. 文件结构与注册

```text
.agents/skills/vj-mock-board/
├── SKILL.md                     # 瘦：适用/不适用、铁律、Phase 骨架、触发示例
├── references/
│   ├── screen-inventory.template.md   # 清单表格式 + 判定规则指针（不复述真相源）
│   ├── board-skeleton.md              # 骨架结构 / 共享 CSS 类约定 / 注记框格式 / golden 样例
│   └── subagent-dispatch.md           # 分区 subagent prompt 模板
└── scripts/
    └── validate_mock_board.py         # P4 机检（exit code 拦截）
```

注册三处（实现时一并完成）：

1. `.agents/skills/skill-rules.json`：promptTriggers 关键词
   （mock board / mock html / 看看产品长什么样 / UI mock / PRD 转界面 / 原型板 / wireframe）
2. `AGENTS.md` AI Workflow Entry Points 加一行
3. `docs/reference/guides/ai-workflow.md` 更新链路图

遵守 `.agents/skills/_shared/vj-skill-conventions.md` 全部 checklist
（瘦 SKILL.md、无人值守 fallback、失败兜底表、真相源只指针不复述、机检脚本、后置审查钩子）。

## 8. 引用完整性

被引用的 skill / 文档均已核实存在：`vj-design-md-matcher`、`vj-product-requirements`、
`vj-epic-story`、`vj-epic-plan`、`ui-state-coverage`、`ui-visual-consistency-audit`、
`web-access`、`.agents/skills/_shared/ui-planning-contract.md`、`docs/project/DESIGN.md`。

## 9. 明确不在本期范围

- 板内锚点跳转模拟流程（被拒的产物形态 C，如后续真需要再议）
- 按 Epic 局部重生成（被拒的生命周期方案 B）
- 深色模式 mock（DESIGN.md operational 轨有 `.dark` 组，但 mock 阶段只出 light；
  front-of-house 轨本身 light-only）
- 多方案/多保真度变体（Magdoub 式 5 方案 × 3 档）——本 skill 定位是"看产品长什么样"的
  单一方向快照，方向探索属 `vj-design-md-matcher` 轨
