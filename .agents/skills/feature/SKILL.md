---
name: feature
description: 给已有项目追加功能。从功能想法出发，通过对话澄清需求，生成或追加 Epic/Story，可选同步 PRD，最后路由到实现。不要求 PRD 和架构文档预先存在。
---

# feature

给已有项目加功能的轻量入口。

这个 skill 解决的问题：项目已经跑起来了，用户想加一个新功能，但不想从 PRD 重新走一遍。

它和 `epic-story-generator` 的区别：
- `epic-story-generator` 是"从 PRD 全量拆解"，要求 PRD + Architecture 必须存在
- `feature` 是"从一个功能想法出发"，从对话和现有代码推导约束，不强制依赖文档

## 适用场景

- 用户说"我要加一个 XXX 功能"
- 用户有明确的功能想法，但还没有 Story 文件
- 功能规模可大可小：小到一个 Story，大到一个新 Epic 含多个 Story
- 用户希望功能需求被结构化记录到 Epic/Story 文件，而不是口述后就丢了

## 不适用场景

- 已经有 Story 文件，只需要实现 → 用 `do-story` 或 `run-story`
- 从零启动新项目，需要完整 PRD → 用 `product-requirements`
- 只是修 bug 或小调整，不需要记录 Story
- 用户明确要求做架构设计 → 用 `architecture`

## 执行哲学

**目标先行，过程校验，按需决策。**

不要死板按步骤走。带着目标进入，每一步的结果都是证据——用来判断方向是否正确，而不只是"这一步完成了没"。

- **目标先行**：每次启动先定义成功标准（什么算"这个 skill 跑完了"），后续所有判断对照这个标准
- **过程校验**：拆完 Story 后回头对照功能摘要，检查是否所有核心能力都被覆盖；发现遗漏立即补，不等到用户指出
- **按需决策**：追加 vs 新建、同步 PRD vs 跳过、路由实现 vs 只生成文件——这些不是预设步骤，而是根据当前上下文做的判断

### 决策矩阵

| 判断点 | 条件 A | 条件 B |
|--------|--------|--------|
| Epic 归属 | 功能是已有 Epic 的自然延伸 → 追加 | 功能是独立新能力域 → 新建 |
| PRD 同步 | docs/project/requirements.md 存在 且 新建 Epic → 同步 | docs/project/requirements.md 不存在 或 追加模式 → 跳过 |
| 路由实现 | 用户要求现在实现 → 接入 run-story | 用户只要 Story 文件 → 停止 |
| 停止升级 | 功能超出单 Epic 规模 → 引导到 architecture | 澄清后仍模糊 → 引导到 product-requirements |

## 输入

优先从用户输入中提取：
- 功能描述（必须）
- 目标用户 / 使用场景（如有）
- 已知约束或偏好（如有）
- 参考来源（如有）

## Workflow

### Phase 0: 初始化 (REQUIRED)

1. **加载模板**：读取 `epic-story.template.md` 理解 Epic/Story 输出结构
2. **扫描已有 Epic**：读取 `docs/tasks/epics/` 目录，记录已有 Epic 编号和 Story 编号上限

### Phase 1: 理解功能

目标：把模糊的功能想法变成清晰的功能定义。

1. **读取项目现状**（自动，不问用户）：
   - 读 `docs/tasks/epics/` 了解已有 Epic 和 Story
   - 读现有代码结构了解技术栈和模块划分
   - 如果 `docs/project/requirements.md` 存在，读取了解产品上下文
   - 如果 `docs/project/architecture.md` 存在，读取了解架构约束

2. **需求澄清**（对话式，控制在 3-5 个问题）：

   必须搞清楚的：
   - 谁用这个功能？什么场景下用？
   - 核心能力是什么？（用户做完这个操作后得到什么结果）
   - 边界在哪？（明确不做什么）

   按需追问的：
   - 和现有哪个模块最相关？
   - 有没有非功能要求？（性能、权限、并发）
   - 有没有参考产品或开源实现？
   - 有没有设计稿？

   原则：
   - 不要一次问超过 5 个问题
   - 能从代码和文档推断的不问
   - 用户回答模糊时追问一次，不纠缠

3. **输出功能摘要**（供用户确认）：

   ```
   功能：[一句话]
   用户：[谁]
   场景：[什么情况下用]
   核心能力：
   - [能力 1]
   - [能力 2]
   不含：
   - [明确排除的]
   涉及模块：[从代码推断]

   完成标准：
   - [ ] Epic/Story 文件已写入 docs/tasks/epics/
   - [ ] 每个核心能力至少被一个 Story 覆盖
   - [ ] 用户已确认 Story 粒度和 AC
   - [ ] [如触发] PRD 已同步
   ```

   **[BLOCKING gate]** 用户确认功能摘要后才能进入 Phase 2。如果用户要求调整，修改摘要后重新确认。

### Phase 2: 拆解 Epic + Story

1. **判断归属**：

   - 扫描 `docs/tasks/epics/` 已有的 Epic 文件
   - 判断新功能应该：
     - **追加到已有 Epic** — 功能属于某个已有 Epic 的自然延伸
     - **新建 Epic** — 功能是独立的新能力域
   - 将判断结果告知用户，用户确认

2. **拆 Story**：

   遵循 INVEST 原则：
   - Independent：独立可交付
   - Negotiable：可协商调整
   - Valuable：对用户有价值
   - Estimable：可估算
   - Small：1-2 Sprint 可完成
   - Testable：可测试验证

   每个 Story 拆完后需用户确认粒度。

3. **生成验收标准**：

   复用 `epic-story-generator` 的 AC 格式和可测试性标准：

   ```markdown
   - [ ] [可测试条件，含预期结果] `验证: <kind> <target> → <assert>`
   ```

   kind 为 `pytest` / `API` / `DB` / `Browser` 四选一。

   禁止模糊 AC：不接受"正确显示""合理处理"等无法断言的描述。

4. **生成 Epic 文件**：

   **追加模式**：在已有 Epic 文件末尾的 Story 列表中追加新 Story，更新依赖关系图。

   **新建模式**：使用 `epic-story.template.md` 格式生成新文件，放到 `docs/tasks/epics/`。

   新建时的 `source_documents` 字段：
   - 文档存在 → 填路径
   - 文档不存在 → 不填，不伪造

   Epic 编号规则：读取 `docs/tasks/epics/` 中最大编号 +1。

   Story 编号规则：
   - **新建 Epic**：从 X.1 开始
   - **追加到已有 Epic**：读取该 Epic 文件中最大 Story 编号 +1（如已有 4.1-4.5，新 Story 从 4.6 开始）

5. **覆盖校验**：拆完所有 Story 后，回头对照 Phase 1 功能摘要中的"核心能力"列表，逐条检查是否每个能力都被至少一个 Story 覆盖。发现遗漏则补充 Story，不等用户指出。

6. **[BLOCKING gate] 用户确认**：展示生成的 Epic/Story 内容，用户确认后才写入文件。

### Phase 3: 同步 PRD（条件触发）

触发条件（同时满足）：
- `docs/project/requirements.md` 存在
- 新功能是**新建 Epic**（不是追加 Story 到已有 Epic）

不触发时直接跳到 Phase 4。

同步方式：
1. 读 `docs/project/requirements.md`
2. 找到 `## 4. 功能需求` 章节
3. 在该章节末尾追加一个新的 Epic 子章节，格式与已有条目一致
4. 只追加，不改动已有内容
5. 告知用户 PRD 已同步更新

如果 `docs/project/requirements.md` 不存在：
- 不创建
- 不提示用户去创建
- 直接跳过

### Phase 4: 路由到实现

询问用户：

```
Epic/Story 已生成。接下来要：
- 现在开始实现第一个 Story（推荐）
- 选择要实现的 Story
- 先不实现，只生成 Story 文件
```

如果用户选择实现：
- 单个 Story → 接入 `run-story`
- 多个 Story → 按依赖顺序列出，用户选择起始 Story，接入 `run-story`

## Story 格式

复用 `epic-story.template.md` 中的格式，不另起一套：

```markdown
### Story X.Y: [标题]

**用户故事**: 作为 [角色]，我可以 [功能]，以便 [价值]

#### 验收标准
- [ ] [可测试条件] `验证: <kind> <target> → <assert>`
- [ ] [异常场景] `验证: <kind> <target> → <assert>`
- [ ] [边界条件] `验证: <kind> <target> → <assert>`

#### 前端验收标准
<!-- 仅当涉及 UI 交互时包含 -->
- [ ] [页面元素] `验证: Browser <selector> → exists`
- [ ] [交互行为] `验证: Browser <action> → <assert>`

**参考**: [相关文档引用]
**依赖**: Story X.Z / 无
```

## 停止条件

以下情况应停止并告知用户，不继续往下走：

- **功能描述过于模糊**：经过 3-5 个问题后仍无法确定核心能力和边界 → 建议用户先用 `product-requirements` 做完整的产品思考
- **功能规模超出 Epic 级别**：澄清后发现需要多个 Epic + 架构变更 → 建议用户先用 `architecture` 做架构设计
- **docs/tasks/epics/ 目录不存在且无法创建** → 报告问题，不伪造目录
- **追加模式下已有 Epic 文件格式无法识别** → 新建 Epic 而不是强行追加

## 与其他 skill 的关系

```
feature（本 skill）
  ├─ 产出 → docs/tasks/epics/ 中的 Epic/Story 文件
  ├─ 可选 → 同步 docs/project/requirements.md
  └─ 路由 → run-story → do-story → story-verify-fix → review
```

- `product-requirements`：从零写 PRD。`feature` 不替代它，只在已有 PRD 时做增量追加
- `epic-story-generator`：从 PRD 全量拆解。`feature` 不依赖它，但复用其模板和 AC 标准
- `run-story` / `do-story`：`feature` 生成 Story 后路由到它们执行实现

## 触发示例

```text
/feature 我想加一个 Excel 导入导出功能
```

```text
/feature 加一个企业微信登录，支持扫码和静默授权两种方式
```

```text
/feature 我们需要一个完整的审计日志系统，记录所有关键操作
```
