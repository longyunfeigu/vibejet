---
name: vj-feature
description: 给已有项目追加功能。从功能想法出发，通过对话澄清需求，生成或追加 Epic/Story，可选同步 PRD，最后路由到实现。不要求 PRD 和架构文档预先存在。
---

# vj-feature

给已有项目加功能的轻量入口。

这个 skill 解决的问题：项目已经跑起来了，用户想加一个新功能，但不想从 PRD 重新走一遍。

它和 `vj-epic-story` 的区别：
- `vj-epic-story` 是"从 PRD 全量拆解"，要求 PRD + Architecture 必须存在
- `vj-feature` 是"从一个功能想法出发"，从对话和现有代码推导约束，不强制依赖文档

## 适用场景

- 用户说"我要加一个 XXX 功能"
- 用户有明确的功能想法，但还没有 Story 文件
- 功能规模可大可小：小到一个 Story，大到一个新 Epic 含多个 Story
- 用户希望功能需求被结构化记录到 Epic/Story 文件，而不是口述后就丢了

## 不适用场景

- 已经有 Story 文件，只需要实现 → 交给 `vj` 路由；普通 Story 直接执行，strict/Epic 才走 `vj-epic-plan` + `vj-work`
- 从零启动新项目，需要完整 PRD → 用 `vj-product-requirements`
- 只是修 bug 或小调整，不需要记录 Story
- 用户明确要求做架构设计 → 用 `vj-architecture`

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
| PRD 同步 | docs/product/requirements.md 存在 且 新建 Epic → 同步 | docs/product/requirements.md 不存在 或 追加模式 → 跳过 |
| 路由实现 | 用户要求现在实现 → 交给 `vj` 选择 Story/Epic 轨 | 用户只要 Story 文件 → 停止 |
| 停止升级 | 功能超出单 Epic 规模 → 引导到 vj-architecture | 澄清后仍模糊 → 引导到 vj-product-requirements |

## 输入

优先从用户输入中提取：
- 功能描述（必须）
- 目标用户 / 使用场景（如有）
- 已知约束或偏好（如有）
- 参考来源（如有）

## Workflow

### Phase 0: 初始化 (REQUIRED)

1. **加载模板**：读取 `epic-story.template.md` 理解 Epic/Story 输出结构
2. **分配编号**：新 Epic/追加 Story 都调用
   `.agents/skills/vj-epic-story/scripts/allocate_ids.py`；编号从现有文件派生，不维护全局看板。
3. **扫描已有 Epic**：读取 `docs/work/epics/` 目录，记录已有 Epic、状态及 Story 编号上限。

### Phase 1: 理解功能

目标：把模糊的功能想法变成清晰的功能定义。

1. **读取项目现状**（自动，不问用户）：
   - 读 `docs/work/epics/` 了解已有 Epic 和 Story
   - 读现有代码结构了解技术栈和模块划分
   - 如果 `docs/product/requirements.md` 存在，读取了解产品上下文
   - 如果 `docs/project/architecture.md` 存在，读取了解架构约束

2. **需求澄清**（能推断则不问；需要时一次批量问 1-5 个问题）：

   必须搞清楚的：
   - 谁用这个功能？什么场景下用？
   - 核心能力是什么？（用户做完这个操作后得到什么结果）
   - 边界在哪？（明确不做什么）

   按需追问的：
   - 和现有哪个模块最相关？
   - 有没有非功能要求？（性能、权限、并发）
   - 有没有参考产品或开源实现？
   - 有没有设计稿？
   - 涉及 UI 时，这个页面属于 front-of-house（login / landing / 空首屏 / 营销页）还是 operational（dashboard / table-list / detail / form / 设置）？
   - 涉及 UI 时，产品身份、品牌表达、首屏主任务、空/加载/错误状态是否已有约束？

   原则：
   - 不要一次问超过 5 个问题；不要逐题开新一轮 gate
   - 能从代码和文档推断的不问
   - 用户回答模糊时追问一次，不纠缠

   UI 需求补强按 `.agents/skills/_shared/ui-planning-contract.md` 执行（屏型判定 §1、双轨触发 §2、
   复杂操作流判定 §3、屏型规划要求 §4 的唯一真相源，本 skill 不复述规则条目）。
   核心口径：强制的是页面体验地图完整度，不是跑满所有 ui-* skill；按缺口触发对应 skill。

   本 skill 特有的 brief 产物要求：
   - 产品级 brief 至少包含：产品定位、目标用户、品牌气质、信任点、核心屏型、视觉反模式、front-of-house 要表达的价值。
   - 单屏级 brief 至少包含：页面类型、目标用户、进入场景、主任务、最多 2 个次任务、P0/P1/P2 信息优先级、必须覆盖状态、品牌/视觉约束、明确禁止项。

3. **建立 Intent Contract**：

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
   UI Brief（如涉及前端）：
   - 轨道：产品/品牌方向轨 / 单屏体验轨 / 两者都需要 / 不需要
   - 完整度：已完整 / 缺结构需补 `ui-page-goal-structure` / 缺状态需补 `ui-state-coverage` / 缺流程需补 `ui-user-journey-audit` / 缺品牌需补 `vj-design-md-matcher`
   - 屏型：front-of-house / operational / mixed
   - 主任务：[用户进入该屏最该完成什么]
   - 信息优先级：P0 / P1 / P2
   - 状态覆盖：默认 / loading / empty / error / disabled / permission（按需）
   - 品牌与视觉约束：[产品身份、价值点、参考、禁止项]
   - 全局设计前置：[DESIGN.md 已存在 / 需先跑 vj-design-md-matcher / 不适用]

   完成标准：
   - [ ] Epic/Story 文件已写入 docs/work/epics/
   - [ ] Epic/Story 编号由 allocate_ids.py 分配且无冲突
   - [ ] 每个核心能力至少被一个 Story 覆盖
   - [ ] [如涉及 UI] UI brief 已进入 Epic 的页面体验地图与前端 AC
   - [ ] Story 粒度和 AC 通过硬规则校验；如有产品未决项，已在单一 Intent Gate 解决或标待审批
   - [ ] [如触发] PRD 已同步
   ```

   **单一 Intent Gate**：只有存在会改变可观察行为的未决产品选择时才阻塞确认；需求清楚、
   实现可逆时直接进入 Phase 2，并在写盘前批量预览中展示这份 contract。不要把“我理解了”
   变成形式审批。

### Phase 2: 拆解 Epic + Story

1. **判断归属**：

   - 扫描 `docs/work/epics/` 已有的 Epic 文件
   - 判断新功能应该：
     - **追加到已有 Epic** — 功能属于某个已有 Epic 的自然延伸
     - **新建 Epic** — 功能是独立的新能力域
   - 有唯一合理归属时直接采用；多个归属都会改变长期产品边界时，合并进单一 Intent Gate

2. **拆 Story**：

   遵循 INVEST 原则：
   - Independent：独立可交付
   - Negotiable：可协商调整
   - Valuable：对用户有价值
   - Estimable：可估算
   - Small：1-2 Sprint 可完成
   - Testable：可测试验证

   Story 粒度由 INVEST、AC 上限和覆盖校验判定，不逐 Story 向用户索要形式确认。

3. **生成验收标准**：

   复用 `vj-epic-story` 的 AC 格式和可测试性标准：

   ```markdown
   - [ ] [可测试条件，含预期结果] `验证: <kind> <target> → <assert>`
   ```

   kind 为 `pytest` / `API` / `DB` / `Browser` 四选一。

   禁止模糊 AC：不接受"正确显示""合理处理"等无法断言的描述。

   UI Story 额外规则：按 `.agents/skills/_shared/ui-planning-contract.md` 执行——
   页面体验地图完整度 BLOCKING（§5）、按缺口强制触发 ui-* skill（§2/§3）、
   屏型 AC 要求与前端 AC 写法（§4/§7）。本 skill 不复述规则条目。

4. **生成 Epic 文件**：

   **追加模式**：在已有 Epic 文件末尾的 Story 列表中追加新 Story，更新依赖关系图。

   **新建模式**：使用 `epic-story.template.md` 格式生成新文件，放到 `docs/work/epics/`。

   新建时的 `source_documents` 字段：
   - 文档存在 → 填路径
   - 文档不存在 → 不填，不伪造

   编号规则：
   - **新建 Epic**：运行 `allocate_ids.py next-epic`；Story 的 Epic 内序号从 X.1 开始
   - **追加到已有 Epic**：运行 `allocate_ids.py next-story <epic-number> <epic-path>`
   - 展开模式新 Story 文件名为 `story-{epic}-{local-seq}-{slug}.md`；既有 `usNNN-*` 兼容读取

5. **覆盖校验**：拆完所有 Story 后，回头对照 Phase 1 功能摘要中的"核心能力"列表，逐条检查是否每个能力都被至少一个 Story 覆盖。发现遗漏则补充 Story，不等用户指出。

6. **机检（必跑）**：把组装好的 Epic/Story 内容写入临时文件后执行
   `python3 .agents/skills/vj-epic-story/scripts/validate_story.py <临时文件>`——
   覆盖 AC≤7 / `验证:` 三要素 / Assumptions 三要素 / Feature Bundling / 前向依赖，
   exit 1 则修复后重跑，禁止带 ERROR 进入用户确认。

7. **批量预览与写盘**：一次展示 Intent Contract、Epic 归属、Story 列表、AC 计数和所有
   待确认推断。若单一 Intent Gate 已解决且没有新未决选择，直接写盘；否则在这里一次确认后
   写盘。用户明确要求“只生成文档、先别落盘”时除外。

### Phase 3: 同步 PRD（条件触发）

触发条件（同时满足）：
- `docs/product/requirements.md` 存在
- 新功能是**新建 Epic**（不是追加 Story 到已有 Epic）

不触发时直接跳到 Phase 4。

同步方式：
1. 读 `docs/product/requirements.md`
2. 找到 `## 4. 功能需求` 章节
3. 在该章节末尾追加一个新的 Epic 子章节，格式与已有条目一致
4. 只追加，不改动已有内容
5. 告知用户 PRD 已同步更新

如果 `docs/product/requirements.md` 不存在：
- 不创建
- 不提示用户去创建
- 直接跳过

### Phase 4: 路由到实现

若用户已经要求立即实现，直接交给 `vj` router，不重复询问。只有用户意图未说明是否继续实现
时，才一次询问：

```
Epic/Story 已生成。接下来要：
- 现在开始实现第一个 Story（推荐）
- 选择要实现的 Story
- 先不实现，只生成 Story 文件
```

如果用户选择实现：交给 `vj` router。无 strict trigger 的单 Story 用轻量执行计划直接实现；
命中 strict 或 Epic 级范围才接 `vj-epic-plan` → `vj-work`。

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

## 无人值守模式

作为 subagent 运行或用户不可达时，单一 Intent Gate 不阻塞——
按最合理理解继续，所有待确认项记为"假设待审批 + Confidence: H/M/L"，生成的 Epic/Story
frontmatter 标 `status: draft-unattended`。**例外**：Phase 2 机检 ERROR 是质量闸，仍硬停。
Phase 4 路由实现在无人值守下默认不启动（只生成文件），除非调用方明确要求继续。
绝不静默拍板、绝不静默跳过。

## 停止条件

以下情况应停止并告知用户，不继续往下走：

- **功能描述过于模糊**：经过 3-5 个问题后仍无法确定核心能力和边界 → 建议用户先用 `vj-product-requirements` 做完整的产品思考
- **功能规模超出 Epic 级别**：澄清后发现需要多个 Epic + 架构变更 → 建议用户先用 `vj-architecture` 做架构设计
- **docs/work/epics/ 目录不存在且无法创建** → 报告问题，不伪造目录
- **追加模式下已有 Epic 文件格式无法识别** → 新建 Epic 而不是强行追加

## 与其他 skill 的关系

```
vj-feature（本 skill）
  ├─ 产出 → docs/work/epics/ 中的 Epic/Story 文件
  ├─ 可选 → 同步 docs/product/requirements.md
  └─ 路由 → vj Story track 或 vj-epic-plan → vj-work → verify/review/QA（按风险）
```

- `vj-product-requirements`：从零写 PRD。`vj-feature` 不替代它，只在已有 PRD 时做增量追加
- `vj-epic-story`：从 PRD 全量拆解。`vj-feature` 不依赖它，但复用其模板和 AC 标准
- `vj`：`vj-feature` 生成 Story 后由它决定轻量 Story 轨还是完整 Epic 轨

## 触发示例

```text
/vj-feature 我想加一个 Excel 导入导出功能
```

```text
/vj-feature 加一个企业微信登录，支持扫码和静默授权两种方式
```

```text
/vj-feature 我们需要一个完整的审计日志系统，记录所有关键操作
```
