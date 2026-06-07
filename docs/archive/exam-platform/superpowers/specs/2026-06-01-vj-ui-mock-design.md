# vj-ui-mock 设计文档

**日期**: 2026-06-01
**状态**: 已确认设计，待写实现计划
**类型**: 新增 repo-local skill

---

## 1. 问题与定位

当前 vibejet 的 AI 工作流链路是：

```
vj-product-requirements → vj-architecture → vj-epic-story
  → run-story → (do-story / story-reference-impl)
  → story-verify-fix → review → diff-aware-qa
```

链路里**预留了消费 UI 设计稿的接口**（`do-story` 会从 `docs/reference/research/designs/{epic-id}/` 发现设计图；Story 有 `#### 前端验收标准`；`story-verify-fix` 做视觉对齐），但**缺少生产端**——没有任何 skill 负责产出设计稿或给 v0/Lovable 的提示词。设计稿被假设为"用户从外部塞进来的输入"。

`vj-ui-mock` 补上这个缺口。

### 解决

- 产出**全局设计基座**（信息架构、导航骨架、设计系统），保证跨 Epic 的 UI 衔接一致。
- 产出**每屏的 v0/Lovable 提示词**，每屏继承同一基座，天然一致。

### 不做（边界）

- 不直接生成图片——把"喂 v0 出图"留给人或外部工具。
- 不碰后端 / 系统架构 / 技术选型——归 `vj-architecture`。
- 不写前端代码——归 `do-story`。

### 工作流位置

```
PRD → vj-architecture → vj-epic-story →【vj-ui-mock】→ run-story
```

---

## 2. 核心设计：两阶段

「UI mock」被拆成两层，因为**会 churn 的层和需要全局的层不是同一层**：

| 层 | 内容 | 变化频率 | 处理方式 |
|----|------|---------|---------|
| 设计基座 | 信息架构、导航骨架、设计系统、三态约定 | 低（实现完 epic1 也基本不动） | 全局出一次 |
| 逐屏详细稿 | 某屏的完整布局 + 状态 | 高（实现完就想调） | 随实现节奏按需出 |

衔接（"epic2 的 UI 怎么接上 epic1"）是**设计基座层**的属性，不靠"把所有屏一次画完"。churn 被限制在逐屏层、且只在实现时发生。

```
Phase A  设计基座（全局，一次）
  输入: PRD（角色/价值） + 全部 epic/story（枚举所有屏） + CLAUDE.md（前端栈）
  产出: docs/project/design_guidelines.md

Phase B  逐屏提示词（按 target，按需）
  输入: target 解析出的屏集合 + design_guidelines.md
  产出: 每屏一个 v0/Lovable 提示词
        （头部 = design_guidelines.md 的 v0 Base Prompt 段整段拷贝 + 本屏专属内容）
        存盘 + 回填 Story 设计参考
```

**衔接保证**：所有屏的提示词都拷贝同一段 `v0 Base Prompt`，因此 epic2 的屏自动套用 epic1 的导航外壳和设计 tokens。

---

## 3. design_guidelines.md 结构（Phase A 产出）

写入 `docs/project/design_guidelines.md`（该路径已被 epics README 的 `source_documents` 预留）。

MVP 原则：每节短写，够 v0 生成一致 UI 即可，不写长篇设计规范。

| # | Section | 作用 |
|---|---------|------|
| 1 | 前端栈快照 | MUI v9 / React 19 / TanStack，"用这套生成"。冗余记录（来自 CLAUDE.md），让提示词自包含 |
| 2 | 信息架构 / 站点地图 | 枚举所有屏 + 路由 + 所属角色 + 来源 epic。衔接骨架① |
| 3 | 导航外壳 | 持久布局：header（logo/用户名/登出）、按角色的侧边导航、路由嵌套方式。衔接骨架② |
| 4 | 设计 tokens | 配色（主/辅/语义）、字体阶、间距、圆角 |
| 5 | 共享组件 + 状态约定 | 按钮/表单/卡片/表格/对话框，**尤其空态/loading/错误态三态规范**（本产品每个 AI 环节都需要，PRD §4.2） |
| 6 | 角色 UX 规则 | 出题管理员 vs 员工考生 各自可见内容、导航差异（本产品有严格数据可见性边界） |
| — | `## v0 Base Prompt` | 抽 §1/3/4/5 压成的整段工具中立自然语言。Phase B 直接整段拷贝（选项 A：单一事实源、零漂移） |

---

## 4. 输入模型（屏为单位）

- `target` 接受任意组合：`epic-4` / `4.2` / 多个混合。**内部归并去重成「屏清单」**，1 个还是 N 个 epic/story 走同一代码路径（无单/多特例）。
- 屏来源：扫 target 范围内 Story 的 `#### 前端验收标准`，提取路由 + 元素 + 状态 + 角色，**按路由归并成屏**（一个屏可能跨多个 Story 的 AC）。
- **默认引导单 Epic**；多 Epic 作为显式 opt-in，文档明确提示"出一个、实现一个、再出下一个"以对抗 MVP 阶段全量返工。
- **缺口反馈**：有 UI 但缺 `#### 前端验收标准` 的 Story → 显式报出，不静默跳过（成为补 Story 的信号）。

---

## 5. 产出物落盘与回填

- 提示词：`docs/reference/research/designs/{epic-id}/{story-id}-{page}.prompt.md`
- 用户用 v0 出的图回灌到既有约定：`docs/reference/research/designs/{epic-id}/{story-id}-{page}.png`（沿用 ai-workflow.md §5 的 `{page}` 命名，不另造 token）
- 回填：写入 Story 的 `### 设计参考` 表格 → `story-verify-fix` 视觉对齐据此进行，mock ↔ 实现 ↔ 验证锁同一事实源。

---

## 6. 前置依赖

- Phase B 运行前检查 `docs/project/design_guidelines.md`。
- **不存在 → 提示先跑 Phase A**，不静默猜测设计基座。

---

## 7. 与 vj-architecture 的边界

本项目技术栈写死在 CLAUDE.md（Vite 8 + React 19 + MUI v9 + TanStack），所以 `design_guidelines.md` 不选技术栈，只定**视觉/交互设计语言**。

| | vj-architecture | vj-ui-mock Phase A |
|---|---|---|
| 管 | 后端/系统架构、DDD 分层、数据流、技术选型 | 视觉设计语言、信息架构、导航骨架、组件用法 |
| 产出 | architecture.md | design_guidelines.md |

边界划分：职责不重叠（决策 A）；但 design_guidelines.md **冗余记录一份前端栈快照**（决策 B），让 v0 提示词自包含，不依赖 v0 去读 architecture.md。

---

## 8. 复用边界：不依赖 ln-114

环境中存在 `documentation-pipeline:ln-114-frontend-docs-creator`，也产出 design_guidelines.md（偏 WCAG / 通用设计系统）。

**决策：Phase A 自产，不依赖 ln-114。** 理由：我们需要它不产出的两样东西——
1. `v0 Base Prompt` 段；
2. 从**本 repo 的 epic/story 格式**抽出的屏级站点地图。

section 结构保持与通用设计文档兼容，日后想替换不冲突。

---

## 9. 不在 scope（YAGNI，v1 不做）

- 跨 Epic 流程图 / 屏间跳转建模
- 屏的智能去重启发式（仅做按路由的朴素归并）
- 多套设计主题对比
- 直接调用图片生成

---

## 10. 关键决策记录

| 决策 | 选择 | 理由 |
|------|------|------|
| 主输入 | Story 的 `#### 前端验收标准`（非 PRD） | 与 story-verify-fix 共享事实源；颗粒度天然匹配；工作流最新产物；PRD 可能缺席 |
| 工作单位 | 屏（screen） | 单 Story 太碎、整 Epic 太粗、屏匹配 v0 实际工作单位 |
| 全局 vs 按需 | 基座全局一次 + 逐屏按需 | 衔接靠基座，churn 限在逐屏层 |
| 支持多 epic/story | 输入层支持，工作流层默认引导单 Epic | 归并到屏后多个免费；但全量提前出图易返工 |
| Phase A vs architecture | 职责不重叠 + 冗余栈快照（决策 B） | 栈已固定，Phase A 只管视觉；提示词需自包含 |
| Base Prompt 存储 | design_guidelines.md 内的 fenced section（选项 A） | 单一事实源、零漂移、Phase B 只拼接 |
| 复用 ln-114 | 不依赖，自产 | 需要 Base Prompt 段 + repo 专属屏站点地图 |

---

## 11. 验收标准（skill 本身）

- [ ] `vj-ui-mock` SKILL.md 存在于 `.agents/skills/vj-ui-mock/`，含 Phase A / Phase B 两阶段流程
- [ ] Phase A 能从 PRD + 全部 epic/story 生成含 6 节 + `v0 Base Prompt` 段的 design_guidelines.md
- [ ] Phase B 接受 `epic-X` / `X.Y` / 混合 target，归并去重成屏清单
- [ ] Phase B 缺 design_guidelines.md 时提示先跑 Phase A，不静默生成
- [ ] 每屏提示词头部为 Base Prompt 段整段拷贝
- [ ] 缺 `#### 前端验收标准` 的 UI Story 被显式报出
- [ ] 提示词落盘到约定路径并回填 Story 设计参考表
- [ ] ai-workflow.md 更新，把 vj-ui-mock 接入链路
