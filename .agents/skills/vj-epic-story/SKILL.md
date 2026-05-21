---
name: vj-epic-story
description: Use when PRD and Architecture already exist and need to be decomposed into implementation-ready Epic/Story files with acceptance criteria.
---

# Epic & Story 规划

## 核心目标

通过结构化对话，将需求文档转化为可执行的 Epic + Story。输出轻量、聚焦验收标准，直接指导 `do-story` 实施。

**你的角色**：产品策略和技术规格协调者，与用户平等协作。

---

## 工作流程（8 Phase）

| Phase | 职责 |
|-------|------|
| 1 | 初始化（加载模板 / 配置 / 检测已有，**不询问**） |
| 2 | Epic 识别（**Decompose-First**：IDEAL → 对比现状 → 差异表） |
| 2.5 | **Epic Quality Gate**（5 项体检，BLOCKING） |
| 2.6 | **Auto-Extract + Batch Question**（一次问完所有缺口 + System-Wide 6 维度） |
| 3 | Story 拆分（INVEST + Feature Bundling 拦截） |
| 4 | AC 生成（4 分类 + `验证:` 三要素 + 覆盖度自检） |
| 5 | **Batch Preview + 写盘**（写盘前批量预览 → 用户确认 → 完整性验证 → 写盘 → kanban 回写） |

### Phase 1: 初始化

1. **加载模板**：读取 `epic-story.template.md` 理解输出结构
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
   - **推荐**: `docs/project/api_spec.md` → 接口定义
   - **推荐**: `docs/project/database_schema.md` → 数据结构
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
| **UPDATE** | IDEAL + 现状都有，scope/criteria 已变 | 标题匹配但 In Scope 或 Success Criteria 不一致 |
| **OBSOLETE** | 现状有，IDEAL 无 | 现状 Epic 在 IDEAL 列表无匹配 |
| **CREATE** | IDEAL 有，现状无 | IDEAL Epic 在现状无匹配 |

**OBSOLETE 警告规则**：若该 Epic 有 Story 状态为 `in_progress` 或 `Done`，**禁止自动归档**，必须显式提示人工评估。

**展示格式**：

```
📋 Epic 差异分析

✅ KEEP (N 个): 无变化
- Epic 1: 用户管理
- Epic 2: 商品目录

🔧 UPDATE (M 个): 范围/标准已变
- Epic 3: 订单
  diff: 新增"退款流程"（来源 PRD R12-R14），原"售后客服"已移至 Epic 5

❌ OBSOLETE (K 个): 不再在当前需求范围内
- Epic 4: 短信验证码 → 建议归档（已被第三方 SDK 替代）
  ⚠️ 该 Epic 有 2 个 Story 状态为 in_progress，归档需人工评估

➕ CREATE (L 个): 新增
- Epic 6: 数据分析（来源 PRD R15-R18，新需求）

请审核差异：输入 confirm 接受 / 输入 adjust 调整 / 输入 abandon 放弃
```

#### Phase 2.4: 用户确认

- 用户输入 `confirm` → 进入 Phase 2.5 Quality Gate
- 用户输入 `adjust` → 接受用户修订，重新生成差异表
- `has_existing = false` → 跳过 2.2-2.3，直接展示 IDEAL 列表让用户确认

**Stop Condition**：调整循环 ≥3 次 → 强制弹窗"3 次调整未收敛，建议先重审 PRD scope。继续 / 重审 / 放弃？"

### Phase 2.5: Epic Quality Gate（BLOCKING）

Epic 列表确认后、抽取详细信息前，对**每个** Epic 跑 5 项体检。

| # | 体检项 | PASS 标准 | FAIL 信号 |
|---|--------|-----------|-----------|
| 1 | **Scope clarity** | In/Out 都明确，与其他 Epic 不重叠 | "用户相关的所有功能" / Epic 间含混 / In Scope 与其他 Epic 有 ≥30% 重叠 |
| 2 | **Success criteria 可衡量** | 含数字或可断言状态（"<200ms"、">98%"） | 模糊词："快"、"稳"、"好用"、"流畅" |
| 3 | **Risk 已识别** | 至少 1 条具体风险，或显式标注"无重大风险" | section 空白 / 内容为占位符 |
| 4 | **Balance（工作量平衡）** | 每个 Epic 的 PRD §4 Requirements 条数在 `[均值×0.5, 均值×1.5]` 区间 | 一个 Epic 含 ≥20 Requirements、其他 ≤3 |
| 5 | **Independence（Epic 级无循环）** | Epic 间依赖单向 | Epic A 依赖 B，B 又依赖 A |

**评分规则**：
- **5/5 通过** → 进入 Phase 2.6
- **3-4/5 通过** → 显示警告 + 失败项详情，问用户"知悉风险继续 / 调整"
- **<3/5** → BLOCKING，必须重回 Phase 2.1 重审 scope

**说明**：第 4 项在 Phase 2.5 阶段还没拆 Story，**用 PRD §4 该 Epic 包含的 Requirements 条数当代理指标**。Phase 5.1 写盘前会用真实 Story 数再次验证 balance。

**Stop Condition**：第 1 或第 5 项失败 + rework ≥2 次 → 弹窗"Epic 划分本身有问题（重叠 / 循环依赖），建议检查是否漏拆共同基础设施 / 边界划错"。

**展示格式**：

```
📋 Epic Quality Gate 体检结果

Epic 1: 用户管理
  ✓ Scope clarity
  ✓ Success criteria 可衡量
  ✓ Risk 已识别
  ✓ Balance (5 Requirements，均值 6)
  ✓ Independence
  得分: 5/5 PASS

Epic 2: 商品目录
  ✓ Scope clarity
  ⚠️ Success criteria 不可衡量
     问题: "列表加载流畅" 没有数字
     建议: 改为 "列表加载 <500ms (p95)"
  ✓ Risk 已识别
  ✓ Balance
  ✓ Independence
  得分: 4/5 WARNING

Epic 3: ...

总分: 19/25 (2 个 Epic 有警告)
输入 continue 接受警告 / 输入 fix 修订 / 输入 rework 回到 Phase 2.1
```

---

### Phase 2.6: 信息抽取 + 一次性补全

合并了原 System-Wide 抽取 + 新增的 Auto-Extract，目的是**对每个 Epic 一次性填齐细节信息**，避免多 phase 反复问询。

#### Step 1: Auto-Extract（per Epic 跑一遍）

对每个 Epic，按以下映射尝试从文档抽取 5 项核心信息：

| 字段 | 主源 | 备源 | 找不到的标记 |
|------|------|------|--------------|
| **业务目标** | PRD §11.1 "理由"列 | PRD §1.3 核心价值（标 ⚠️ 推断） | ❓ |
| **In Scope** | PRD §4 该 Epic 下的 R1/R2/R3... | Architecture 模块职责描述 | ❓ |
| **Out of Scope** | PRD §11.2 "可延后能力" | PRD §9 非目标（标 ⚠️ 全局） | ❓ |
| **成功标准** | （PRD 当前无 per-Epic 字段） | PRD §1.4 + §5（标 ⚠️ 全局，必问确认） | **❓ 必问** |
| **风险** | PRD §11.3 "验收风险" + Architecture 约束 | PRD §10.2 外部依赖 | ❓ |

**重要规则**：
- 标 `⚠️` 的字段表示"从全局推断而来"，**必须在 Batch Question 里让用户确认/修正，不能默认接受**
- 标 `❓` 的字段表示"完全找不到，必须用户提供"
- 标 `✓` 的字段表示"从精确来源抽到，可直接使用"

#### Step 2: System-Wide 6 维度抽取（保留原设计）

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

每条 System-Wide 项的处置三选一：
- **新增 Story** → 候选清单进入 Phase 3 拆分
- **加进现有 Story 的 AC** → 候选清单进入 Phase 4 生成
- **仅记录在 Epic 文档** → 写入 Epic 的 `## System-Wide Considerations` section

#### Step 3: Batch Question（所有 ❓ + ⚠️ 一次问完）

把 Step 1 和 Step 2 的结果合并成一张大表，**一次性展示给用户**：

```
📋 Epic 详情自动填充结果（请一次性补齐 ❓ 和确认 ⚠️）

═══════════════════════════════════════
Epic 1: 用户管理
═══════════════════════════════════════
  ✓ 业务目标: 让新用户能注册登录找回密码（来源: PRD §11.1）
  ✓ In Scope: 手机号注册、手机号登录、密码重置（PRD R1-R5）
  ⚠️ Out of Scope: 第三方登录（推断自 PRD §9 "未来版本"，请确认）
  ❓ 成功标准: PRD 没有 per-Epic 标准，请提供
     提示: 注册成功率？登录响应时间？密码重置完成率？
  ✓ 风险: 短信网关 SLA 不达标（PRD §11.3）

  System-Wide:
  ✓ 跨模块影响: 牵动 Epic 3 订单（需要 user_id）→ 建议 Epic 1 先交付
  ✓ 不变量保护: 用户名唯一性约束 → 加入 Story 1.1 的 Edge AC
  ❓ 状态生命周期: session 过期策略未知，请确认（24h / 7d / 配置化？）
  ✓ API 表面一致性: /api/users 已存在，新增字段需 minor 版本号
  ⚠️ 错误传播: 短信失败时降级到邮件（推断，请确认）
  ✓ 权限边界: 仅限本人修改个人资料

═══════════════════════════════════════
Epic 2: 商品目录
═══════════════════════════════════════
  ...

请按 Epic 编号逐项补齐 ❓ 和回应 ⚠️，或直接输入 confirm 接受所有 ⚠️
```

**判断规则**（System-Wide 项是否变成 Story）：
- 影响项已被现 Epic 的 Story 自然覆盖 → 仅作为 Epic 文档记录
- 影响项独立成块、有自己的验收标准 → 拆出新 Story
- 影响项是对现有行为的保护 → 进入对应 Story 的 Edge/Error/Integration AC

**输出**：
- 每个 Epic 的 5 项核心信息填齐
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

每个 Story 拆分后需用户确认粒度。

#### Feature Bundling 拦截（BLOCKING）

Story 标题禁止用 "**和** / **&** / **+** / **,**" 连接两个独立能力。检测到必须拆成多个 Story。

**自动检查**：用 grep 在拆分输出上跑：

```bash
grep -nE "^### Story.*(和| 和 |&|\+|,)" <生成的 epic md>
```

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

#### 覆盖度自检（BLOCKING — 不通过则不输出 Story）

生成每个 Story 的 AC 后，按以下清单逐项检查；任一适用项缺失则必须补齐：

- [ ] **Happy Path**：至少 1 条覆盖核心成功路径
- [ ] **Edge Cases**：至少 1 条空输入 + 1 条边界值（除非 Story 显式说明无边界，例如纯静态展示）
- [ ] **Error Paths**：至少 1 条非法输入 + 1 条下游/外部故障（除非纯只读且无外部依赖）
- [ ] **Integration**：跨层 Story 必填；纯单层 Story（仅一个模块内）可省略
- [ ] **前端 AC**：UI 交互 Story 必填；纯后端 API Story 可省略
- [ ] **AC 总数硬上限**：单个 Story AC 总数 ≤ 7（Happy 1-2 + Edge 1-2 + Error 1-2 + Integration 0-2）。超过必须拆 Story，**不允许**通过删减必要类别来压缩条数
- [ ] **Assumptions section 存在**：每个 Story 必须有 `#### Assumptions` section；无相关假设填"无"，**不能删除整个 section**

输出 Story 前必须显式声明：「覆盖度自检通过：Happy ✓ / Edge ✓ / Error ✓ / Integration ✓ / FE ✓ / AC 总数 N ≤7 ✓ / Assumptions [N 条 或 "无"]」，或对省略项注明理由（例："Integration N/A — 纯单层"）。

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

**模糊 AC 改写示例**：

```markdown
# ❌ 模糊（不可测试）
- [ ] 系统发送 6 位数字验证码短信

# ✅ 可测试
- [ ] 调用发送验证码 API 后，verification_codes 表新增一条记录，
      code 为 6 位数字，expired_at = now + 5min
      `验证: API POST /auth/send-code → 200; DB SELECT FROM verification_codes → code LIKE '[0-9]{6}'`

# ❌ 模糊
- [ ] 注册页面包含 App Logo 和标题

# ✅ 可测试
- [ ] 注册页面顶部显示 App Logo（img[alt="logo"]），下方 h1 文案为"食光记"
      `验证: Browser 访问 /register → img[alt="logo"] 存在 + h1.textContent === "食光记"`
```

**标准来源**：
1. PRD 中的需求描述 → 转为可测试条件
2. API Design 中的接口行为 → 状态码、响应格式
3. 非功能性需求 → 性能、安全、可用性
4. **设计稿匹配**（自动检查） → 前端交互与 UI 状态

**设计稿自动检查**：
1. 检查 `docs/reference/research/designs/{epic-id}/` 是否存在匹配当前 Epic 的设计稿
2. 如有设计稿 → 提取页面结构、交互流程、状态变化，自动生成「前端验收标准」section
3. 如无设计稿 → 根据 PRD 中的前端交互描述生成前端 AC；若 PRD 也无前端描述则跳过
4. 在 Story 的 `参考` 行追加设计稿路径：`docs/reference/research/designs/{epic-id}/{文件名}`

### Phase 5: 批量预览 + 写盘

#### Phase 5.1: 在内存里组装所有产出（不写盘）

填充模板：将所有 Epic + Story + AC 决策**在内存中**填入 `epic-story.template.md`，组装出完整的文件内容（暂不写到磁盘）。

#### Phase 5.2: 写盘前批量预览（USER GATE）

展示完整产出概览给用户确认。**预览默认折叠 AC 详情**，只显示统计；用户可显式要求展开。

**展示格式**：

```
📋 完整产出预览（共 N 个 Epic, M 个 Story）

═══════════════════════════════════════
Epic 1: 用户管理 (P0, 5 Story, 平铺模式)
═══════════════════════════════════════
[Epic 概述]: 让新用户能注册登录找回密码
[Success Criteria]: 注册成功率 >95%, 登录响应 <500ms (p95), 密码重置完成率 >90%
[System-Wide]: 已识别 6 项（4 进 AC，2 进 Epic 文档）

Story 1.1: 手机号注册 (US001)
  Happy: 1 | Edge: 2 | Error: 2 | Integration: 0 | FE: 2 | Assumptions: 1
Story 1.2: 手机号登录 (US002)
  Happy: 1 | Edge: 1 | Error: 2 | Integration: 0 | FE: 2 | Assumptions: 0
Story 1.3: 密码重置 (US003)
  ...

═══════════════════════════════════════
Epic 2: 商品目录 (P0, 4 Story, 展开模式)
═══════════════════════════════════════
...

───────────────────────────────────────
完整性验证（先于写盘）:
  ✅ 所有 PRD 需求都有 Story 映射
  ✅ INVEST 检查通过
  ✅ 无 Feature Bundling（grep "和|&|+|," 无命中）
  ✅ 无前向依赖
  ✅ 所有 Story AC 总数 ≤7
  ✅ 所有 Story 有 Assumptions section
  ✅ Quality Gate Balance 复检：Story 数 [5,4,6,3,5]，方差正常
  ⚠️ 警告: Epic 3 的 Success Criteria 只有 2 条（P0 建议 ≥3）

写盘后改动:
  - 新建 6 个 Epic 文件 (epic-1 平铺, epic-2~6 展开)
  - 新建 25 个 Story 文件
  - kanban_board.md: Next Epic 11 → 17, Next Story 1 → 26

输入 confirm 写盘 / 输入 adjust 修订 / 输入 abandon 放弃
输入 expand epic-N 展开第 N 个 Epic 的完整 AC 详情
```

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
   - Epic.md 的 "## Story 列表" 只保留指向 stories/ 的链接表，不重复 Story 详情

**同一 Epic 内不允许混用结构**：要么全平铺，要么全展开。增量添加 Story 时若已有 Story 数从 2 增到 3，必须迁移到展开模式（在 Phase 2.3 的 UPDATE 差异里提示用户确认）。

#### Phase 5.5: 完整性验证（写盘前最后一道闸）

注：以下大部分项 Phase 5.2 预览阶段已显示给用户。此处是写盘前最后一次自动校验，发现任意 BLOCKING 项失败则中止写盘并报告。

   - [ ] 所有 PRD 功能需求都有对应 Story
   - [ ] Story 遵循 INVEST 原则
   - [ ] 验收标准按 4 分类组织（Happy / Edge / Error / Integration），覆盖度自检通过
   - [ ] AC 总数 ≤7（见 Phase 4）
   - [ ] Story 标题无 Feature Bundling（见 Phase 3）
   - [ ] 每个 Story 有 `#### Assumptions` section（"无" 也算）
   - [ ] 每个 Epic 有 System-Wide Considerations section
   - [ ] Epic 有 Success Criteria（P0/P1 至少 3 条，P2/P3 至少 1 条）
   - [ ] Story ID 编号正确（Epic 内序号 X.Y + 全局 US{NNN}）

#### Phase 5.6: 无前向依赖校验（BLOCKING）

Story X.N 的"依赖"字段只能引用：
- 同 Epic 内序号更小的 Story（X.M，M < N）
- 更小序号 Epic 的任意 Story（例：Epic 2 的 Story 可依赖 Epic 1 的 Story）

**禁止**：依赖同 Epic 内序号更大的 Story、依赖未来 Epic、循环依赖。

**自动检查**：

```bash
# 提取所有依赖声明，校验编号方向
grep -nE "^\*\*依赖\*\*:" <生成文件> | while read line; do
  # 解析当前 Story 序号和依赖目标，若依赖 > 当前 → 报错
done
```

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
- 在 Story Index 表追加所有新建 Story 行（状态默认 `Backlog`，do-story 完成时改为 `Done`）
- 更新文件顶部 `**最后更新**: {{DATE}}`

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

**覆盖度自检**: Happy ✓ / Edge ✓ / Error ✓ / Integration [✓ 或 N/A — 理由] / FE [✓ 或 N/A] / AC 总数 [N] ≤7 ✓ / Assumptions [N 条 或 "无"]
**参考**: docs/project/api_spec.md §X, docs/project/database_schema.md §Y, docs/reference/research/designs/{epic-id}/{文件名}（如适用）
**依赖**: Story X.Z（必须 Z<当前序号，禁止前向依赖） / 无
```

---

## Epic 格式

参见 `epic-story.template.md`。核心要素：
- Frontmatter: epic_id, epic_name, status, priority, owner, source_documents
- 概述: 背景 + 价值 + 范围
- Story 列表: 每个 Story ~15 行
- 依赖关系: Mermaid 图
- 参考文档链接

---

## 重要规则

1. **不替用户做决策**：Epic 划分、Story 拆分、优先级排序都需用户确认
2. **不跳过确认**：每个重大决策需用户明确确认
3. **遵循上游约束**：Architecture、API Design、Data Model 中的决策是硬约束
4. **Story 粒度控制**：不太细（变成 Task）也不太粗（超过 2 Sprint）
5. **轻量原则**：Story 只写 What（验收标准），不写 How（实施方案属于 Plan 阶段）
6. **Decompose-First**：先按当前 PRD 构建 IDEAL Epic 列表，再对比现状输出差异（见 Phase 2），禁止先看已有 Epic 再决定怎么拆
7. **Feature Bundling 禁止**：Story 标题禁止用 "和 / & / + / ," 连接两个独立能力（见 Phase 3）
8. **AC 总数硬上限 ≤7**：超过必须拆 Story，不允许通过删类别压缩（见 Phase 4）
9. **Assumptions section 必须存在**：每个 Story 必填，无假设填"无"，不能删 section
10. **无前向依赖**：Story X.N 只能依赖 X.M (M<N) 或更小序号 Epic 的 Story（见 Phase 5.6）
11. **kanban_board.md 是编号唯一源**：Next Epic Number / Next Story Number 不重用废弃编号
12. **Epic Quality Gate 是 BLOCKING**：5 项体检 <3/5 通过必须重审 scope，不允许跳过（见 Phase 2.5）
13. **OBSOLETE 不删文件**：REPLAN 模式归档的 Epic 只改 frontmatter `status: archived`，保留历史记录
14. **Stop Conditions（防止死循环）**：
    - 任一用户确认 gate（Phase 2.4 / 2.5 / 2.6 / 5.3）反馈 ≥3 次 → 强制弹窗"继续 / 重审上游 / 放弃"
    - Epic Quality Gate <3/5 + rework ≥2 次 → 升级到"scope 本身有问题"，建议重审 PRD
    - 理由：拉锯到第 3 次还在调，几乎一定是 PRD 或 Architecture 有歧义，不是 epic-story 这一层能解决的

---

## 与其他 Skill 的协作

```
vj-product-requirements → vj-architecture → api-design → data-model
                                                           ↓
                                       vj-epic-story
                                                           ↓
                                         "实现 Story X.Y" → Plan → do-story
```

- **输入来源**: vj-product-requirements, vj-architecture, api-design, data-model
- **输出去向**: Plan mode → do-story 执行实现

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
  ac_max_per_story: 7                            # AC 总数硬上限
  dependency_tracking: true
  forbid_forward_dependency: true                # Story X.N 只能依赖 X.M (M<N)
```
