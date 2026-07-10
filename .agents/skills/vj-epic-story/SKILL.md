---
name: vj-epic-story
description: Use when PRD and Architecture already exist and need to be decomposed into implementation-ready Epic/Story files with acceptance criteria. 用户说"拆 Epic""拆 Story""把需求拆成 epic/story""生成验收标准""epic story 拆分""规划 story""epic 划分"，或在 PRD+架构完成后准备拆分开发任务时使用。
---

# Epic & Story 规划

## 核心目标

通过结构化对话，将需求文档转化为可执行的 Epic + Story。输出轻量、聚焦验收标准，作为 `vj-epic-plan` 的 WHAT 输入，并由 `vj-work` 执行落地。

**你的角色**：产品策略和技术规格协调者，与用户平等协作。

---

## 工作流程（7 Phase）

| Phase | 职责 |
|-------|------|
| 1 | 初始化（加载模板 / 配置 / 检测已有，**不询问**） |
| 2 | Epic 识别（**Decompose-First**：IDEAL → 对比现状 → 差异表） |
| 2.5 | **Epic Quality Gate**（3 项体检，BLOCKING） |
| 2.6 | **Auto-Extract + 用户旅程 + Batch Question**（一次问完所有缺口 + System-Wide 6 维度） |
| 3 | Story 拆分（INVEST + Feature Bundling 拦截） |
| 4 | AC 生成（4 分类 + `验证:` 三要素 + 覆盖度自检） |
| 5 | **Batch Preview + 写盘**（写盘前批量预览 → 用户确认 → 完整性验证 → 写盘 → kanban 回写 → HTML 视图） |

### Phase 1: 初始化

1. **加载模板**：读取 `epic-story.template.md` 理解输出结构；用户交互的展示格式在
   `references/display-formats.md`（§A-§E），到对应 Phase 需要展示时再读，不预加载
2. **配置自动发现**（kanban_board.md）：
   - 检查 `docs/tasks/kanban_board.md` 是否存在
   - **存在** → 从 Tracker Configuration 表读取 `Next Epic Number` / `Next Story Number`；从 Epic Story Counters 拿已有 Epic 列表
   - **不存在** → 从 skill 目录 copy `kanban_board.template.md` 到 `docs/tasks/kanban_board.md`，替换 `{{PROJECT_NAME}}` / `{{DATE}}` 占位符
   - 这是后续所有 Epic / Story 编号的唯一源
3. **检测已有文档**（仅标记状态，不询问用户）：
   - 检查 `docs/tasks/epics/` 目录状态
   - 已有 Epic 文件（平铺 `.md` 或目录形式）→ 标记 `has_existing = true`，记录路径列表
   - 目录为空 → 标记 `has_existing = false`
   - **不要在此处询问"继续/添加/重写"**。决策推迟到 Phase 2.3 的差异对比阶段
   - 理由：用户在没看到"按当前需求该拆成啥"之前，无法判断该"继续/重写"，过早决策会造成 anchoring
4. **检测上游输入**：
   - **必需**: `docs/project/requirements.md` → 功能需求和用户故事
   - **必需**: `docs/project/architecture.md` → 技术约束和模块划分
   - **推荐**: `docs/project/api/` → 模块化接口定义（`conventions.md` + `{module}.md`）
   - **推荐**: `docs/project/data/` → 模块化数据结构（`overview.md` + `{module}.md`）
   - **推荐（前端 Epic）**: `docs/project/DESIGN.md` → 项目级设计系统合同；旧路径 `docs/project/design_guidelines.md` 仅作 fallback
   - **推荐（前端 Epic）**: `docs/project/ui/` → Screen / Route / 导航 / 状态合同；不存在时本 skill 必须从页面体验地图生成初始候选，交给 `vj-epic-plan` 写入 catalog
   - **推荐**: `docs/reference/research/designs/` → UI 设计稿（按 Epic 子目录组织）
   - 必需文档缺失 → 报错终止
5. **约束提取**（自动）：
   - 从 Architecture 提取：分层约束、模块划分、技术栈
   - 从 API Design 提取：端点列表、认证方案
   - 从 Data Model 提取：实体关系、主键策略
6. **配置确认**：

```
1. Epic 范围
   □ 全部功能（推荐）
   □ 特定模块
   □ 按优先级（MVP 必需）

2. 预期规模
   □ 小型（<5 Epic）→ 快速模式
   □ 中型（5-15 Epic）→ 标准模式
   □ 大型（>15 Epic）→ 完整模式

3. 每个 Epic 的 Story 数预估（决定输出结构）
   □ <3 Story → 平铺：epic-{N}-{slug}.md（单文件）
   □ ≥3 Story → 展开：epic-{N}-{slug}/{epic.md + stories/us{NNN}-{slug}.md}
   说明：预估值仅用于判定结构，Phase 5 会按实际 Story 数自动选择
```

### Phase 2: Epic 识别（Decompose-First 模式）

**核心原则**：先按当前 PRD + Architecture 构建 IDEAL Epic 列表，**不看现有 Epic**。然后再加载现状做对比。

**理由**：防止 anchoring bias —— 旧 Epic 结构可能已经过时，若先看旧结构再"加 Story"，会被锁死在错误的拆分上。

#### Phase 2.1: 构建 IDEAL Epic 列表（不看现状）

**识别逻辑**（按优先级）：
1. PRD §4 "功能需求 (EARS格式)" 已按 Epic 分组 → 直接使用 Epic 标题
2. PRD §11.1 "建议拆解顺序" → 作为辅助参考（MVP 必需 / 顺序 / 理由）
3. PRD §4 无 Epic 分组时 → 从 Architecture 业务模块映射

**命名规范**：使用业务术语（"用户认证" 而非 "JWT实现"），体现用户价值。

**输出**（暂不展示给用户）：IDEAL Epic 列表 `[{epic_id, title, source, priority_hint}]`

#### Phase 2.2: 加载现有 Epic（仅当 has_existing = true）

读取 `docs/tasks/epics/` 下所有 Epic 文件，提取：
- `epic_id`, `title`, `status`, `priority`
- 概述段落（用于 fuzzy match）
- 已有 Story 数 + Story 状态（用于 Phase 2.3 警告判断）

#### Phase 2.3: 输出差异表（仅当 has_existing = true）

按 goal/title fuzzy 匹配 IDEAL vs 现状，分类：

| 操作 | 含义 | 触发条件 |
|------|------|----------|
| **KEEP** | IDEAL + 现状都有，目标不变 | 标题或目标 fuzzy match >0.8，且 In Scope 未变 |
| **UPDATE** | IDEAL + 现状都有，scope 已变 | 标题匹配但 In Scope 或 用户旅程/AC 覆盖 不一致 |
| **OBSOLETE** | 现状有，IDEAL 无 | 现状 Epic 在 IDEAL 列表无匹配 |
| **CREATE** | IDEAL 有，现状无 | IDEAL Epic 在现状无匹配 |

**OBSOLETE 警告规则**：若该 Epic 有 Story 状态为 `in_progress` 或 `Done`，**禁止自动归档**，必须显式提示人工评估。

**展示格式**：见 `references/display-formats.md` §A（差异分组 + 逐项 diff 说明 + confirm/adjust/abandon 选项）。

#### Phase 2.4: 🔴 用户确认（STOP，等用户输入）

- 用户输入 `confirm` → 进入 Phase 2.5 Quality Gate
- 用户输入 `adjust` → 接受用户修订，重新生成差异表
- `has_existing = false` → 跳过 2.2-2.3，直接展示 IDEAL 列表让用户确认

**Stop Condition**：调整循环 ≥3 次 → 强制弹窗"3 次调整未收敛，建议先重审 PRD scope。继续 / 重审 / 放弃？"

### Phase 2.5: Epic Quality Gate（🛑 BLOCKING）

Epic 列表确认后、抽取详细信息前，对**每个** Epic 跑 3 项体检。

| # | 体检项 | PASS 标准 | FAIL 信号 |
|---|--------|-----------|-----------|
| 1 | **Scope clarity** | In/Out 都明确，与其他 Epic 不重叠 | "用户相关的所有功能" / Epic 间含混 / In Scope 与其他 Epic 有 ≥30% 重叠 |
| 2 | **Balance（工作量平衡）** | 每个 Epic 的 PRD §4 Requirements 条数在 `[均值×0.5, 均值×1.5]` 区间 | 一个 Epic 含 ≥20 Requirements、其他 ≤3 |
| 3 | **Independence（Epic 级无循环）** | Epic 间依赖单向 | Epic A 依赖 B，B 又依赖 A |

> 注：可衡量性已下沉到 AC 层（Phase 4 `验证:` 三要素 + 禁模糊词）；风险 / 失败模式由 Phase 2.6 System-Wide 6 维度承载。Epic 文档不再单列 Success Criteria / Risks / Metrics（见重要规则 §23）。

**评分规则**：
- **3/3 通过** → 进入 Phase 2.6
- **2/3 通过** → 显示警告 + 失败项详情，问用户"知悉风险继续 / 调整"
- **<2/3（即 ≤1/3）** → BLOCKING，必须重回 Phase 2.1 重审 scope

**说明**：Balance 项在 Phase 2.5 阶段还没拆 Story，**用 PRD §4 该 Epic 包含的 Requirements 条数当代理指标**。Phase 5.1 写盘前会用真实 Story 数再次验证 balance。

**Stop Condition**：Scope clarity 或 Independence 项失败 + rework ≥2 次 → 弹窗"Epic 划分本身有问题（重叠 / 循环依赖），建议检查是否漏拆共同基础设施 / 边界划错"。

**展示格式**：见 `references/display-formats.md` §B（逐 Epic 三项体检结果 + 失败项问题/建议 + continue/fix/rework 选项）。

---

### Phase 2.6: 信息抽取 + 一次性补全

合并了原 System-Wide 抽取 + 新增的 Auto-Extract + 用户旅程抽取，目的是**对每个 Epic 一次性填齐细节信息**，避免多 phase 反复问询。

#### Step 1: Auto-Extract（per Epic 跑一遍）

对每个 Epic，按以下映射尝试从文档抽取 5 项核心信息：

| 字段 | 主源 | 备源 | 找不到的标记 |
|------|------|------|--------------|
| **业务目标** | PRD §11.1 "理由"列 | PRD §1.3 核心价值（标 ⚠️ 推断） | ❓ |
| **In Scope** | PRD §4 该 Epic 下的 R1/R2/R3... | Architecture 模块职责描述 | ❓ |
| **Out of Scope** | PRD §11.2 "可延后能力" | PRD §9 非目标（标 ⚠️ 全局） | ❓ |
| **用户旅程** | PRD §1.5 核心用户旅程 / PRD §11 关键步骤 | PRD §4 功能需求 + UI 设计稿（标 ⚠️ 推断） | **❓ 必问** |
| **页面体验地图** | PRD 页面描述 / UI 设计稿 / DESIGN.md | 从用户旅程 + PRD §4 推断（标 ⚠️ 推断） | 前端 Epic **❓ 必问** |

> 注：不再抽取「成功标准」与「风险」——epic 级完成判据由 Story AC 承载，失败模式 / 不变量由 Step 3 System-Wide 承载（见重要规则 §23）。

前端 Epic 额外抽取：

| 字段 | 主源 | 备源 | 找不到的标记 |
|------|------|------|--------------|
| **屏型** | DESIGN.md / UI brief / 路由语义 | 从 route 和任务推断：login/landing=front-of-house，dashboard/list/detail/form/settings=operational | ⚠️ 推断 |
| **首屏品牌/任务要求** | UI brief / PRD 页面描述 / DESIGN.md §Richness Floor | 从用户旅程推断 | front-of-house **❓ 必问** |
| **状态覆盖** | PRD 异常流 / 接口状态 / ui-state-coverage | 从 EARS If/While/Where 与数据源推断 | ⚠️ 推断 |
| **参考来源** | docs/reference/research/designs/ / 用户 URL 或截图 | DESIGN.md §Reference Skeletons | ⚠️ 推断 |

前端设计轨道判定：按 `.agents/skills/_shared/ui-planning-contract.md` §2（双轨触发）与 §3（复杂操作流判定）执行，本 skill 不复述规则条目。本 skill 特有机制：命中产品/品牌方向轨缺口时，停止把 UI Story 直接推进实现，把缺口列入 Batch Question，建议先跑产品级 `ui-requirement-brief -> vj-design-md-matcher`。

**重要规则**：
- 标 `⚠️` 的字段表示"从全局推断而来"，**必须在 Batch Question 里让用户确认/修正，不能默认接受**
- 标 `❓` 的字段表示"完全找不到，必须用户提供"
- 标 `✓` 的字段表示"从精确来源抽到，可直接使用"

#### Step 2: 用户旅程抽取与映射（per Epic 跑一遍）

为每个 Epic 生成 `## 用户旅程` section，说明**用户**如何实际使用系统完成业务目标。它是 WHAT 层产物，不写实现方案、不列 API 细节，也不写成 UI 点击脚本。

**抽取来源**（按优先级）：
1. PRD 显式用户旅程（§1.5 核心用户旅程）/ 业务流程 / 场景描述
2. PRD §11 关键步骤 / 建议拆解顺序
3. PRD §4 功能需求的前后依赖与 EARS 条件
4. UI 设计稿中的页面流转 / 状态变化
5. `docs/project/DESIGN.md`（优先）/ `docs/project/design_guidelines.md`（fallback）中的页面密度、组件、状态与视觉约束
6. Architecture / API / Data 仅用于校验系统响应是否可落地，不作为旅程主来源

**输出结构**：
- **Mermaid 概览**：用 `flowchart LR` 画端到端主路径，节点用客户可理解的业务语言，不画 API / 表 / 服务内部调用
- **主旅程**：角色完成核心目标的正常路径，按时间顺序写 `步骤 / 页面或入口 / 用户行为 / 系统响应 / 覆盖 Story或AC`
- **分支与异常旅程**：未登录、无权限、数据为空、重复操作、下游失败、非法输入等路径，写 `场景 / 页面或入口 / 用户行为 / 系统响应 / 覆盖 Story 或 AC`
- **页面体验地图**（仅前端 Epic）：每个页面/区域一行，写页面职责、屏型、主操作、次操作、关键状态、信息优先级、体验护栏、品牌/富度要求、禁止项；这不是设计稿，也不是控件清单

**映射要求**：
- 每个主旅程步骤必须映射到至少 1 个 Story；映射不到 = 缺 Story，回 Phase 3 拆分
- 每个异常旅程必须映射到 Story 的 Edge/Error AC，或拆成独立 Story
- 单个 Story 内的小流程可以在 Story AC 中覆盖；跨 Story 的端到端路径必须落在 Epic 的 `## 用户旅程`
- 涉及前端的旅程步骤必须有页面/入口；没有明确页面时标 `⚠️ 推断` 并在 Batch Question 让用户确认
- 前端 Epic 必须有 `## 页面体验地图`；后端/纯能力 Epic 可省略并说明 N/A
- 页面体验地图完整度 BLOCKING、屏型判定与默认表、front-of-house / operational 必写项与禁止项、状态覆盖口径：按 `.agents/skills/_shared/ui-planning-contract.md` §1/§4/§5 执行（本 skill 不复述条目）。缺字段回对应 `ui-*` skill 或 Batch Question 补齐；屏型不确定时标 `⚠️ 推断` 并在 Batch Question 让用户确认。
- 若旅程由 PRD 推断而来，标 `⚠️ 推断` 并在 Batch Question 让用户确认

#### Step 3: System-Wide 6 维度抽取（保留原设计）

对每个 Epic 跑 6 维度扫描，挖出隐藏 Story：

**自动扫描来源**：
1. Architecture → 此 Epic 跨越的模块边界
2. API Design → 此 Epic 触及端点的其他消费方
3. Data Model → 共享数据 / 外键依赖 / 索引影响
4. 已有 Epic 列表 → 上下游 Epic 的耦合点

**6 个维度**：
- **跨模块影响**: 哪些其他 Epic / 模块 / 服务 / 第三方会被牵动
- **不变量保护**: 哪些现有行为 / 数据约束 / API 行为不能被破坏
- **状态生命周期**: 并发 / 缓存 / 重试 / 清理 / 长事务风险
- **API 表面一致性**: 其他端点 / 界面 / 客户端是否需要同步改
- **错误传播**: 错误如何跨层 / 跨服务传递
- **权限边界**: 涉及的角色 / 资源所有权 / 越权场景

每条 System-Wide 项的处置二选一（epic.md **不落盘** System-Wide section——该产物无下游具名
消费者，且"已下放"断言无检查兜底、已实证漂移，见 epic-1 plan 的 ACD3）：
- **新增 Story** → 候选清单进入 Phase 3 拆分
- **加进现有 Story 的 AC** → 候选清单进入 Phase 4 生成

落不进任何 AC 的条目**显式路由**，禁止静默丢弃：决策/开放问题 → PRD open questions 或
plan 阶段 `decisions.md`；repo 级基线约束（如统一响应信封、`/api/v1` 前缀）→ 不重复记录，
由 AGENTS.md / `docs/project/api/conventions.md` + plan 的 Execution Checklist 承载。
路由去向在 Batch Question 表内标注，供追溯。

#### Step 4: 🔴 Batch Question（STOP，所有 ❓ + ⚠️ 一次问完）

把 Step 1、Step 2 和 Step 3 的结果合并成一张大表，**一次性展示给用户**。
展示格式见 `references/display-formats.md` §C（逐 Epic 列 ✓/⚠️/❓ 五项核心信息 +
用户旅程 + System-Wide 六维度，末尾提供 confirm 快捷确认）。

**判断规则**（System-Wide 项是否变成 Story）：
- 影响项已被现 Epic 的 Story 自然覆盖 → 在 Batch Question 表标注覆盖它的 Story/AC，无落盘动作
- 影响项独立成块、有自己的验收标准 → 拆出新 Story
- 影响项是对现有行为的保护 → 进入对应 Story 的 Edge/Error/Integration AC

**输出**：
- 每个 Epic 的核心信息填齐；前端 Epic 含页面体验地图，后端/纯能力 Epic 明确标 N/A
- 每个 Epic 的 `## 用户旅程` section 完整，且每个步骤有 Story / AC 映射
- 前端 Epic 的 `## 页面体验地图` 完整，且每个页面/区域映射到旅程步骤或 Story
- System-Wide 项产出处置决策
- 可能产生的新 Story 候选清单 → Phase 3
- 可能产生的 AC 增强项 → Phase 4

**Stop Condition**：补全后用户反馈 ≥3 次 → 弹窗"信息缺口大，是否回退到 Phase 2.1 调整 Epic 边界？"

### Phase 3: Story 拆分

**INVEST 原则**：
- **I**ndependent: 独立可交付
- **N**egotiable: 可协商调整
- **V**aluable: 对用户有价值
- **E**stimable: 可估算工作量
- **S**mall: 1-2 Sprint 可完成
- **T**estable: 可测试验证

**拆分来源**：
1. PRD 中的需求条目
2. 用户旅程的关键步骤
3. 技术实现的独立单元（按聚合根或模块）

**用户旅程映射规则**：
- 主旅程每一步都必须有对应 Story；若一个步骤跨越多个可独立交付能力，拆成多个 Story
- 分支与异常旅程优先进入对应 Story 的 Edge/Error AC；若异常路径有独立用户价值或独立状态生命周期，拆成 Story
- Story 列表生成后，回填 `## 用户旅程` 的 `覆盖 Story / AC` 列；禁止保留"待定"
- Story 描述写可交付能力，不写成“点击左侧菜单、选择下拉框第 N 项”的操作脚本；控件细节只进入前端 AC，且必须能用 Browser 验证
- UI Story 必须能追溯到 `## 页面体验地图` 的某个页面/区域；追溯不到说明页面组织缺口，回 Phase 2.6 补齐

每个 Story 拆分后需用户确认粒度。

#### Feature Bundling 拦截（🛑 BLOCKING）

Story 标题禁止用 "**和** / **&** / **+** / **,**" 连接两个独立能力。检测到必须拆成多个 Story。

**自动检查**：写盘前由 `scripts/validate_story.py`（R4）统一机检；拆分阶段先做语义判断。
确为单一原子能力（见下方例外）时在标题行尾加 `<!-- bundling-ok -->` 豁免机检。

**改写示例**：

```
❌ Story 1.3: 用户注册 和 登录
   → 拆为两个独立 Story:
   ✓ Story 1.3: 手机号注册
   ✓ Story 1.4: 手机号登录

❌ Story 2.1: 创建订单 + 发送通知
   → 拆为:
   ✓ Story 2.1: 创建订单
   ✓ Story 2.2: 订单创建后发送通知

❌ Story 3.5: 商品列表、详情页、搜索
   → 拆为三个独立 Story
```

**例外**：标题中的 "和" 用于描述同一原子能力时可保留（如 "用户名和密码登录" 是单一登录流程的输入，不是两个能力）。判断标准：能否单独交付价值。

#### 覆盖空间拆分触发器（第三个拆分信号）

除 Feature Bundling（标题层）和行为 AC 总数 ≤7（条数层）外，还有**覆盖空间层**的拆分信号：

- 当 Phase 4 Step 0 对某 Story 派生出的**等价类 / 状态迁移 / 决策表规则数** > 单 Story 能容纳的 AC（≤7）时 → **拆 Story**（按子能力 / 子流程切），不要在一个 Story 里堆条数，也不要删类别压缩。
- 这是 Phase 4 → Phase 3 的回环：派生发现覆盖空间溢出，回到本 Phase 重新拆分。
- **完整性在 Story 集合层达成，不在单 Story 内堆叠**——多个聚焦的小 Story 比一个塞满 AC 的大 Story 更可测、更可交付。

### Phase 4: 验收标准生成

为每个 Story 生成 **4 分类** checkbox 格式的验收标准，**每条 AC 必须附带验证方式**。

#### 4 分类强制框架

每个 Story 的 AC 按以下 4 类组织。**Happy Path 必须有**；其余类别若不适用可省略，但省略前必须经过覆盖度自检（见下文 BLOCKING 自检表）。

| 类别 | 用途 | 子类型提示（穷举式覆盖检查） |
|------|------|------------------------------|
| **Happy Path** | 核心成功路径 | 主流程、典型输入、期望输出 |
| **Edge Cases** | 边界与非常规输入 | 空输入 / 边界值（最小/最大）/ nil-null / 并发操作 / 重复请求 / 长度极限 |
| **Error Paths** | 失败与防御 | 非法输入 / 下游服务故障 / 网络超时 / 权限拒绝 / 速率限制 / 数据库约束冲突 |
| **Integration** | 跨层 / 跨模块行为（**Story 跨层时必填**） | callback 触发 / middleware 顺序 / 多层数据流 / 事件传播 / 副作用 |

> 上表「子类型提示」列是**派生后的复核清单**（兜底视角），不是"挑 1-2 条凑数"的输入。Edge/Error AC 先经下面 Step 0 按 Story 形态结构化派生，再用该列复核是否漏。

#### Step 0: 按 Story 形态派生 Edge/Error 候选（Derive, don't checklist）

生成 AC 前，先判定本 Story 的形态，套对应黑盒测试设计技术派生 Edge/Error 候选——**让 case 从这个 Story 的真实输入域 / 状态空间来，而不是从通用清单挑**。

| 形态信号 | 派生技术 | 产出候选 |
|----------|----------|----------|
| 有输入字段 | 等价类划分 EP：每字段分有效 / 无效类 | 每个无效类 → 1 条 Error AC |
| 字段是数值 / 长度 / 日期 / 区间 | 边界值分析 BVA：min−1 / min / max / max+1 | 边界 → Edge AC（无序集合 / 布尔 / 枚举不适用 BVA，改用 EP 逐值） |
| ≥2 个条件交叉决定结果 | 决策表：列条件组合 → 每条规则一行 | 每条规则 → 1 条 AC（组合爆炸时用 pairwise，并记录砍了哪些组合） |
| 有状态实体 / 工作流 | 状态迁移：列 状态 × 事件 | 每条合法迁移 + ≥1 条非法迁移 → Edge AC |
| 单 Story 本身是一段用户流程 | 主流程 / 备选流 / 异常流走查（**限本 Story 内**；跨 Story 端到端旅程不在此，归 epic.md + Phase 5.5 旅程完整性） | 备选 / 异常分支 → Edge / Error AC |

**派生后两件事**：
1. 用上面「4 分类」表的子类型提示列**复核**派生结果有没有漏。
2. 派生候选数若超过 AC 上限（≤7）→ 这是**拆 Story 信号**（回 Phase 3 覆盖空间拆分触发器），**不是删类别**。砍掉的低优先级候选（Impact×Probability ≤8）→ 落到 `Assumptions [SCOPE]`，写明失效影响，不静默丢。

**AC 模板格式：**

```markdown
#### 验收标准

**Happy Path**
- [ ] [核心流程条件，含预期结果] `验证: <kind> <target> → <assert>`

**Edge Cases**
- [ ] [空输入处理] `验证: <kind> <target> → <assert>`
- [ ] [边界值] `验证: <kind> <target> → <assert>`
- [ ] [并发 / 重复请求] `验证: <kind> <target> → <assert>`

**Error Paths**
- [ ] [非法输入 → 预期错误码] `验证: <kind> <target> → <assert>`
- [ ] [下游故障 → 预期降级行为] `验证: <kind> <target> → <assert>`
- [ ] [权限拒绝] `验证: <kind> <target> → <assert>`

**Integration**（仅当 Story 跨多个层/模块时）
- [ ] [跨层行为：callback / middleware / 多层数据流] `验证: <kind> <target> → <assert>`

#### 前端验收标准（如有 UI 交互）
- [ ] [元素存在性] `验证: Browser <selector> → exists`
- [ ] [交互行为] `验证: Browser <action> → <assert>`
- [ ] [状态展示：空态/加载/错误] `验证: Browser <condition> → <element state>`
```

#### 覆盖度自检（🛑 BLOCKING — 不通过则不输出 Story）

生成每个 Story 的 AC 后，按以下清单逐项检查；任一适用项缺失则必须补齐：

- [ ] **派生表已应用**：已按 Step 0 判定 Story 形态并套对应技术（EP / BVA / 决策表 / 状态迁移 / 单 Story 流程）派生 Edge/Error，而非从通用清单挑选凑数
- [ ] **Happy Path**：至少 1 条覆盖核心成功路径
- [ ] **Edge Cases**：至少 1 条空输入 + 1 条边界值（除非 Story 显式说明无边界，例如纯静态展示）
- [ ] **Error Paths**：至少 1 条非法输入 + 1 条下游/外部故障（除非纯只读且无外部依赖）
- [ ] **Integration**：跨层 Story 必填；纯单层 Story（仅一个模块内）可省略
- [ ] **前端 AC**：UI 交互 Story 必填；纯后端 API Story 可省略
- [ ] **行为 AC 硬上限**：单个 Story 的业务/行为 AC 总数 ≤ 7（Happy 1-2 + Edge 1-2 + Error 1-2 + Integration 0-2）。`#### 前端验收标准` 单独计数，建议 ≤4 条；若前端 AC 描述的是新增业务行为而非呈现/交互/设计验证，必须回流到行为 AC 或拆 Story
- [ ] **Assumptions section 存在**：每个 Story 必须有 `#### Assumptions` section；无相关假设填"无"，**不能删除整个 section**

输出 Story 前必须显式声明：「覆盖度自检通过：派生 ✓ / Happy ✓ / Edge ✓ / Error ✓ / Integration ✓ / FE ✓ / 行为 AC 总数 N ≤7 ✓ / FE AC M≤4 ✓ / Assumptions [N 条 或 "无"]」，或对省略项注明理由（例："Integration N/A — 纯单层"）。

#### Assumptions 写法（BLOCKING）

每条假设必须满足三要素：

```
[类别] 假设描述 — Confidence: H/M/L — 失效影响: 具体影响描述
```

- **类别**枚举（四选一）：
  - `FEASIBILITY` — 技术/实现可行性假设（例：某算法在数据量 N 下性能可接受）
  - `DEPENDENCY` — 外部依赖假设（例：第三方服务 SLA、库行为）
  - `DATA` — 数据形态假设（例：字段唯一性、空值率、量级）
  - `SCOPE` — 范围假设（例：不处理某场景、某环境不支持）
- **Confidence**：H（高，几乎确定）/ M（中，有依据但未验证）/ L（低，凭直觉）
- **失效影响**：必须具体、可观测，禁止"会有问题"这种模糊描述

**示例**：

```markdown
#### Assumptions
- [DEPENDENCY] 短信网关 99.5% 可用 — Confidence: M — 失效影响: 验证码送达率 <95%，需引入降级到邮件
- [DATA] 单用户每日发送 ≤10 次验证码 — Confidence: L — 失效影响: rate limit 设计偏紧，可能误伤
- [SCOPE] 不支持国际手机号（仅 +86） — Confidence: H — 失效影响: 海外用户无法注册
```

无假设时：

```markdown
#### Assumptions
- 无
```

**AC 可测试性要求（BLOCKING — 不通过则不输出 Story）**：

每条 AC 必须满足：
1. **有明确的预期结果**：状态码、数据值、页面元素、时间阈值等
2. **有可执行的验证方式**：API 调用、DB 查询、pytest 断言、浏览器操作
3. **无模糊用语**：禁止使用"合理"、"正常"、"正确显示"等无法断言的描述

**`验证:` 格式要求（必须包含 3 要素）**：

```
验证: <kind> <target> → <assert>
```

- **kind**: `pytest` / `API` / `DB` / `Browser` 四选一
- **target**: 具体的测试函数、API 路径、SQL 查询或 DOM 操作
- **assert**: 可断言的预期结果（状态码、行数、元素状态、字段值）

| kind | target 示例 | assert 示例 |
|------|------------|------------|
| `pytest` | `test_code_expires_after_5min` | `PASSED` |
| `API` | `POST /auth/register` | `→ 201 + body.token exists` |
| `DB` | `SELECT FROM users WHERE phone=X` | `→ 1 row, is_active=true` |
| `Browser` | `click button[type=submit]` | `→ .toast 出现, textContent="保存成功"` |

**不合格的 `验证:` 示例**（缺少 assert，会被拦截）：
- ❌ `验证: Browser 打开页面` — 没有断言
- ❌ `验证: API 调用接口` — 没有具体路径和预期结果
- ❌ `验证: pytest 跑测试` — 没有具体测试函数名

**模糊 AC 改写示例**：见 `references/display-formats.md` §E。

**标准来源**：
1. PRD 中的需求描述 → 转为可测试条件
2. API Design 中的接口行为 → 状态码、响应格式
3. 非功能性需求 → 性能、安全、可用性
4. **项目设计合同** → 优先 `docs/project/DESIGN.md`；旧路径 `docs/project/design_guidelines.md` 仅作 fallback
5. **页面体验地图** → 页面职责、主/次操作、关键状态、信息优先级、体验护栏
6. **UI workflow skills（按缺口触发）** → 产品/品牌方向缺口用产品级 `ui-requirement-brief -> vj-design-md-matcher`；单屏结构缺口用 `ui-page-goal-structure`；状态缺口用 `ui-state-coverage`；命中复杂操作流判定时用 `ui-user-journey-audit`
7. **设计稿匹配**（自动检查） → 前端交互与 UI 状态

**设计稿自动检查**：
1. 检查 `docs/reference/research/designs/{epic-id}/` 是否存在匹配当前 Epic 的设计稿
2. 如有设计稿 → 提取页面结构、交互流程、状态变化，自动生成「前端验收标准」section
3. 如无设计稿 → 根据页面体验地图 + PRD 中的前端交互描述生成前端 AC；若二者都无前端描述则跳过
4. 在 Story 的 `参考` 行追加设计稿路径：`docs/reference/research/designs/{epic-id}/{文件名}`；如适用也追加 `docs/project/DESIGN.md`

**前端 AC 富度规则**：按 `.agents/skills/_shared/ui-planning-contract.md` §4/§7 执行（front-of-house / operational 的 Browser 验证下限、前端 AC 写法与下游截图验证链路），本 skill 不复述条目。

### Phase 5: 批量预览 + 写盘

#### Phase 5.1: 在内存里组装所有产出（不写盘）

填充模板：将所有 Epic + Story + AC 决策**在内存中**填入 `epic-story.template.md`，组装出完整的文件内容（暂不写到磁盘）。

#### Phase 5.2: 写盘前批量预览（🔴 USER GATE，STOP 等确认）

展示完整产出概览给用户确认。**预览默认折叠 AC 详情**，只显示统计；用户可显式要求展开。

**展示格式**：见 `references/display-formats.md` §D（逐 Epic 概览 + 每 Story 的 AC 分类计数 +
完整性验证清单 + 写盘后改动预告 + confirm/adjust/abandon/expand 选项）。

#### Phase 5.3: 用户确认

- `confirm` → 执行写盘（Phase 5.4）
- `adjust` → 接受用户具体反馈，回到对应 Phase 修订（如改 AC 回 Phase 4，改 Story 拆分回 Phase 3）
- `abandon` → 不写盘，记录到对话上下文供用户复用
- `expand epic-N` → 展开第 N 个 Epic 的所有 Story AC 详情，继续等确认

**Stop Condition**：预览阶段反馈 ≥3 次 → 弹窗"反复调整未收敛，建议保存当前草稿 / 全部放弃"。

#### Phase 5.4: 决定输出结构 + 写盘

按实际 Story 数自动选择结构（不询问用户）：

   | 该 Epic 的 Story 数 | 输出结构 |
   |---------------------|----------|
   | **<3 Story** | 平铺：`docs/tasks/epics/epic-{N}-{slug}.md`（单文件，Story 内嵌） |
   | **≥3 Story** | 展开：`docs/tasks/epics/epic-{N}-{slug}/`（目录） |

   **展开模式的目录结构**：

   ```
   docs/tasks/epics/epic-{N}-{slug}/
   ├── epic.md                        # Epic 主文档（不含 Story 详情，只保留 Story 列表引用）
   └── stories/
       ├── us{NNN}-{slug-1}.md        # 每个 Story 独立文件
       └── us{NNN+1}-{slug-2}.md
   ```

   - `us{NNN}` 是**全局 Story 序号**（跨 Epic 累加），从 `kanban_board.md` 的 `Next Story Number` 读取
   - Story 文件内容 = template 中单个 Story 节（用户故事 + AC + 前端 AC + Assumptions + 覆盖度自检 + 参考 + 依赖）
   - Epic.md 保留 `## 用户旅程`、依赖关系和 Story 列表引用
   - Epic.md 的 "## Story 列表" 只保留指向 stories/ 的链接表，不重复 Story 详情

**同一 Epic 内不允许混用结构**：要么全平铺，要么全展开。增量添加 Story 时若已有 Story 数从 2 增到 3，必须迁移到展开模式（在 Phase 2.3 的 UPDATE 差异里提示用户确认）。

#### Phase 5.5: 完整性验证（写盘前最后一道闸）

注：以下大部分项 Phase 5.2 预览阶段已显示给用户。此处是写盘前最后一次自动校验，发现任意 BLOCKING 项失败则中止写盘并报告。

**第一步（机检，必跑）**：把组装好的内容写入临时文件后执行

```bash
python3 .agents/skills/vj-epic-story/scripts/validate_story.py <临时文件或 epic 目录>
```

机检覆盖 R1 行为 AC ≤7 / R2 `验证:` 三要素 / R3 Assumptions 三要素 / R4 Feature Bundling /
R5 前向依赖，exit 1 则修复后重跑，禁止带 ERROR 写盘。以下人工清单只负责机检覆盖不了的语义项。

   - [ ] 所有 PRD 功能需求都有对应 Story
   - [ ] **EARS 反向追溯**（BLOCKING）：本 Epic 每条 EARS `If-Then`（不期望行为）/ `While`（状态驱动）/ `Where`（环境条件）子句都映射到 ≥1 条 Error/Edge AC（`If` 通常映射 Error，`While`/`Where` 通常映射状态/环境类 Edge；空映射=缺口，补齐或显式标 N/A + 理由）
   - [ ] **旅程完整性**（BLOCKING）：每个 Epic 有 `## 用户旅程` section；主旅程每一步都有对应 Story；分支与异常旅程每一项都有 Story 或 Edge/Error AC 映射（缺步骤=漏 Story/AC，回 Phase 3/4）
   - [ ] **前端体验完整性**（BLOCKING，前端 Epic）：有 `## 页面体验地图`；每个 UI Story 都映射到页面/区域；每个页面/区域字段完整（清单见 `_shared/ui-planning-contract.md` §5）；缺口已用对应 `ui-*` skill 或 Batch Question 补齐；控件细节未写进 Story 主体
   - [ ] Story 遵循 INVEST 原则
   - [ ] 验收标准按 4 分类组织（Happy / Edge / Error / Integration），覆盖度自检通过（含 Step 0 派生）
   - [ ] 行为 AC 总数 ≤7（见 Phase 4）；FE AC 单独计数且未承载新增业务行为
   - [ ] Story 标题无 Feature Bundling（见 Phase 3）
   - [ ] 每个 Story 有 `#### Assumptions` section（"无" 也算）
   - [ ] 每个 Epic 有 `## 用户旅程` section，且无空映射 / "待定" 映射
   - [ ] System-Wide 扫查每条结论已落 Story AC，或已显式路由（PRD open questions / plan decisions.md / repo 基线），Batch Question 表可追溯；epic.md 无 `## System-Wide Considerations` section
   - [ ] Story ID 编号正确（Epic 内序号 X.Y + 全局 US{NNN}）

#### Phase 5.6: 无前向依赖校验（🛑 BLOCKING）

Story X.N 的"依赖"字段只能引用：
- 同 Epic 内序号更小的 Story（X.M，M < N）
- 更小序号 Epic 的任意 Story（例：Epic 2 的 Story 可依赖 Epic 1 的 Story）

**禁止**：依赖同 Epic 内序号更大的 Story、依赖未来 Epic、循环依赖。

**自动检查**：由 `scripts/validate_story.py`（R5）覆盖，Phase 5.5 机检已包含，不单独跑。

发现前向依赖 → **停止写盘**，向用户报告冲突，提示两种解决方式：(a) 调整 Story 顺序使依赖方向正确；(b) 合并两个 Story（如果实际无法解耦）。

#### Phase 5.7: 写盘 + 处理 REPLAN 操作

按 Phase 2.3 的差异表执行：
- **CREATE** → 新建 Epic 文件 / Story 文件
- **UPDATE** → 改写已有 Epic 文件（保留原 Story 状态字段，仅改 Scope/Criteria）
- **OBSOLETE** → 在 Epic frontmatter 把 `status` 改为 `archived`，**不删除文件**
- **KEEP** → 跳过，不动磁盘

#### Phase 5.8: 回写 kanban_board.md（生成成功后）

- 更新 Tracker Configuration：`Next Epic Number` 和 `Next Story Number` 按本次新增数量递增
- 在 Epic Story Counters 表追加/更新本次 Epic 行（标题、状态 `draft`、优先级、Story 数、路径）
- OBSOLETE 的 Epic 在 Epics Overview 移至 Archived 段（不从 Counters 表删除，保留历史）
- 在 Story Index 表追加所有新建 Story 行（状态默认 `Backlog`，vj-work 完成对应 task 时改为 `Done`）
- 更新文件顶部 `**最后更新**: {{DATE}}`

#### Phase 5.9: 生成人读 HTML 视图

按 Phase 5.4 实际选择的输出结构，**只跑对应的一条**（另一条的路径不存在，跑了会报错）：

```bash
python3 .agents/skills/_shared/scripts/render_doc_html.py docs/tasks/epics/epic-{N}-{slug}.md   # 平铺模式
python3 .agents/skills/_shared/scripts/render_doc_html.py docs/tasks/epics/epic-{N}-{slug}/    # 展开模式（目录递归）
```

md/html 分工与派生视图约定按脚本头注释执行，本 skill 不复述。渲染失败不阻塞流程，报告即可。

**archify 旅程图（可选精装修）**：epic 目录若存在 `journey.html`（源 `journey.workflow.json`，
摘要 sidecar `journey.source-digest`；机制见脚本 `journey_embed` docstring），HTML 视图的主旅程
会 iframe 引用它。本次生成/UPDATE 改动了 `## 用户旅程` 章节且渲染输出 stale warning 时**必须同步**：
改 `journey.workflow.json` → 用全局 `archify` skill 重渲 `journey.html` → 把 warning 打印的
新摘要写入 `journey.source-digest`；环境缺 archify 无法重渲时，把 warning 原样上报用户，
不得静默留过期图。新 epic 不强制配图——没有 `journey.html` 时主旅程自动渲染为泳道板，零额外动作。

---

## Story 格式（~25 行）

```markdown
### Story X.Y: [标题]

**用户故事**: 作为 [角色]，我可以 [功能]，以便 [价值]

#### 验收标准

**Happy Path**
- [ ] [核心流程条件] `验证: <kind> <target> → <assert>`

**Edge Cases**
- [ ] [空输入 / 边界值 / nil-null / 并发] `验证: <kind> <target> → <assert>`

**Error Paths**
- [ ] [非法输入 / 下游故障 / 超时 / 权限拒绝] `验证: <kind> <target> → <assert>`

**Integration**（仅当跨层时）
- [ ] [callback / middleware / 多层数据流] `验证: <kind> <target> → <assert>`

#### 前端验收标准
<!-- 仅当 Story 涉及 UI 交互时包含；纯后端 Story 删除此 section -->
- [ ] [页面元素存在性] `验证: Browser <selector> → exists`
- [ ] [交互行为] `验证: Browser <action> → <assert>`
- [ ] [状态展示] `验证: Browser <condition> → <element state>`
- [ ] [设计稿对齐（如有）] `验证: Browser 截图比对 docs/reference/research/designs/{epic-id}/{文件名}`

#### Assumptions
<!-- 无相关假设填"无"，不能删除整个 section。每条必须三要素：[类别] 描述 — Confidence: H/M/L — 失效影响 -->
- [DEPENDENCY/DATA/FEASIBILITY/SCOPE] [假设描述] — Confidence: H/M/L — 失效影响: [具体描述]

**覆盖度自检**: 派生 ✓ / Happy ✓ / Edge ✓ / Error ✓ / Integration [✓ 或 N/A — 理由] / FE [✓ 或 N/A] / 行为 AC 总数 [N] ≤7 ✓ / FE AC [M]≤4 ✓ / Assumptions [N 条 或 "无"]
**参考**: docs/project/api/{module}.md §X, docs/project/data/{module}.md §Y, docs/reference/research/designs/{epic-id}/{文件名}（如适用）
**依赖**: Story X.Z（必须 Z<当前序号，禁止前向依赖） / 无
```

---

## Epic 格式

参见 `epic-story.template.md`。核心要素：
- Frontmatter: epic_id, epic_name, status, priority, owner, source_documents
- 概述: 背景 + 价值 + 范围 + 不含
- 用户旅程: 主旅程 + 分支/异常旅程，每一步映射 Story/AC
- 页面体验地图: 前端 Epic 必填，页面职责 + 主/次操作 + 关键状态 + 信息优先级 + 体验护栏
- Story 列表: 每个 Story ~25 行
- 依赖关系: Mermaid 图
- 参考文档链接

**不写**：`Success Criteria` / `Risks and Mitigations` / `Metrics` / `System-Wide Considerations` 四个 section——epic 级完成判据由 Story AC 承载；跨界约束 / 失败模式经 Phase 2.6 System-Wide 扫查直接落 Story AC 或显式路由（见重要规则 §23）。

---

## 重要规则

1. **不替用户做决策**：Epic 划分、Story 拆分、优先级排序都需用户确认
2. **不跳过确认**：每个重大决策需用户明确确认
3. **遵循上游约束**：Architecture、API Design、Data Model 中的决策是硬约束
4. **Story 粒度控制**：不太细（变成 Task）也不太粗（超过 2 Sprint）
5. **轻量原则**：Story 只写 What（验收标准），不写 How（实施方案属于 Plan 阶段）
6. **Decompose-First**：先按当前 PRD 构建 IDEAL Epic 列表，再对比现状输出差异（见 Phase 2），禁止先看已有 Epic 再决定怎么拆
7. **用户旅程必须显式输出**：每个 Epic 必须有 `## 用户旅程`，以用户视角描述端到端路径；主旅程映射 Story，分支/异常旅程映射 Story 或 Edge/Error AC；它属于 WHAT 层，`vj-epic-plan` 只能引用，不重新生成
8. **页面体验地图前端必填**：前端 Epic 必须有 `## 页面体验地图`，把页面职责、屏型、主/次操作、关键状态、信息优先级、体验护栏、品牌/富度要求和禁止项传给 `vj-epic-plan`；后端 Epic 可标 N/A
9. **DESIGN.md 是设计合同**：前端相关输出优先引用 `docs/project/DESIGN.md`；`docs/project/design_guidelines.md` 只做旧路径 fallback；两者都存在时以 `DESIGN.md` 为准。前端 Epic 缺 `DESIGN.md` 时不得假装已有设计合同，必须在 Batch Question 里标为待补设计合同或使用最小 DESIGN.md 草案待审批。
10. **UI workflow skills 按缺口强制触发**：按 `.agents/skills/_shared/ui-planning-contract.md` §2/§3 执行；产物进入页面体验地图和前端 AC，不生成外部 v0/Lovable 提示词作为必经步骤。
11. **Story 不是点击脚本**：Story 主体写可交付能力；按钮、下拉框、左侧菜单等控件细节只写进前端 AC，且必须有 Browser 断言
12. **Feature Bundling 禁止**：Story 标题禁止用 "和 / & / + / ," 连接两个独立能力（见 Phase 3）
13. **行为 AC 总数硬上限 ≤7**：超过必须拆 Story，不允许通过删类别压缩；前端 AC 单独计数，若承载新增业务行为则回流到行为 AC 或拆 Story（见 Phase 4）
14. **Assumptions section 必须存在**：每个 Story 必填，无假设填"无"，不能删 section
15. **无前向依赖**：Story X.N 只能依赖 X.M (M<N) 或更小序号 Epic 的 Story（见 Phase 5.6）
16. **kanban_board.md 是编号唯一源**：Next Epic Number / Next Story Number 不重用废弃编号
17. **Epic Quality Gate 是 BLOCKING**：3 项体检 <2/3 通过必须重审 scope，不允许跳过（见 Phase 2.5）
18. **OBSOLETE 不删文件**：REPLAN 模式归档的 Epic 只改 frontmatter `status: archived`，保留历史记录
19. **Stop Conditions（防止死循环）**：
    - 任一用户确认 gate（Phase 2.4 / 2.5 / 2.6 / 5.3）反馈 ≥3 次 → 强制弹窗"继续 / 重审上游 / 放弃"
    - Epic Quality Gate <2/3 + rework ≥2 次 → 升级到"scope 本身有问题"，建议重审 PRD
    - 理由：拉锯到第 3 次还在调，几乎一定是 PRD 或 Architecture 有歧义，不是 epic-story 这一层能解决的
20. **Derive, don't checklist**：Edge/Error AC 来自 Phase 4 Step 0 的结构化派生（EP / BVA / 决策表 / 状态迁移 / 单 Story 流程），不从通用清单挑选凑数（见 Phase 4）
21. **完整性靠拆分而非堆叠**：派生覆盖空间超 AC 上限（≤7）→ 拆 Story（见 Phase 3 覆盖空间拆分触发器）；砍掉的低优先级 case 进 `Assumptions [SCOPE]`，不静默丢
22. **无人值守模式**：作为 subagent 运行或用户不可达时，用户确认 gate（Phase 2.4 / 2.6 Step 4 / 5.3）不阻塞——采用 IDEAL/推断结果继续，所有 ⚠️/❓ 项记为"假设待审批 + Confidence: H/M/L"，写盘产物在 Epic frontmatter 标 `status: draft-unattended` 供人后补确认。**例外**：Phase 2.5 Quality Gate（<2/3）与 Phase 5.5 机检 ERROR 是质量闸不是提问，无人值守下仍硬停并输出报告。绝不静默拍板、绝不静默跳过（口径同 `_shared/vj-skill-conventions.md`）
23. **精简 Epic 文档（无仪式）**：Epic 不含 `Success Criteria` / `Risks and Mitigations` / `Metrics` 三个 section。第一性原理（面向 AI coding）：AI 实现者只消费「可测 AC」+「它本地上下文看不到的跨界约束」；epic 级百分比 / 风险表 / 指标对 AI 写代码零增量。epic 级完成判据 = 该 Epic 所有 Story AC 通过；跨界约束 / 不变量 / 失败模式（含设计硬规则如 default-deny、记录强制带身份）经 Phase 2.6 System-Wide 扫查**直接落为对应 Story 的 Integration/Error AC**，落不进 AC 的显式路由到 PRD open questions / plan `decisions.md` / repo 基线。epic.md 不落盘 System-Wide section——扫查是过程，AC 是产物；留一份"已下放"清单而无检查兜底必然漂移（epic-1 实证：ACD3 发现"已下放 Story 1.4"为假）。

---

## 与其他 Skill 的协作

**工作流位置**：在 vj-product-requirements / vj-architecture 之后、vj-epic-plan 之前；完整链条见 `docs/reference/guides/ai-workflow.md` §1。

- **输入来源**: vj-product-requirements, vj-architecture（api-design / data-model 契约存在时按需读取）
- **输出去向**: vj-epic-plan 生成 HOW + task 文档；vj-work 执行实现

---

## 配置项

```yaml
epic_story_generator:
  output_dir: docs/tasks/epics/
  kanban_board: docs/tasks/kanban_board.md       # 编号 + 状态唯一源
  flat_threshold: 3                              # Story 数 <3 平铺，≥3 展开为目录
  flat_format: "epic-{N}-{slug}.md"
  expanded_format: "epic-{N}-{slug}/"
  story_filename_format: "us{NNN}-{slug}.md"     # 仅展开模式使用
  ac_max_per_story: 7                            # 行为 AC 总数硬上限；FE AC 单独计数
  fe_ac_max_per_story: 4                         # 前端呈现/交互/设计验证 AC 建议上限
  dependency_tracking: true
  forbid_forward_dependency: true                # Story X.N 只能依赖 X.M (M<N)
```
