---
name: do-story
description: 从 Epic/Story 文件启动实现工作流，自动读取现有设计文档约束，并在命中接口契约或数据模型变化时按需提示更新相关设计文档，执行 DDD 合规检查
allowed-tools: ["Bash(${SKILL_DIR}/scripts/setup-do-story.py:*)"]
---

# do-story - Story-Driven Feature Development

从 Epic/Story 文件启动结构化实现工作流，自动注入设计文档约束。

## Constraint Model

`do-story` 需要区分两类约束：

1. **Repo 硬约束**：始终可校验
   - DDD 分层方向
   - `BusinessException` / logging / 类型提示 / 测试要求
   - 现有代码库的目录结构、命名和实现模式

2. **设计文档约束**：只有文档存在时才可对照校验
   - `docs/project/architecture.md`
   - `docs/project/api/conventions.md` + `docs/project/api/{module}.md`
   - `docs/project/data/overview.md` + `docs/project/data/{module}.md`
   - Epic `source_documents.*`

旧 `docs/project/api_spec.md` / `docs/project/database_schema.md` 仅作为兼容读取 fallback。

如果对应模块文档不存在：
- 不要声称“实现违背了 API / 数据模型文档”
- 只能判断“这次 Story 是否引入了新的接口契约 / schema / migration 变化”
- 如果答案是是，则应把该变化升级为一个需要补充的 delta 文档，而不是假装存在基线

## Execution Modes

### 1. Single Story Mode
```
/do-story docs/tasks/epics/epic-001.md#story-1.2
```
实现指定的单个 Story。

### 2. Epic Mode (Multi-Story)
```
/do-story docs/tasks/epics/epic-001.md
```
解析 Epic 文件中所有 Stories，允许用户选择要实现的 Stories，然后顺序执行。

---

## Phase 0: 初始化 (REQUIRED)

### Step 1: 询问设计文档

Use AskUserQuestion:
```
本次 Story 是否命中了需要先补设计文档的变更?
- 否，直接进入实现 (推荐)
- 是，涉及较大架构影响，先运行 /vj-architecture
- 是，接口契约变化明显，先运行 /api-design
- 是，数据模型 / migration 变化明显，先运行 /data-model
```

### Step 2: 初始化状态

```bash
python3 "${SKILL_DIR}/scripts/setup-do-story.py" "<epic-path>[#story-id]"
```

**Single Story Mode** (带 #anchor):
- 直接初始化指定 Story 的状态

**Epic Mode** (无 #anchor):
- 解析 Epic 文件，列出所有 Stories
- 输出 `STORIES_FOUND:` 格式供 Claude 解析
- Claude 使用 AskUserQuestion 让用户选择要实现的 Stories
- 用户选择后，再次调用 setup 脚本传入选择的 Stories

```bash
# 第一步: 扫描 Stories
python3 "${SKILL_DIR}/scripts/setup-do-story.py" "docs/tasks/epics/epic-001.md" --scan

# 第二步: 初始化选定的 Stories
python3 "${SKILL_DIR}/scripts/setup-do-story.py" "docs/tasks/epics/epic-001.md" --stories "1.1,1.2,1.3"
```

这会创建 `.claude/do-story.{task_id}.local.md`，包含:
- Story 内容和验收标准
- 从 docs/project/architecture.md 提取的架构约束
- 从 docs/project/api/*.md 提取的 API 契约（如存在；否则兼容读取 api_spec.md）
- 从 docs/project/data/*.md 提取的数据模型（如存在；否则兼容读取 database_schema.md）
- DDD/Hexagonal 合规规则
- Epic 模式下的多 Story 状态跟踪

### Step 3: 读取状态文件

初始化后，使用 Read 工具读取生成的状态文件，获取完整的 Story 内容和设计约束。

## Phase 1: Understand (分析)

**目标**: 理解现有代码库，找到类似实现

**步骤**:
1. 读取状态文件中的设计约束
2. 分析代码库中的类似功能
3. 映射相关模块架构
4. 识别测试模式和规范

#### 前端 Story 视觉参考 [BLOCKING - 必须完成才能进入 Phase 2]

**适用条件**: Story 涉及前端 UI 实现（页面/组件）AND 满足以下任一条件：
- Design Constraints 中包含 `Prototype Structures` section
- Story 文件中包含「设计参考」表格（`### 设计参考`）
- `docs/reference/research/designs/` 下存在与当前 Story 对应的设计图

**纯后端 Story**: 跳过此 section，直接进入 Phase 2。

**前端 UI Story 但无任何外部参考**（确属页面/组件实现，但不满足上述三条）: **不跳过**——遵守 `.claude/rules/frontend.md` 与 `frontend-dev-guidelines` 的「Product Richness 剧本 B」：先分屏型（frontend.md R0），front-of-house 屏调 `design-taste-frontend` / `high-end-visual-design`，operational 屏改用 `frontend-dev-guidelines/resources/dense-ui-craft.md` + DESIGN.md §Richness Floor / §Spacing Hierarchy（design-taste 对后台 out-of-scope）；吃满 epic 页面体验地图，按整屏富度建，**不做 AC 最小的薄屏**。

**数据（所有前端 Story）**: 评审不许空屏——后端先行接真接口（dev 要有 seed），否则用 `features/<x>/mock*.ts` 占位，接口落地即删。

当条件满足时，按来源类型执行对应步骤：

---

##### 路径 A: 设计参考图（图片文件 / URL）

**触发条件**: Story 文件中包含「设计参考」表格，或 `docs/reference/research/designs/` 下有对应图片。

**设计图定位优先级**:
1. Story 文件里的 `### 设计参考` 表格
2. `docs/reference/research/designs/{epic-id}/` 下以当前 `{story-id}` 开头的图片文件
3. 用户在当前对话中显式给出的图片路径或 URL

**推荐命名**:
- `docs/reference/research/designs/{epic-id}/{story-id}-{page}.png`
- `docs/reference/research/designs/{epic-id}/{story-id}-{page}-{state}.png`

例如：
- `docs/reference/research/designs/epic-003/3.2-dashboard.png`
- `docs/reference/research/designs/epic-003/3.2-dashboard-empty.png`
- `docs/reference/research/designs/epic-003/3.2-dashboard-mobile.png`

**Step A1: 收集设计参考图**
- 检查 Story 文件中的 `### 设计参考` 表格，提取所有参考图路径/URL
- 如果 Story 无表格，检查 `docs/reference/research/designs/{epic-id}/` 目录下是否有匹配当前 Story ID 的图片
- 对于图片文件路径：用 Read 工具直接读取（Claude 可读取 PNG/JPG 等图片）
- 对于 URL 链接：用 `mcp__playwright__browser_navigate` 打开后 `mcp__playwright__browser_take_screenshot` 截图
- 如果上述两种自动发现都失败，但用户明确要求按设计稿还原，则必须要求用户手动指定图片路径或 URL，不要猜测

**推荐表格格式**：

```md
### 设计参考

| 页面/状态 | 参考图 | 类型 | 说明 |
|-----------|--------|------|------|
| 主页面 | docs/reference/research/designs/epic-003/3.2-dashboard.png | image | 桌面端 |
| 空状态 | docs/reference/research/designs/epic-003/3.2-dashboard-empty.png | image | 空列表 |
| 移动端 | https://... | url | 375px 宽度 |
```

**Step A2: 分析设计稿 [BLOCKING]**
逐张分析设计图，输出「设计分析清单」：

```markdown
### 设计分析清单

#### 布局结构
- 页面整体布局方式: {flex/grid/混合}
- 栅格系统: {列数、间距}
- 主要区域划分: {header/sidebar/main/footer}

#### 色彩方案
- 主色: {hex}
- 辅色: {hex}
- 中性色: {hex 范围}
- 背景色: {hex}
- 文字色: {主/次/辅助}

#### 字体层级
- 标题: {字号/字重/行高}
- 正文: {字号/字重/行高}
- 辅助文字: {字号/字重/行高}

#### 间距规律
- 组件间距: {px}
- 内边距: {px}
- 卡片间距: {px}

#### 组件拆解
| 组件名 | 位置 | 复用性 | 说明 |
|--------|------|--------|------|
| {name} | {区域} | {高/中/低} | {描述} |

#### 交互状态
- hover: {描述}
- active/pressed: {描述}
- disabled: {描述}
- loading: {描述}
- empty: {描述}

#### 响应式（如有移动端设计图）
- 断点: {px}
- 布局变化: {描述}
```

**Step A3: [BLOCKING gate] 确认设计分析**
使用 AskUserQuestion 让用户确认设计分析清单是否准确，是否需要调整。

---

##### 路径 B: 原型 HTML（Prototype Structures）

**触发条件**: Design Constraints 中包含 `Prototype Structures` section。

**Step B1: 从状态文件获取上下文（已嵌入，无需额外读取）**
- **Design Tokens**: tailwind.config 中的 colors/fonts/borderRadius（状态文件 `#### Design Tokens` 块）
- **Custom CSS**: 动画、滚动条等自定义样式（状态文件 `#### Custom CSS` 块）
- **§2 Component Mapping**: 组件拆分和 Props 定义
- **§3 Data Flow**: Hooks、Endpoints、Cache 策略

**Step B2: 确定当前 Story 对应的原型页面**
- 从 **§7 Implementation Priority** 表找到 Story ID → Page 映射
- 从 **Prototype Files** 表确认原型 HTML 文件路径

**Step B3: 读取完整原型 HTML [BLOCKING]**
状态文件的 `#### Prototype: {PageName}` 只包含截断的 body HTML（4000 chars）。
**你必须用 Read 工具读取完整的原型 HTML 文件**，提取：
- 完整的 HTML 结构作为 JSX 骨架
- 所有 Tailwind CSS classes（直接复用到 React JSX）
- 图标名称（Material Symbols）
- 交互状态样式（hover、active、dragging 等）

**Step B4: 输出原型提取清单（BLOCKING gate - 必须在报告中包含）**

在代码分析报告中必须包含以下内容，否则不能进入 Phase 2：

```markdown
### 原型视觉提取
- [ ] Design tokens 确认: {列出 primary color, font-family, border-radius}
- [ ] 当前 Story 对应页面: {page name} → {prototype file path}
- [ ] 组件结构: {列出从 HTML 提取的组件层级}
- [ ] 关键 Tailwind classes: {列出主要容器/卡片/按钮的 class}
- [ ] 自定义 CSS: {列出需要保留的自定义样式}
- [ ] 交互状态: {列出 hover/active/dragging 等状态样式}
```

---

##### 路径 C: 同时有设计图和原型 HTML

当两种来源都存在时，以**设计图为视觉基准**，以**原型 HTML 为结构参考**：
1. 先执行路径 A（分析设计图获取视觉规范）
2. 再执行路径 B（从原型提取 HTML 结构和 Tailwind classes）
3. 合并两份清单，设计图中的颜色/间距/字体优先级高于原型 HTML

**输出**: 代码分析报告，包含:
- 类似功能的 file:line 引用
- 架构层次映射
- 测试命令和文件位置
- **原型视觉提取清单（前端 Story 必须包含，见上方 BLOCKING gate）**

**完成后**: 更新状态文件
```yaml
current_phase: 2
phase_name: "Clarify"
```

## Phase 2: Clarify (澄清，条件性)

**目标**: 解决阻塞性问题

**规则**:
- 如果 Story 验收标准清晰 → 跳过，进入 Phase 3
- 如果有阻塞问题 → 使用 AskUserQuestion 询问

**完成后**: 更新状态文件
```yaml
current_phase: 3
phase_name: "Design"
```

## Phase 3: Design (设计)

**目标**: 生成实现蓝图。根据复杂度分级，决定是否进入 Claude Code plan mode。

### Step 1: Triage 分级

回答 `docs/tasks/plans/TEMPLATE.md` 的 Triage 八问，确定 Flow：

1. 是否只服务一个明确的用户目标？
2. 是否只影响一个业务模块？
3. 是否不改数据库 schema / migration？
4. 是否不改公共 API 契约？
5. 是否不涉及 domain 规则变化？
6. 是否不涉及外部系统、Celery、缓存、消息队列？
7. 是否不涉及权限、安全、幂等、复杂状态流转？
8. 预估是否只改少量文件且不超过 2 层？

| 条件 | Flow | 行为 |
|------|------|------|
| 8 问全”是” | **Flow A** | 轻量设计，不进 plan mode，直接在状态文件中输出设计 |
| 1-3 个”否” | **Flow B** | **进入 plan mode**，按 `docs/tasks/plans/TEMPLATE.md` 写 plan |
| 4+ 个”否” | **Flow C** | **进入 plan mode**，按 `docs/tasks/plans/TEMPLATE.md` 写完整 plan |

**强制升级条件**（碰到任一条 → 至少 Flow B）：改 DB migration、改公共 API 契约、改权限/认证/安全、引入外部系统或异步任务、复杂状态机/幂等/事务一致性、需求不清楚、影响多个 bounded context。

**Triage 判断细则（防止误判）**：

第 6 问"不涉及外部系统"的正确判断标准：
- **"是"（不涉及）**：仅调用已有 port 的既有方法，无新 prompt、无新解析逻辑、无新调用编排
- **"否"（涉及）**：构建新的 prompt 工程、解析新的结构化返回（JSON/XML）、编排多次外部调用序列、引入新的重试/超时/降级策略
- **"LLM port 已有"不等于"不涉及外部系统"**。如果 Story 需要设计新 prompt + 解析新格式 + 编排调用链，即使 port 抽象已存在，仍应判"否"

第 8 问"只改少量文件"的正确判断标准：
- 不要只数文件数量，还要评估**逻辑复杂度**。一个新建的 Dispatcher 文件如果包含 prompt 工程 + JSON 解析 + 多步编排，其复杂度等价于跨多层改动

### Step 2a: Flow A — 轻量设计（不进 plan mode）

直接在对话中输出：
- 文件变更清单
- 实现序列（按 DDD 层次）
- AC → 测试映射表

然后进入 Phase 4。

### Step 2b: Flow B/C — Plan Mode 设计

**执行流程**：

1. **调用 `EnterPlanMode`**
2. **在 plan mode 中深入探索代码**：利用 plan mode 的只读约束，充分读取相关文件、追溯依赖链、分析现有模式
3. **先读取 `docs/tasks/plans/TEMPLATE.md`**，获取完整模板结构
4. **严格按模板结构写 plan 文件**到 `docs/tasks/plans/{date}-{story-id}-{slug}.md`
5. **在 plan 末尾附加 AC → 测试映射表**（BLOCKING，见下方格式）
6. **调用 `ExitPlanMode`** 等待用户审批
7. 用户审批通过后，进入 Phase 4

**Plan 文件结构强制要求（BLOCKING — 缺少必填节则不能 ExitPlanMode）**：

必须使用 `docs/tasks/plans/TEMPLATE.md` 中的 section 标题和结构，**不允许用自由格式替代**。

| Section | Flow A | Flow B | Flow C | 说明 |
|---------|--------|--------|--------|------|
| `## 0. Triage` | — | 必填 | 必填 | 八问 + 分级结论 + Scope Challenge + 本次必须产出 |
| `## 1. 目标` | — | 必填 | 必填 | 要解决的问题 + 改完后的用户结果 |
| `## 2. 范围` | — | 必填 | 必填 | In Scope + NOT in scope |
| `## 3. 影响范围` | — | 必填 | 必填 | 文件变更表 + "不会修改"清单 |
| `## 4. 风险` | — | 必填 | 必填 | 主要风险 + 边界情况 + 回滚方式 |
| `## 5. 验收标准` | — | 必填 | 必填 | 从 Story AC 复制 |
| `## 6. 术语与代码对象` | — | 按需 | 按需 | 5+ 新概念时 |
| `## 7. 当前现状` | — | 必填 | 必填 | What already exists（可复用/需改造/不应重复建设） |
| `## 8. 方案概述` | — | 必填 | 必填 | 改动思路 + 为什么这样做 |
| `## 8.1 API Contract Delta` | — | 改 API 时 | 改 API 时 | 端点变化表 + 错误与兼容性 |
| `## 8.2 设计参考` | — | 有设计稿时 | 有设计稿时 | 设计参考图表 |
| `## 9. 核心流程` | — | 有流程变化时 | 必填 | 改动前/后 Mermaid 图 + Failure Modes 表 |
| `## 10. 关键实现细节` | — | — | 必填 | 数据结构/状态流转/异常/兼容性 |
| `## 10.1 Schema/Migration Delta` | — | 改 DB 时 | 改 DB 时 | 对象变化表 + 索引约束 |
| `## 11. 执行步骤` | — | 必填 | 必填 | 每步 = task + 涉及文件 + commit |
| `## AC → 测试映射表` | — | 必填 | 必填 | 见下方格式 |

**自检清单（ExitPlanMode 前必须确认）**：
- [ ] plan 文件路径格式正确：`docs/tasks/plans/{date}-{story-id}-{slug}.md`
- [ ] §0 Triage 八问已回答，Flow 分级已标明
- [ ] §0 Scope Challenge 四问已回答（不是跳过）
- [ ] §7 What already exists 列出了可复用代码（不是空的）
- [ ] §11 执行步骤每步有明确的文件列表和 commit 粒度
- [ ] AC → 测试映射表 100% 覆盖所有 AC checkbox

### AC → 测试映射表（Flow A/B/C 均必须）

无论走哪个 Flow，都必须输出此表：

  | # | AC 原文 | 验证方式 | 执行引用 | 预期结果 | 类型 |
  |---|---------|---------|----------|----------|------|
  | 1 | (逐条从验收标准复制) | (从 AC 的 `验证:` 标注提取) | (见下方规则) | (可断言的预期) | unit/integration/api/browser |

  **执行引用填写规则**（按类型区分）：
  - `pytest` / `unit` / `integration`: **必填** `tests/{layer}/test_{module}.py::test_{func}`
  - `API`: **必填** `METHOD /path`（如 `POST /auth/register`）
  - `DB`: **必填** `SELECT ... FROM ... WHERE ...`
  - `Browser`: **可选** 填写 DOM 操作步骤（如 `click button[type=submit] → .toast exists`），无需测试文件

  映射规则：
  - 每个 Given-When-Then 场景 → 至少一个测试函数
  - 正常流程 → 正向测试 (assert 200/201/204)
  - 异常流程 → 错误测试 (assert 400/404/409/422)
  - 边界条件 → 边界测试
  - Domain 层业务规则 → 独立的单元测试（不依赖 HTTP）
  - 前端 Story → 组件测试 + 视觉验证清单

  **完整性门控（BLOCKING）**：
  - 统计 Story 中所有 AC checkbox 数量 → `total_ac`
  - 统计映射表中已映射的 AC 数量 → `mapped_ac`
  - 如果 `mapped_ac < total_ac`，列出未映射的 AC 并**阻塞进入 Phase 4**
  - 未映射原因通常是 AC 写得太模糊无法转为测试 → 使用 AskUserQuestion 要求用户澄清该 AC

### 设计文档约束判断规则

在 plan 中评估 API / 数据模型变化时：
- **有文档时**：可以判断”是否与现有设计说明不一致”
- **无文档时**：只能判断”是否产生了新的 contract / schema delta，需要补充说明”
- **无文档时禁止输出**：”违反 docs/project/api/{module}.md” 或 “违反 docs/project/data/{module}.md” 这类结论

**完成后**: 更新状态文件
```yaml
current_phase: 4
phase_name: “Implement”
```

## Phase 4: Implement + Review (实现 + 审查)

### 4.1 TDD 实现

#### 后端 Story：按 DDD 层次 Red-Green-Refactor

按 Domain → Application → Infrastructure → API 顺序，每层：

**Step A: RED - 从 AC 生成失败测试**
1. 根据 Phase 3 的 AC → 测试映射表创建测试文件
2. 测试函数名直接反映 AC 场景：`test_{ac_scenario_name}`
3. 运行测试确认失败：`cd backend && pytest tests/{layer}/test_{module}.py -v`
4. 确认失败原因是功能缺失（ImportError / AssertionError），非语法错误

**Step B: GREEN - 最小化实现**
1. 编写刚好让测试通过的代码
2. 运行当层测试：`cd backend && pytest tests/{layer}/test_{module}.py -v`
3. 运行全量测试确认无回归：`cd backend && pytest -v`

**Step C: REFACTOR**
1. 消除重复、改善命名
2. 保持所有测试绿色

**实现顺序（每层完成后 commit）**:
1. Domain 实体 → 单元测试验证 AC 中的业务规则 → commit
2. Application 服务 → 单元测试验证用例编排（内存假仓储）→ commit
3. Infrastructure 仓储 → 集成测试验证持久化 → commit
4. API 路由 → API 测试覆盖 AC 中的所有 HTTP 场景 → commit

#### 4.1.1 Checkpoint 状态更新（每层 commit 后必须执行）

每完成一个 DDD 层的 RED-GREEN-REFACTOR 并 commit 后，使用 Edit 工具更新状态文件的 checkpoints：

```yaml
# Schema per checkpoint entry:
#   layer: string (required)
#   status: "pending" | "in_progress" | "completed" (required)
#   commit: string (required when status=completed)
#   tests_passing: bool (required when status=completed, backend only)
#   verified: bool (required when status=completed, frontend only)
#   files: list[string] (optional, populated during in_progress/completed)
checkpoints:
  - layer: "domain"
    status: "completed"          # pending | in_progress | completed
    commit: "<git commit hash>"  # 该层 commit 的 short hash
    tests_passing: true
    files:
      - "backend/domain/{module}/entity.py"
      - "backend/domain/{module}/repository.py"
  - layer: "application"
    status: "in_progress"        # ← 当前正在进行的层
    files: []
  - layer: "infrastructure"
    status: "pending"
  - layer: "api"
    status: "pending"
```

**恢复规则**：当新 session 读取状态文件时：
1. 找到第一个非 "completed" 的 checkpoint：
   - 如果 `status: "in_progress"`: 检查 `files` 列表中的文件是否存在，运行该层测试判断是否处于 RED 或 GREEN 阶段，从对应步骤继续
   - 如果 `status: "pending"`: 从该层的 RED 步骤开始
2. 如果上一个 checkpoint 有 `commit` 字段，运行 `git log --oneline -1 <commit>` 验证 commit 存在
3. 运行 `cd backend && pytest -v` 验证已完成层的测试仍通过

**前端 Story 的 Checkpoint**：
```yaml
checkpoints:
  - layer: "components"
    status: "completed"
    commit: "<hash>"
    verified: true
    files:
      - "frontend/src/pages/{Page}.tsx"
      - "frontend/src/components/{Component}.tsx"
  - layer: "hooks-services"
    status: "in_progress"
    files: []
  - layer: "visual-verification"
    status: "pending"
```

#### 前端 Story：组件实现 + 视觉验证

**Step A: 组件实现**
1. 按 docs/project/design_guidelines.md 创建组件（复用 prototype HTML 结构和样式）
2. Hook + Service 层数据接入
3. commit

**Step B: 视觉验证（使用 web-access CDP）**

前提：确认后端 + 前端开发服务器运行中。如未运行，提示用户启动。
使用前先运行 `bash ~/.claude/skills/web-access/scripts/check-deps.sh` 确保 CDP Proxy 就绪。

逐条验证 Story AC：

```
对于每个 AC 场景:
1. 准备 Given 条件（导航到正确页面、准备测试数据）
   → /new 或 /navigate 打开目标 URL
2. 执行 When 动作（点击、填表、提交）
   → /click / /type / /eval 执行页面交互
3. 验证 Then 结果（检查元素、URL、状态）
   → /eval 断言 DOM 状态
4. 截图存证
   → /screenshot?target=ID&file=tmp/{story_id}_{ac_name}.png
```

验证清单（对照 Story AC）：
- 正常流程：元素渲染、交互响应、路由跳转
- 异常流程：错误提示正确显示
- 边界条件：空状态、加载态、骨架屏
- 非功能：响应速度可感知

**Step C: 设计稿对比验证（当 Story 有设计参考图时）**

当 Phase 1 产出了「设计分析清单」时，额外执行设计还原验证：

1. 用 `/screenshot?target=ID&file=path` 截取实现后的页面
2. 用 Read 工具读取原始设计图
3. 逐项对比设计分析清单中的关键指标：
   - 布局结构是否一致
   - 颜色是否匹配
   - 间距是否接近
   - 组件样式是否还原
4. 列出差异点，逐一修正
5. 修正后重新截图确认

### 4.2 自我审查 (DDD 合规检查)

**BLOCKING 级别检查** (必须通过):
- [ ] Domain 层没有导入 infrastructure/application/api
- [ ] Infrastructure 实现了 Domain 定义的 Repository 接口
- [ ] Application 层没有直接使用 ORM Model
- [ ] API 层只处理 HTTP I/O，无业务逻辑

**MINOR 级别检查** (建议修复):
- [ ] 文件位置符合分层规范
- [ ] 类型提示完整
- [ ] 异常使用 BusinessException

### 4.3 处理审查结果

- **BLOCKING 问题**: 必须修复才能继续
- **MINOR 问题**: 自动修复或记录 TODO

### 4.4 Design Doc 差异检测与回写 [RECOMMENDED]

**目标**: 检测实现与设计文档的偏差，提示更新。

**步骤**:

1. **收集实际实现清单**：
   - 实际创建的 API 端点（路径、方法、请求/响应 schema）
   - 实际创建的数据模型字段（表名、列名、类型、索引）
   - 实际的 Domain 实体和方法

2. **对比设计文档**：
   - 如果存在 API 契约文档，读取 `docs/project/api/conventions.md` + 相关 `docs/project/api/{module}.md`（或 source_documents.api_design 路径；旧 api_spec.md 仅 fallback）
   - 如果存在数据模型文档，读取 `docs/project/data/overview.md` + 相关 `docs/project/data/{module}.md`（或 source_documents.data_model 路径；旧 database_schema.md 仅 fallback）
   - 逐项对比，识别以下差异类型：

   | 差异类型 | 示例 |
   |----------|------|
   | 新增 | 设计文档中没有，实现中新增了字段/端点 |
   | 修改 | 类型/约束/路径与设计文档不同 |
   | 删除 | 设计文档中有，但实现中未包含 |

3. **输出差异报告**（如有差异）：

   ```markdown
   ### 📋 Design Doc 差异报告

   #### API Design (docs/project/api/{module}.md)
   | 变更 | 位置 | 设计文档 | 实际实现 | 原因 |
   |------|------|----------|----------|------|
   | 新增 | POST /api/v1/xxx | - | 新增 query 参数 `status` | 业务需要按状态过滤 |

   #### Data Model (docs/project/data/{module}.md)
   | 变更 | 表/字段 | 设计文档 | 实际实现 | 原因 |
   |------|---------|----------|----------|------|
   | 新增 | sessions.retry_count | - | Integer, default=0 | 重试逻辑需要 |
   ```

4. **用户确认**：

   使用 AskUserQuestion：
   ```
   实现过程中发现以下设计偏差，是否更新设计文档？
   - 更新相关增量设计文档（推荐）— 保持契约/模型说明与代码同步
   - 跳过，后续手动更新
   - 查看详细差异报告
   ```

5. **执行更新**（如用户确认）：
   - 使用 Edit 工具更新对应的模块文档；API 全局约定变化才改 `api/conventions.md`，数据表索引 / 跨模块关系变化同步改 `data/overview.md`
   - 在更新的段落末尾添加注释：`<!-- Updated by Story {story_id}, {date} -->`

**跳过条件**:
- 本次未命中 API / 数据模型变化
- 对应设计文档不存在，且本次无需沉淀增量说明
- 或实现与现有设计文档完全一致（无差异）

**完成后**: 更新状态文件
```yaml
current_phase: 5
phase_name: "Complete"
```

## Phase 5: Complete (完成)

**目标**: 生成完成摘要

**完成前必须确认**:
- [ ] 所有 AC 场景都有对应测试（后端）或视觉验证（前端）
- [ ] `cd backend && pytest -v` 全部通过
- [ ] 前端 Story：每个 AC 场景有截图验证记录
- [ ] 前端 Story（有设计参考图时）：最终截图 vs 设计稿对比完成，差异已修正
- [ ] 前端 Story：已过 `.claude/rules/frontend.md`「出口闸：品味」对应轨（front-of-house 走 A 轨 A1–A3；operational 走 B 轨 B1–B5 含工艺线 C1–C5），变更叙事按闸门要求留证据（组件/data-testid/间距实测/参考对照）；闸门条目以 frontend.md 为唯一真相源
- [ ] checkpoints 中所有层均为 "completed" 状态
- [ ] 所有 checkpoint 关联的 commit 存在于 git log 中
- [ ] Design Doc 差异已处理（如命中相关契约/模型变化，则已更新或确认跳过）

**输出**:
- 实现了什么功能
- 修改的文件列表
- 验证命令 (如何测试)
- 测试覆盖情况（AC → 测试映射完成度）
- Checkpoint 汇总（各 DDD 层的 commit hash 和文件列表）
- Design Doc 变更记录（如有更新）
- 后续建议 (可选)

**完成信号**:

在状态文件中添加完成标记，并输出:
```
<promise>DO_STORY_COMPLETE</promise>
```

## Context Pack 模板

每个 Phase 使用以下格式传递上下文:

```text
## Story
<from state file>

## Acceptance Criteria
<from state file>

## Design Constraints
### Architecture (from docs/project/architecture.md)
<层次规则、依赖方向>

### API Contract (optional, from docs/project/api/*.md)
<如存在，放相关端点定义；否则写 N/A>

### Data Model (optional, from docs/project/data/*.md)
<如存在，放相关表结构；否则写 N/A>

### DDD Compliance Rules [BLOCKING]
- Domain 层禁止导入: infrastructure/, application/, api/
- Infrastructure 必须实现 Domain Repository 接口
- Application 层禁止直接使用 ORM Model
- API 层只处理 HTTP I/O

## Current Phase
Phase X: <name>

## Current Task
<specific task>

## Previous Phase Outputs
- Phase 1 (Understand): <summary or "N/A">
- Phase 2 (Clarify): <summary or "Skipped">
- Phase 3 (Design): <summary or "N/A">
- Phase 4 (Implement): <summary or "N/A">
```

## 状态管理

每完成一个 Phase，使用 Edit 工具更新状态文件的 frontmatter:

```yaml
current_phase: <next phase number>
phase_name: "<next phase name>"
```

---

## Epic Mode: 多 Story 顺序执行

### Epic Mode 工作流

```
┌─────────────────────────────────────────────────────────────────┐
│  Phase 0: Story 选择 + 初始化                                    │
│  1. 解析 Epic 文件，列出所有 Stories (--scan)                    │
│  2. AskUserQuestion: 选择本次要实现的 Stories                    │
│  3. 运行 setup-do-story.py --stories "1.1,1.2" 初始化状态文件    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  循环: 对每个选中的 Story 顺序执行                               │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ for story in selected_stories:                              ││
│  │     Phase 1: Understand - 分析代码库中的类似实现             ││
│  │     Phase 2: Clarify - 条件性澄清阻塞问题                    ││
│  │     Phase 3: Design - 生成符合 DDD 的实现蓝图                ││
│  │     Phase 4: Implement + Review - 实现 + DDD 合规审查        ││
│  │     Phase 5: Complete - 生成 Story 完成摘要                  ││
│  │     → 更新状态: story.status = "completed"                   ││
│  │     → 移动到下一个 Story: current_story_index += 1          ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Epic 完成: 生成总结报告                                         │
│  - 所有 Stories 的实现摘要                                       │
│  - 修改的文件列表汇总                                            │
│  - 下一步建议: /commit-push-pr                                   │
│  - 输出: <promise>DO_STORY_COMPLETE</promise>                   │
└─────────────────────────────────────────────────────────────────┘
```

### Epic Mode 状态文件格式

```yaml
---
active: true
mode: "epic"                      # "story" | "epic"
epic_file: "docs/tasks/epics/epic-001.md"
epic_title: "User Authentication System"

selected_stories:
  - id: "1.1"
    title: "用户注册"
    status: "completed"           # pending | in_progress | completed
  - id: "1.2"
    title: "邮箱登录"
    status: "in_progress"
    current_phase: 3
    phase_name: "Design"
  - id: "1.3"
    title: "OAuth 集成"
    status: "pending"

current_story_index: 1            # 当前正在实现的 Story 索引
total_stories: 3

# 当前 Story 的 Phase 状态
current_phase: 3
phase_name: "Design"
max_phases: 5

completion_promise: "<promise>DO_STORY_COMPLETE</promise>"
---

# Current Story Content

[当前 Story 的详细内容]

# Design Constraints

[从 docs/ 提取的设计约束]
```

### Story 切换流程

当一个 Story 完成 Phase 5 后:

1. **更新当前 Story 状态**:
   ```yaml
   selected_stories[current_story_index].status: "completed"
   ```

2. **检查是否有下一个 Story**:
   - 如果 `current_story_index < total_stories - 1`:
     - `current_story_index += 1`
     - 重置 `current_phase: 1, phase_name: "Understand"`
     - 更新 `selected_stories[new_index].status: "in_progress"`
     - 继续执行 Phase 1
   - 如果没有更多 Story:
     - 生成 Epic 完成报告
     - 输出 `<promise>DO_STORY_COMPLETE</promise>`

### Epic 完成报告模板

```markdown
═══════════════════════════════════════════════════════════════
  ✅ Epic 实现完成!
  Epic: [epic_title]
═══════════════════════════════════════════════════════════════

### Stories 完成情况
| Story | Title | Status |
|-------|-------|--------|
| 1.1 | 用户注册 | ✅ Completed |
| 1.2 | 邮箱登录 | ✅ Completed |
| 1.3 | OAuth 集成 | ✅ Completed |

### 总体变更统计
- 文件修改: [count] 个
- 新增代码: [lines] 行
- 测试文件: [count] 个

### 下一步
建议运行: `/commit-push-pr`

<promise>DO_STORY_COMPLETE</promise>
```

---

## Common Rationalizations

| 偷懒借口 | 现实 |
|---------|------|
| "这个 Story 太简单，不需要走 Triage 八问" | Triage 就是用来验证"真的简单"的。跳过 Triage 等于盲猜 Flow，后面发现改 DB 或改 API 时才补 plan，返工更贵。 |
| "AC 很清楚了，不用写测试映射表" | AC 清楚 ≠ 测试覆盖清楚。映射表的目的是暴露"看起来清楚但没人写测试"的 AC。跳过它你会在 Phase 5 才发现缺测试。 |
| "先实现再补测试" | 后补的测试是按实现写的，不是按 AC 写的。TDD 的 RED 步骤就是防这个——先有失败测试，再有代码。 |
| "这层太薄了，不值得单独 commit" | 单层 commit 是你唯一的回滚粒度。把 domain + infrastructure 混在一个 commit 里，出问题时只能整体回退。 |
| "Domain 层导入一下 ORM 的类型标注应该没事" | 这不是类型标注问题，这是依赖方向问题。Domain 导入 Infrastructure 的任何符号，都破坏了六边形架构的核心约束。 |
| "这个 Story 不需要进 plan mode，我直接写" | Flow B/C 进 plan mode 的目的不是走流程，是强制你在只读状态下充分读代码。跳过它你会在实现中途才发现遗漏的依赖。 |
| "设计文档不存在，所以不用管设计约束" | 不存在 ≠ 不需要。如果你的改动引入了新 API 或新 schema，你要判断是否需要补 delta 文档，而不是假装没有约束。 |
| "AC 有一条太模糊了，我按自己理解实现" | 模糊的 AC 应该用 AskUserQuestion 澄清，不是用你的猜测替代用户的意图。猜错了返工比问一句贵得多。 |

## Red Flags

出现以下任何一条，说明执行质量不达标：

- Triage 八问没有逐条回答，直接跳到了 Flow A
- AC → 测试映射表的 `mapped_ac < total_ac`，但没有阻塞
- Phase 4 写代码时没有先跑 RED（失败测试），直接写实现
- 单个 commit 跨了两个以上 DDD 层
- Domain 层文件中出现 `from backend.infrastructure` 或 `from sqlalchemy`
- 状态文件的 `current_phase` 没有随 Phase 推进更新
- 前端 Story 没有执行视觉验证就标记完成
- Plan 文件缺少 §0 Triage 或 §7 What already exists
- 实现引入了新 API 端点或新 DB 表，但没有触发 Design Doc 差异检测

## Hard Constraints

1. **遵循 DDD 分层**: 所有代码必须按 Domain → Application → Infrastructure → API 分层
2. **BLOCKING 问题必须解决**: 发现 DDD 违规时，必须修复才能继续
3. **更新状态**: 每个 Phase 完成后必须更新状态文件
4. **Epic 模式顺序执行**: 必须完成当前 Story 所有 Phases 才能进入下一个 Story
5. **完成信号**: 最终必须输出 `<promise>DO_STORY_COMPLETE</promise>`
