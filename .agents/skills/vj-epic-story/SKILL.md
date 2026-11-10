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
| 5 | **Batch Preview + 写盘**（单一 Intent Gate → 完整性验证 → 写盘 → HTML 视图） |

### Phase 1: 初始化

1. **加载模板**：读取 `epic-story.template.md` 理解输出结构；用户交互的展示格式在
   `references/display-formats.md`（§A-§E），到对应 Phase 需要展示时再读，不预加载
2. **编号自动发现**：
   - 新 Epic 号运行 `python3 .agents/skills/vj-epic-story/scripts/allocate_ids.py next-epic`
   - 追加 Story 运行 `python3 .agents/skills/vj-epic-story/scripts/allocate_ids.py next-story
     <epic-number> <epic-path>`
   - 编号由文件系统派生；不维护计数器或状态索引
   - 这是后续所有 Epic / Story 编号的唯一源
3. **检测已有文档**（仅标记状态，不询问用户）：
   - 检查 `docs/work/epics/` 目录状态
   - 已有 Epic 文件（平铺 `.md` 或目录形式）→ 标记 `has_existing = true`，记录路径列表
   - 目录为空 → 标记 `has_existing = false`
   - **幂等短路**：has_existing 且全部 Epic frontmatter 的 `source_digest` ==
     `shasum <PRD> | cut -c1-16` 当前值 → PRD 未变，直接报告"无变更，Epic/Story 保持现状"
     并结束（用户显式要求重拆时除外）；此短路不违反 Decompose-First——它只在输入零变化时
     跳过，而非拿旧结构锚定新拆分
   - **不要在此处询问"继续/添加/重写"**。决策推迟到 Phase 2.3 的差异对比阶段
   - 理由：用户在没看到"按当前需求该拆成啥"之前，无法判断该"继续/重写"，过早决策会造成 anchoring
4. **检测上游输入**：
   - **必需**: `docs/product/requirements.md` → 功能需求和用户故事
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
6. **配置自动推导（不单独设闸）**：
   - Epic 范围优先服从用户显式范围；未指定时覆盖 PRD 全部功能
   - 规模按 IDEAL Epic 数自动判为快速（<5）/标准（5-15）/完整（>15）
   - 输出结构只按 Phase 5 的实际 Story 数决定，不让用户预估
   - 只有多个范围选择会改变交付内容时，才把该选择加入 Phase 5 的单一 Intent Gate

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

读取 `docs/work/epics/` 下所有 Epic 文件，提取：
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

**展示格式**：见 `references/display-formats.md` §A。差异先进入批量预览，不在这里单独索要
confirm。

#### Phase 2.4: Epic 边界检查（不单独设用户闸）

- KEEP/CREATE/无风险 UPDATE 直接进入 Phase 2.5
- OBSOLETE、已有进行中 Story、或多个合理边界方案加入 Phase 5 的单一 Intent Gate
- `has_existing = false` → 跳过 2.2-2.3，把 IDEAL 列表加入 Phase 5 批量预览

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
- **2/3 通过** → 自动按失败项重拆一次；仍失败且根因是产品边界选择时，加入本轮唯一
  Intent Gate，技术性拆分问题则继续自动修正
- **<2/3（即 ≤1/3）** → BLOCKING，必须重回 Phase 2.1 重审 scope；需要用户裁决时沿用
  同一个 Intent Gate，不新开形式审批

**说明**：Balance 项在 Phase 2.5 阶段还没拆 Story，**用 PRD §4 该 Epic 包含的 Requirements 条数当代理指标**。Phase 5.1 写盘前会用真实 Story 数再次验证 balance。

**Stop Condition**：Scope clarity 或 Independence 项失败 + rework ≥2 次 → 弹窗"Epic 划分本身有问题（重叠 / 循环依赖），建议检查是否漏拆共同基础设施 / 边界划错"。

**展示格式**：见 `references/display-formats.md` §B（逐 Epic 三项体检结果 + 失败项问题/建议 + continue/fix/rework 选项）。

---

### Phase 2.6: 信息抽取 + 一次性补全

读取 `references/decomposition-analysis.md` 并按四步执行：Auto-Extract -> 用户旅程/页面地图 ->
System-Wide 六维扫描 -> Batch Decisions。所有 ⚠️/❓ 与 Epic 边界统一进入 Phase 5 的单一
Intent Gate；确定性映射不设人工闸。

完成判据：每个旅程步骤与异常都有 Story/AC 去向；前端 Epic 页面体验地图字段完整；六维扫描
结果已拆 Story、落 AC 或显式路由到 PRD/plan/repo baseline。

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

Story 粒度由 INVEST、覆盖空间和 AC 上限自动判定；所有需用户裁决的边界统一进入 Phase 5，
不逐 Story 停顿。

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

读取 `references/ac-design.md`。先按 Story 形态用 EP/BVA/决策表/状态迁移/流程走查派生候选，
再组织为 Happy / Edge / Error / Integration；不要从通用清单挑选凑数。

阻塞条件：每条 AC 缺 `验证: <kind> <target> -> <assert>` 三要素、行为 AC >7、跨层无
Integration、UI Story 无前端 AC、缺 Assumptions，或存在模糊不可断言结果。候选超过上限回
Phase 3 拆 Story。确定性格式由 `scripts/validate_story.py` 拦截。

### Phase 5: 批量预览 + 写盘

#### Phase 5.1: 在内存里组装所有产出（不写盘）

填充模板：将所有 Epic + Story + AC 决策**在内存中**填入 `epic-story.template.md`，组装出完整的文件内容（暂不写到磁盘）。

#### Phase 5.2: 写盘前批量预览（唯一 Intent Gate）

展示完整产出概览、IDEAL/现状差异和全部 ❓/⚠️ 决策。**预览默认折叠 AC 详情**，只显示
统计；用户可显式要求展开。只有未决项会改变产品行为、Epic 边界或验收口径时才 STOP；没有
这类未决项时直接写盘并报告，不要求形式确认。

**展示格式**：见 `references/display-formats.md` §D（逐 Epic 概览 + 每 Story 的 AC 分类计数 +
完整性验证清单 + 写盘后改动预告 + confirm/adjust/abandon/expand 选项）。

#### Phase 5.3: Intent Gate 结果（仅当 Phase 5.2 有阻塞未决项）

- `confirm` → 执行写盘（Phase 5.4）
- `adjust` → 接受用户具体反馈，回到对应 Phase 修订（如改 AC 回 Phase 4，改 Story 拆分回 Phase 3）
- `abandon` → 不写盘，记录到对话上下文供用户复用
- `expand epic-N` → 展开第 N 个 Epic 的所有 Story AC 详情，仍属于同一个 gate

**Stop Condition**：预览阶段反馈 ≥3 次 → 弹窗"反复调整未收敛，建议保存当前草稿 / 全部放弃"。

#### Phase 5.4: 决定输出结构 + 写盘

按实际 Story 数自动选择结构（不询问用户）：

   | 该 Epic 的 Story 数 | 输出结构 |
   |---------------------|----------|
   | **<3 Story** | 平铺：`docs/work/epics/epic-{N}-{slug}.md`（单文件，Story 内嵌） |
   | **≥3 Story** | 展开：`docs/work/epics/epic-{N}-{slug}/`（目录） |

   **展开模式的目录结构**：

   ```
   docs/work/epics/epic-{N}-{slug}/
   ├── epic.md                        # Epic 主文档（不含 Story 详情，只保留 Story 列表引用）
   └── stories/
       ├── story-{N}-1-{slug-1}.md    # 每个 Story 独立文件
       └── story-{N}-2-{slug-2}.md
   ```

   - 文件名使用 Epic 内 Story 编号，不再分配无消费者的全局 US 序号；既有 `usNNN-*`
     文件作为兼容输入继续读取，不要求迁移
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
   - [ ] Story ID 编号正确且 Epic 内连续（X.1、X.2……）

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

#### Phase 5.8: 生成人读 HTML 视图

按 Phase 5.4 实际选择的输出结构，**只跑对应的一条**（另一条的路径不存在，跑了会报错）：

```bash
python3 .agents/skills/_shared/scripts/render_doc_html.py docs/work/epics/epic-{N}-{slug}.md   # 平铺模式
python3 .agents/skills/_shared/scripts/render_doc_html.py docs/work/epics/epic-{N}-{slug}/    # 展开模式（目录递归）
```

md/html 分工与派生视图约定按脚本头注释执行，本 skill 不复述。渲染失败不阻塞流程，报告即可。

**archify 旅程图（默认生成，缺 archify 才降级）**：HTML 视图的主旅程会 iframe 引用 archify 图，
寻图按文件名绑定（机制见脚本 `journey_embed` docstring）——目录型 epic 用目录级 `journey.html`
（源 `journey.workflow.json`，sidecar `journey.source-digest`）；平铺 epic 共享 `epics/` 目录，
各配 `{epic文件名}.journey.html`（源/sidecar 同前缀：`{epic文件名}.journey.workflow.json` /
`{epic文件名}.journey.source-digest`）。写盘后默认为每个新 epic 生成旅程图并写 sidecar；
环境缺 archify 时降级为自动泳道板并在收尾报告注明，不算失败。本次生成/UPDATE 改动了
`## 用户旅程` 章节且渲染输出 stale warning 时**必须同步**：改源 JSON → archify 重渲 →
把 warning 打印的新摘要写入对应 sidecar；不得静默留过期图。首轮过检规则与**多图并行
subagent 纪律（硬超时 + 降级）**按 `_shared/vj-skill-conventions.md`「archify 出图约定」
执行，本 skill 不复述。

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

1. **不替用户做产品决策**：多个合理选项会改变可观察行为时进入单一 Intent Gate
2. **不制造形式审批**：粒度、格式和可由硬规则确定的事项自动处理，不逐阶段重复确认
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
16. **编号从文件派生**：只通过 `scripts/allocate_ids.py` 分配新 Epic/Story 编号；状态不复制到全局看板
17. **Epic Quality Gate 是 BLOCKING**：3 项体检 <2/3 通过必须重审 scope，不允许跳过（见 Phase 2.5）
18. **OBSOLETE 不删文件**：REPLAN 模式归档的 Epic 只改 frontmatter `status: archived`，保留历史记录
19. **Stop Conditions（防止死循环）**：
    - 单一 Intent Gate 反馈 ≥3 次 → 强制弹窗"继续 / 重审上游 / 放弃"
    - Epic Quality Gate <2/3 + rework ≥2 次 → 升级到"scope 本身有问题"，建议重审 PRD
    - 理由：拉锯到第 3 次还在调，几乎一定是 PRD 或 Architecture 有歧义，不是 epic-story 这一层能解决的
20. **Derive, don't checklist**：Edge/Error AC 来自 Phase 4 Step 0 的结构化派生（EP / BVA / 决策表 / 状态迁移 / 单 Story 流程），不从通用清单挑选凑数（见 Phase 4）
21. **完整性靠拆分而非堆叠**：派生覆盖空间超 AC 上限（≤7）→ 拆 Story（见 Phase 3 覆盖空间拆分触发器）；砍掉的低优先级 case 进 `Assumptions [SCOPE]`，不静默丢
22. **无人值守模式**：单一 Intent Gate 不可达时采用 IDEAL/推断结果继续，所有 ⚠️/❓ 项记为
    "假设待审批 + Confidence: H/M/L"，Epic frontmatter 标 `status: draft-unattended`。
    Phase 2.5 Quality Gate 与 Phase 5.5 机检 ERROR 仍硬停。
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
  output_dir: docs/work/epics/
  id_allocator: .agents/skills/vj-epic-story/scripts/allocate_ids.py
  flat_threshold: 3                              # Story 数 <3 平铺，≥3 展开为目录
  flat_format: "epic-{N}-{slug}.md"
  expanded_format: "epic-{N}-{slug}/"
  story_filename_format: "us{NNN}-{slug}.md"     # 仅展开模式使用
  ac_max_per_story: 7                            # 行为 AC 总数硬上限；FE AC 单独计数
  fe_ac_max_per_story: 4                         # 前端呈现/交互/设计验证 AC 建议上限
  dependency_tracking: true
  forbid_forward_dependency: true                # Story X.N 只能依赖 X.M (M<N)
```
