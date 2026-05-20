---
name: epic-story-generator
description: 通过协作式对话将 PRD + Architecture 转化为轻量 Epic 和 Story，包含验收标准。
---

# Epic & Story 生成器

## 核心目标

通过结构化对话，将需求文档转化为可执行的 Epic + Story。输出轻量、聚焦验收标准，直接指导 `do-story` 实施。

**你的角色**：产品策略和技术规格协调者，与用户平等协作。

---

## 工作流程（6 Phase）

### Phase 1: 初始化

1. **加载模板**：读取 `epic-story.template.md` 理解输出结构
2. **配置自动发现**（kanban_board.md）：
   - 检查 `docs/tasks/kanban_board.md` 是否存在
   - **存在** → 从 Tracker Configuration 表读取 `Next Epic Number` / `Next Story Number`；从 Epic Story Counters 拿已有 Epic 列表
   - **不存在** → 从 skill 目录 copy `kanban_board.template.md` 到 `docs/tasks/kanban_board.md`，替换 `{{PROJECT_NAME}}` / `{{DATE}}` 占位符
   - 这是后续所有 Epic / Story 编号的唯一源
3. **检测已有文档**：
   - 检查 `docs/tasks/epics/` 目录状态
   - 已有 Epic 文件（平铺 `.md` 或目录形式）→ **增量更新模式**（询问用户：继续创建 / 为已有 Epic 添加 Story / 全量重写）
   - 目录为空 → **新建模式**
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

### Phase 2: Epic 识别

**识别逻辑**（按优先级）：
1. PRD 已有 Epic 章节 → 直接使用
2. Architecture 的业务模块 → 映射为 Epic
3. 相关功能需求 → 自然分组为 Epic

**引导流程**：

```
基于 PRD 和 Architecture，识别出以下 Epic 候选：

| Epic 候选 | 来源 | 包含功能 | 优先级建议 |
|----------|------|----------|------------|
| [Epic A] | PRD §3.1 | [功能列表] | P0 (MVP) |
| [Epic B] | Architecture 模块 B | [功能列表] | P1 |

需要确认：
1. Epic 划分是否合理？需要合并/拆分？
2. 优先级排序是否正确？
```

**命名规范**：使用业务术语（"用户认证" 而非 "JWT实现"），体现用户价值。

### Phase 2.5: System-Wide Considerations 抽取

在拆 Story 之前，为**每个**已确认的 Epic 生成 System-Wide Considerations。目的是挖出隐藏 Story —— 被这个 Epic 牵动但容易遗漏的其他模块、跨层副作用、不变量等。

**自动扫描来源**：
1. Architecture → 识别此 Epic 跨越的模块边界
2. API Design → 找此 Epic 触及的端点的其他消费方
3. Data Model → 找共享数据 / 外键依赖 / 索引影响
4. 已有 Epic 列表 → 找上下游 Epic 的耦合点

**为每个 Epic 输出 6 个维度**：

```
- 跨模块影响: [哪些其他 Epic / 模块 / 服务 / 第三方会被牵动]
- 不变量保护: [哪些现有行为 / 数据约束 / API 行为不能被破坏]
- 状态生命周期: [并发 / 缓存 / 重试 / 清理 / 长事务风险]
- API 表面一致性: [其他端点 / 界面 / 客户端是否需要同步改]
- 错误传播: [错误如何跨层 / 跨服务传递]
- 权限边界: [涉及的角色 / 资源所有权 / 越权场景]
```

**用户交互**：

```
基于 Epic [N] 的 System-Wide 影响分析：

| 维度 | 影响项 | 建议 |
|------|--------|------|
| 跨模块影响 | [模块 X 的 Y 行为会被牵动] | 新增 Story 覆盖 / 已在 Epic Z 内 / 仅需在现有 Story 加 AC |
| 不变量保护 | [现有 API 契约 Z] | 加 Regression Story / 加进现有 Story 的 AC |
| ... | ... | ... |

需要确认：
1. 这些影响项是否需要新增 Story？
2. 或者扩展已有 Story 的 AC（Edge/Integration 类别）？
3. 或者保持现状（影响已被 Epic 范围隐含覆盖）？
```

**输出**：
- 填入 Epic 文档的 `## System-Wide Considerations` section（template 里已预留）
- 可能产生的新 Story 候选清单，进入 Phase 3 拆分
- 可能产生的 AC 增强项，进入 Phase 4 生成

**重要**：System-Wide 项**不一定**都要变成 Story —— 它们的存在是为了让 Phase 3/4 在拆 Story 和写 AC 时主动覆盖。判断规则：
- 影响项已被现 Epic 的 Story 自然覆盖 → 仅作为 Epic 文档记录
- 影响项独立成块、有自己的验收标准 → 拆出新 Story
- 影响项是对现有行为的保护 → 进入对应 Story 的 Edge/Error/Integration AC

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

### Phase 5: 生成与验证

1. **填充模板**：将所有决策填入 `epic-story.template.md`

2. **决定输出结构**（按实际 Story 数自动选择，不询问用户）：

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

3. **同一 Epic 内不允许混用结构**：要么全平铺，要么全展开。增量添加 Story 时若已有 Story 数从 2 增到 3，必须迁移到展开模式（询问用户确认后执行）。

4. **完整性验证**：
   - [ ] 所有 PRD 功能需求都有对应 Story
   - [ ] Story 遵循 INVEST 原则
   - [ ] 验收标准按 4 分类组织（Happy / Edge / Error / Integration），覆盖度自检通过
   - [ ] AC 总数 ≤7（见 Phase 4）
   - [ ] Story 标题无 Feature Bundling（见 Phase 3）
   - [ ] 每个 Story 有 `#### Assumptions` section（"无" 也算）
   - [ ] 每个 Epic 有 System-Wide Considerations section
   - [ ] Epic 有 Success Criteria（P0/P1 至少 3 条，P2/P3 至少 1 条）
   - [ ] Story ID 编号正确（Epic 内序号 X.Y + 全局 US{NNN}）

5. **无前向依赖校验**（BLOCKING）：

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

   发现前向依赖 → **停止输出**，向用户报告冲突，提示两种解决方式：(a) 调整 Story 顺序使依赖方向正确；(b) 合并两个 Story（如果实际无法解耦）。

6. **回写 kanban_board.md**（生成成功后）：
   - 更新 Tracker Configuration：`Next Epic Number` 和 `Next Story Number` 按本次新增数量递增
   - 在 Epic Story Counters 表追加/更新本次 Epic 行（标题、状态 `draft`、优先级、Story 数、路径）
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
6. **检测到已有文档必须询问**：不直接覆盖
7. **Feature Bundling 禁止**：Story 标题禁止用 "和 / & / + / ," 连接两个独立能力（见 Phase 3）
8. **AC 总数硬上限 ≤7**：超过必须拆 Story，不允许通过删类别压缩（见 Phase 4）
9. **Assumptions section 必须存在**：每个 Story 必填，无假设填"无"，不能删 section
10. **无前向依赖**：Story X.N 只能依赖 X.M (M<N) 或更小序号 Epic 的 Story（见 Phase 5）
11. **kanban_board.md 是编号唯一源**：Next Epic Number / Next Story Number 不重用废弃编号

---

## 与其他 Skill 的协作

```
product-requirements → architecture → api-design → data-model
                                                      ↓
                                          epic-story-generator
                                                      ↓
                                    "实现 Story X.Y" → Plan → do-story
```

- **输入来源**: product-requirements, architecture, api-design, data-model
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
