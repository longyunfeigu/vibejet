---
name: vj-ui-mock
description: 为前端项目产出全局设计基座与每屏 v0/Lovable 提示词。Phase A 从 PRD 与全部 Epic/Story 生成 docs/project/design_guidelines.md（信息架构、导航骨架、设计系统、三态约定）；Phase B 把指定的 Epic/Story 归并成屏清单，每屏生成继承基座的 UI 提示词并回填 Story 设计参考。适用于已有 Epic/Story、准备进入前端实现、需要保证跨 Epic UI 衔接一致的场景。不直接生成图片，不做技术选型，不写前端代码。
---

# vj-ui-mock

补上 AI 工作流缺失的「UI 设计生产端」。链路位置：

```
PRD -> vj-architecture -> vj-epic-story -> 【vj-ui-mock】-> run-story
```

## 核心模型：两阶段

「UI mock」分两层，会 churn 的和需要全局的不是同一层：

- **设计基座（Phase A，全局一次）**：信息架构、导航骨架、设计系统、三态约定。变化频率低。**跨 Epic 衔接靠这层。**
- **逐屏详细稿（Phase B，按需）**：某屏的具体提示词。随实现节奏出，churn 限制在此层。

衔接保证：每屏提示词都拷贝同一段 `v0 Base Prompt`，epic2 的屏自动套 epic1 的外壳与 tokens。

## 适用 / 不适用

适用：
- 已有 Epic/Story（`docs/tasks/epics/`），准备做前端
- 想先有全局设计基座，再逐屏出 v0/Lovable 提示词
- 关心跨 Epic 的 UI 一致性

不适用：
- 还没有 Epic/Story（先用 `vj-product-requirements` / `vj-epic-story` / `vj-feature`）
- 要直接出图片（本 skill 只产提示词，出图交给 v0/Lovable 等工具）
- 要做后端/系统架构（用 `vj-architecture`）或写前端代码（用 `do-story`）

## 不做（边界）

- 不直接生成图片
- 不碰技术选型（栈从 CLAUDE.md 读；前端栈只在 design_guidelines.md 里冗余快照，方便提示词自包含）
- 不写前端代码
- v1 不做：跨 Epic 流程图、屏间跳转建模、屏智能去重、多套主题对比

## 输入

- `target`（Phase B 用）：接受任意组合
  - `epic-4` 或 epic 文件名 -> 该 Epic 全部屏
  - `4.2` -> 该 Story 涉及的屏
  - 多个混合（空格/逗号分隔），或 `all`
- 无 target -> 默认走 Phase A（或在 Phase A 已存在时询问要对哪个 Epic 跑 Phase B）

## Phase A：生成设计基座（全局，一次）

目标：产出 `docs/project/design_guidelines.md`。

1. **加载模板**：读取本 skill 目录的 `design_guidelines.template.md`。
2. **检测已有**：若 `docs/project/design_guidelines.md` 已存在 -> 进入增量更新（保留已确认内容，只补/改受影响节），不全量覆盖。
3. **读输入**：
   - `docs/project/requirements.md`（若存在）：取角色定义、核心价值、非功能里的 UI 相关约束（空态/loading/失败）
   - `docs/tasks/epics/` 全部 Epic：枚举所有屏（两种 Epic 布局都要扫，见「Epic/Story 布局」与「屏归并规则」）
   - `CLAUDE.md`：前端栈快照（§1）
   - `docs/project/architecture.md`（若存在）：仅取与前端相关的约束，不复制后端架构
4. **填 6 节**：信息架构（§2 站点地图用屏归并结果）、导航外壳（§3）、tokens（§4）、共享组件+三态（§5，结合 PRD 非功能要求）、角色 UX（§6，结合 PRD 角色边界）。每节短写。
5. **写 `## v0 Base Prompt` 段**：把 §1/§3/§4/§5 压成一段工具中立自然语言，以"请...设计下面这个具体页面："收口。
6. **[BLOCKING] 用户确认**：展示 design_guidelines.md 草案（尤其 §3 导航外壳 + v0 Base Prompt 段），用户确认后写入 `docs/project/design_guidelines.md`。

## Phase B：逐屏提示词（按 target，按需）

目标：对 target 涉及的每个屏产出一份 v0/Lovable 提示词。

1. **前置检查**：`docs/project/design_guidelines.md` 不存在 -> **停止并提示先跑 Phase A**，不静默生成基座。
2. **解析 target -> Epic/Story 集合**：把 `epic-N` / Story id / 混合 / `all` 解析到 `docs/tasks/epics/` 下的具体 Story。注意本仓库 Epic 有两种布局（见「Epic/Story 布局」）：单文件 Epic 用 `N.M` 形式的 Story id；目录式 Epic 用 `usNNN` 形式。
3. **屏归并**（见下规则）：扫范围内每个 Story 的 `#### 前端验收标准`，按路由归并成屏；去重。
4. **缺口反馈**：范围内有 UI 但缺 `#### 前端验收标准` 的 Story -> 显式列出（成为补 Story 的信号），不静默跳过。
5. **默认引导单 Epic**：若 target 跨多个 Epic，提示"建议出一个、实现一个、再出下一个"，确认后再批量。
6. **逐屏生成**：用 `v0-prompt.template.md`，头部整段拷贝 design_guidelines.md 的 `v0 Base Prompt` 段，填入本屏 路由/角色/元素/四态/交互 与关联 AC。
7. **落盘**：`docs/reference/research/designs/{epic-id}/{story-id}-{page}.prompt.md`（目录不存在则创建）。`{epic-id}` 用 `epic-N` 形式（与 epic 文件前缀及 ai-workflow.md §5 的 `epic-003` 示例一致），如 `epic-1`。
8. **回填 Story**：在对应 Story 的 `### 设计参考` 区登记该屏提示词与预期截图路径 `{story-id}-{page}.png`。
9. **告知用户**：列出生成的屏 + 提示词路径 + 下一步（把提示词粘进 v0/Lovable，出图回灌为同名 .png）。

### Epic/Story 布局

本仓库 `docs/tasks/epics/` 下 Epic 有两种布局，解析时都要覆盖：

- **单文件 Epic**：`epic-N-<slug>.md`，内含若干 `### Story N.M` 段，Story id 形如 `1.1`、`4.2`。
- **目录式 Epic**：`epic-N-<slug>/`，含 `epic.md` + `stories/usNNN-<slug>.md`（一文件一 Story），Story id 形如 `us003`。

`{epic-id}` 统一取 `epic-N`（落盘目录名）；`{story-id}` 取该 Story 的原始 id（`N.M` 或 `usNNN`）。

### 屏归并规则

- 一个「屏」= 一个路由（page）。
- 来源：Story 的 `#### 前端验收标准` 里 `验证: Browser ...` 行的路由——可能在 `Browser` 之后（如 `Browser /admin/papers/new`），也可能在断言里（如 `→ url=/`）。两处都要识别。
- 同一路由跨多个 Story 的 AC -> 合并到同一屏（元素/状态取并集）。
- 角色：取 Story 用户故事中的角色 / 该 Epic 的角色边界。
- 路由里的动态段（如 `/exam/{id}`）按模板屏处理，不为每个实例建屏。
- 后端类 Story（无 UI，自然没有 `#### 前端验收标准`，如自动判分）不产屏，也不计入缺口反馈。

## 产出物

- `docs/project/design_guidelines.md`（Phase A）
- `docs/reference/research/designs/{epic-id}/{story-id}-{page}.prompt.md`（Phase B，每屏一份）
- 回填到各 Story 的 `### 设计参考`

## 与其他 skill 的关系

- `vj-epic-story` / `vj-feature`：上游，产出 Epic/Story（vj-ui-mock 的输入来源）
- `vj-architecture`：边界——它管后端/系统架构与技术选型；vj-ui-mock Phase A 只管视觉/IA/导航
- `do-story`：下游，消费 `### 设计参考` 里的设计图实现前端
- `story-verify-fix`：下游，视觉对齐用的就是回填进 Story 的同名截图
- `documentation-pipeline:ln-114`：也产 design_guidelines.md（偏通用/WCAG）；本 skill 自产不依赖它，因为需要 `v0 Base Prompt` 段与本 repo epic/story 格式的屏站点地图

## 触发示例

```text
/vj-ui-mock                 # 先出全局设计基座（Phase A）
/vj-ui-mock epic-1          # 出 epic-1 所有屏的提示词（Phase B）
/vj-ui-mock 4.2             # 只出 Story 4.2 涉及的屏
/vj-ui-mock epic-1 epic-2   # 多 Epic（会提示按需，默认引导单 Epic）
```
