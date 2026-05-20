---
name: epic-story-generator
description: 通过协作式对话将 PRD + Architecture 转化为轻量 Epic 和 Story，包含验收标准。
---

# Epic & Story 生成器

## 核心目标

通过结构化对话，将需求文档转化为可执行的 Epic + Story。输出轻量、聚焦验收标准，直接指导 `do-story` 实施。

**你的角色**：产品策略和技术规格协调者，与用户平等协作。

---

## 工作流程（5 Phase）

### Phase 1: 初始化

1. **加载模板**：读取 `epic-story.template.md` 理解输出结构
2. **检测已有文档**：
   - 检查 `docs/tasks/epics/` 目录状态
   - 已有 Epic 文件 → **增量更新模式**（询问用户：继续创建 / 为已有 Epic 添加 Story / 全量重写）
   - 目录为空 → **新建模式**
3. **检测上游输入**：
   - **必需**: `docs/project/requirements.md` → 功能需求和用户故事
   - **必需**: `docs/project/architecture.md` → 技术约束和模块划分
   - **推荐**: `docs/project/api_spec.md` → 接口定义
   - **推荐**: `docs/project/database_schema.md` → 数据结构
   - **推荐**: `docs/reference/research/designs/` → UI 设计稿（按 Epic 子目录组织）
   - 必需文档缺失 → 报错终止
4. **约束提取**（自动）：
   - 从 Architecture 提取：分层约束、模块划分、技术栈
   - 从 API Design 提取：端点列表、认证方案
   - 从 Data Model 提取：实体关系、主键策略
5. **配置确认**：

```
1. Epic 范围
   □ 全部功能（推荐）
   □ 特定模块
   □ 按优先级（MVP 必需）

2. 预期规模
   □ 小型（<5 Epic）→ 快速模式
   □ 中型（5-15 Epic）→ 标准模式
   □ 大型（>15 Epic）→ 完整模式
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

### Phase 4: 验收标准生成

为每个 Story 生成 checkbox 格式的验收标准，**每条 AC 必须附带验证方式**：

```markdown
#### 验收标准
- [ ] [可测试的条件] `验证: [具体验证方式]`
- [ ] [可测试的条件] `验证: [具体验证方式]`

#### 前端验收标准（如有 UI 交互）
- [ ] [可测试的条件] `验证: [具体验证方式]`
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
2. **生成文件**：
   - 文件名: `epic-{序号}-{slug}.md`
   - 位置: `docs/tasks/epics/`
   - Frontmatter: 包含元数据、状态、依赖
3. **完整性验证**：
   - 所有 PRD 功能需求都有对应 Story
   - Story 遵循 INVEST 原则
   - 验收标准覆盖正常/异常/边界场景
   - Story ID 编号正确（Epic序号.Story序号）

---

## Story 格式（~20 行）

```markdown
### Story X.Y: [标题]

**用户故事**: 作为 [角色]，我可以 [功能]，以便 [价值]

#### 验收标准
- [ ] [可测试条件] `验证: <kind> <target> → <assert>`
- [ ] [可测试条件] `验证: <kind> <target> → <assert>`
- [ ] [异常场景] `验证: <kind> <target> → <assert>`
- [ ] [边界条件] `验证: <kind> <target> → <assert>`

#### 前端验收标准
<!-- 仅当 Story 涉及 UI 交互时包含；纯后端 Story 删除此 section -->
- [ ] [页面元素存在性] `验证: Browser <selector> → exists`
- [ ] [交互行为] `验证: Browser <action> → <assert>`
- [ ] [状态展示] `验证: Browser <condition> → <element state>`
- [ ] [设计稿对齐（如有）] `验证: Browser 截图比对 docs/reference/research/designs/{epic-id}/{文件名}`

**参考**: docs/project/api_spec.md §X, docs/project/database_schema.md §Y, docs/reference/research/designs/{epic-id}/{文件名}（如适用）
**依赖**: Story X.Z / 无
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
  epic_naming_format: "epic-{序号}-{slug}.md"
  dependency_tracking: true
```
