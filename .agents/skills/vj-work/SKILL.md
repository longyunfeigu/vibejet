---
name: vj-work
description: 消费 vj-epic-plan 产出的 epic 实现计划并落地：按 Implementation Unit 拆任务、按 vj-epic-plan 算好的并行波次用 subagent（worktree 隔离）并行执行，逐 Unit 尊重 Execution note（如 test-first）实现、跑该 Unit 的 Verification 当 done 信号、增量提交。用户说"执行这个 plan""做 epic X""跑实现""把计划落地""vj-work"时使用。在 vj-epic-plan 之后使用。
---

# vj-work — Epic 计划执行器

把 `vj-epic-plan` 产出的 epic 实现计划（`docs/tasks/plans/{date}-epic-{N}-{slug}-plan.md`）系统化落地成"已实现、已验证、已提交"的代码。

**工作流位置**：
```
vj-epic-story (WHAT) → vj-epic-plan (HOW) → vj-work (执行, 本 skill) → vj-compound (沉淀)
```

**设计取舍**：只借 compound `ce-work` 的执行机制（Unit 驱动、文件交集并行安全检查、worktree 隔离子代理、增量提交、边做边简化），按 vj 轻量风格自包含实现，**零插件耦合**——不依赖 compound 插件、不调 ce-* agent。

## 铁律

- **plan 是决策依据，不是执行脚本**。Appendix C 的 Unit 给目标/文件/方法/验收；HOW 的具体代码由本 skill 执行时决定。
- **不改 plan 正文**。进度由 git commit 承载；唯一允许的 plan 改动是收尾时把 frontmatter `status: active → completed`。
- **每个 Unit 的 `Verification` 字段是该 Unit 的 done 信号**，必须实际跑通（命令全绿）才算完成。
- **尊重 `Execution note`**：标了 test-first 就先写失败测试再实现，且不在同一步写测试与实现、不跳过"确认测试先失败"。trivial 改动（纯配置/重命名/纯样式）可跳过 test-first。
- **KISS / YAGNI**：只实现 Unit 要求的，不加投机抽象、不动无关代码、匹配既有约定（信封 / DDD 垂直切片 / UoW 等，见 plan 的复用锚点）。
- **⛔ 并行不可随意降级**：波次计划（§6/Appendix D）标明同波内 ≥2 个 Unit 无文件冲突 + 无逻辑依赖，且当前运行时具备 subagent + 独立写入隔离能力 → Phase 3 **必须**并行。禁止以"稳妥 / 减少风险 / 简化"为由退化为串行；唯一合法降级条件是平台缺少 subagent 或独立写入隔离能力，且必须在 ledger 写明 runtime fallback 原因。
- **UI Unit 必须遵循 Design context**：task 文档 Technical Approach 中若含 `Design context（UI Unit 必读）` 或旧版 `Visual style（UI Unit 必读）` 块，实现前必须读取现有前端 theme / 组件模式，优先读取 `docs/project/DESIGN.md`，缺失时 fallback `docs/project/design_guidelines.md` 并标注；两者都缺失时暂停 UI 实现，先给出轻量 Design Read 或补 `DESIGN.md` 草案。加载 `design-taste-frontend` 只作为防默认风格兜底，项目 `DESIGN.md` 优先。
- **前端执行不得临时套风格库**：`vj-work` 不在执行期从 vibeui / awesome-design-md 自动挑新 DESIGN.md。设计参考选择必须在上游沉淀到 `docs/project/DESIGN.md` 或 plan/task 文档。
- **UI Unit 必须视觉验收**：完成前必须用浏览器截图检查桌面与移动端；无文字溢出、无元素重叠，主操作清晰，空态/加载/错误/成功/无权限状态完整，并与 `DESIGN.md`、页面体验地图一致。
- **完成整个 feature**，不留 80% 半成品。

## 输入

```
vj-work docs/tasks/plans/2026-06-01-epic-1-...-plan.md   # 指定 plan
vj-work epic-1                                            # 按 epic 编号定位 plan
vj-work                                                   # 未指定则取 output_dir 下最新 plan
```

## 配置项

```yaml
epic_work_executor:
  plans_dir: docs/tasks/plans/          # plan 来源
  default: latest                        # 未指定时取最新 plan
  learnings_skill: vj-compound           # 收尾沉淀（可选）
  worktree_root: .vj/worktrees/          # 并行 subagent 的隔离 worktree 根目录（需在 .gitignore）
  runtime_adapter: auto                  # Claude Agent / Codex multi_agent_v1 / inline fallback
  work_dir: docs/tasks/work/epic-{N}-{slug}/  # 执行产物目录：_ledger.md（总账/索引）+ 每 task 一份 7 段文档
  approval_gate: true                    # 生成全部 task 文档后、动代码前，停下请用户批准
```

---

## 工作流

### Phase 0：定位 plan 与环境

1. **定位 plan**：按输入解析；`vj-work` 空参时取 `plans_dir` 下最新的 `*-plan.md`。读全文。
2. **解析执行原料**（只读这些，不解析正文论证）：
   - `## 6. 实现单元与依赖`：Unit 概览表 + 依赖 DAG（每 Unit 的 `Depends`）。
   - `Appendix C` 每个 Unit 的：`Goal`、`Files`(Create/Modify/Test)、`Approach`、`Execution note`、`Patterns to follow`、`Test scenarios`、`Verification`。
   - `Appendix D` 的并行波次表 + 共享文件冲突点表（**权威波次计划**，Phase 2 直接消费、不重算）。
   - `Scope Boundaries` / `Out of Scope`：实现中若被带偏，回头对照。
   - `Requirements`（R-ID 列表，常在 Unit 概览或 §1）+ `Deferred to Implementation` / `Implementation-Time Unknowns`：前者供 Phase 4 逐条核对；后者是规划期故意留给执行期解决的问题，开工前先看，免得中途被绊住。
3. **分支检查（轻量，仅校验 worktree base）**：本 skill 改代码一律切 worktree、不直接往当前分支堆 commit，所以无需"防止误提交"那套——只校验一件事：**当前分支是这个 epic 的正确 base 吗？**（worktree 从当前分支切出、最终 merge 回当前分支，所以当前分支即集成目标）。
   - 不在默认分支 → 直接以当前分支为 base；分支名无意义（如自动生成）时建议改名后继续。
   - 在默认分支 → 🛑 **STOP** 停下确认：epic 工作通常不落在默认分支（约定 epic 分支 merge 进集成分支），确认 base 后再继续。

### Phase 1：装载 task 文档 + 看板（默认轻，缺失才生成）

执行产物在 `work_dir`：`docs/tasks/work/epic-{N}-{slug}/`，内含 `_ledger.md`（总账/索引）+ 每个 task 一份 `T{NNN}-{slug}.md`（7 段文档）。**正常情况下这些文档已由 `vj-epic-plan` Phase 5 随 plan 生成**——本 Phase 默认直接装载，不重做投影。

1. **定位 work_dir**：从 plan 路径推出 `docs/tasks/work/epic-{N}-{slug}/`。

2. **装载 or 回退生成**（二选一）：

   **2a. work_dir 含 task 文档 + `_ledger.md` → 直接装载（默认路径，快）**
   - 读 `_ledger.md` + 各 `T{NNN}.md`，用平台任务工具建会话内 live 看板（Claude `TaskCreate`/`TaskUpdate`/`TaskList`；Codex `update_plan`），subject 以 T-ID 前缀。
   - **不重新生成、不做过期校验**——信任 plan 阶段产物（plan 是真相源，task 文档是其投影；若 plan 改过，应由 vj-epic-plan 重新生成，不在此补偿）。

   **2b. work_dir 缺失或无 task 文档 → 就地补生成（回退，兼容旧 plan / 未经新版 vj-epic-plan 生成）**
   - 拆 task：默认每个 Implementation Unit 生成 1 个 task（`1 Unit = 1 T{NNN}`），Unit 内执行步骤写入该 task 的 `## 2. Implementation Plan`；只有同步生成 task 级 DAG / 波次 / 共享文件冲突表时才允许把一个 Unit 拆成多个 task。同时建 live 看板。
   - 按 `references/task-doc.template.md` **投影自 plan Appendix C**（Goal/Files/Approach/Patterns/Test scenarios/Verification）逐 task 生成 7 段文档，**不重新发明 HOW**；「变更叙事」段留 `_(待执行)_` 占位。
   - **UI Unit 检测 + Design context 注入**：某 Unit 的 `Files:` 含 `.tsx`、或路径含 `routes/`/`features/`/`components/` → 判为 UI Unit，把模板末尾「附：UI Unit Design context 注入块」原样复制进该文档 `## 3. Technical Approach` 段末。非 UI Unit 不注入。
   - 生成 `_ledger.md`：波次计划 + 每个 task 一行（T-ID / 标题 / 状态 / 波次 / commit）。
   - **这些文档在当前工作树（主分支）生成，不在任何 worktree 里**——是 Review 入口，必须先于代码、集中可见。

> Phase 1 只装载，不审批；审批连同波次计划一起放到 Phase 2。

### Phase 2：展示波次计划 + 审批门（读 ledger/Appendix D，不重算）

波次计划**已由 vj-epic-plan 算好，并已写进 Phase 1 装载的 `_ledger.md`**：§6 给依赖 DAG + 并行结论，`Appendix D` 给并行波次表 + 共享文件冲突点表。本 skill **直接消费、不重算**——与 Phase 1「信任 plan 阶段产物」一致；波次正确性归 `vj-plan-review`（其"依赖并行"视角已在 plan 写盘后审过），不在执行期重算来补 plan 的课。

1. **读并展示波次计划**：取 `_ledger.md` 的波次列（源自 §6/Appendix D）作执行调度，并连同 task 文档一起摆给用户看（哪些波、每波哪些 Unit、`Appendix D` 标出的序列化点直接采纳）；§6 的 DAG / 各 Unit `Depends` 留作**合并顺序与失败影响**参考（回合制收口按依赖序合并；某 Unit 失败时判断哪些后续被阻塞），不用于重算波次。
2. **🔴 CHECKPOINT · 🛑 STOP — 审批门 + 规划提交**（`approval_gate: true` 时）：动代码前**停下，用平台阻塞提问请用户 Review/批准完整蓝图（task 文档 + 波次计划）**——AI 动 worktree 前先看它要做什么、按什么顺序并行。**未获批准不得进入 Phase 3。** 批准后，把 work_dir 下 task 文档 + `_ledger.md`（若尚未提交）作为一个 **docs-only 提交**落在当前分支，再进 Phase 3（执行）。

> **顺序铁律**：task 文档必须先提交到当前分支 → 再开 worktree 写代码。worktree 从已含 task 文档的分支切出，subagent 把它当只读上下文。绝不在 worktree 里才补 task 文档。

> **回退（仅当 plan 无 Appendix D / 无波次，如旧 plan）**：才就地从各 Unit `Files:`（Create+Modify+Test 取交集判冲突）+ `Depends` 拓扑分层补算一次；正常路径不走这里。

> 退化：若波次计划本就是逐 Unit 串行（如 epic-1 的 U1→U2），则无并行波次——这是正确结果，不是缺陷。

### Phase 3：执行

**先识别运行时适配器**：

| 运行时 | 并行执行方式 | 写入隔离 | 降级规则 |
|--------|--------------|----------|----------|
| Claude Code | `Agent` + `run_in_background: true` | `isolation: "worktree"` | 可并行波次必须并行 |
| Codex | `multi_agent_v1.spawn_agent`（若工具暴露） | 仅当子代理具备 forked workspace / disjoint write set 集成能力时视为可隔离 | 无写入隔离时改 serial subagents / inline，并写明 runtime fallback |
| 无 subagent 能力 | 不派代理 | 无 | 串行执行；这不是计划降级，是平台能力缺失 |

**再按波次结构选执行策略**：

| 策略 | 触发条件（**满足即必须用**） | 隔离 |
|------|--------------------------|------|
| **Inline 内联** | 1-2 个小 Unit，或需中途和用户交互的 Unit | 主上下文 |
| **Serial subagents 串行子代理** | 单波只 1 个 Unit；或整条依赖链 ≥3 个串行 Unit（每个派 fresh-context subagent，避免长链退化） | 各自上下文，主分支顺序提交 |
| **⚡ Parallel subagents 并行子代理** | **同一波内 ≥2 个 Unit，且彼此无逻辑依赖、无文件冲突，且运行时具备写入隔离 → 必须并行，不得降级** | 见运行时适配表 |

> **⛔ 红线**：策略选择不是自由裁量。波次计划标明可并行且运行时支持写入隔离 → Phase 3 必须并行。"稳妥""风险""简化"不是降级理由。降级须明确写 runtime fallback：缺 subagent / 缺 forked workspace / 缺 worktree isolation。

**Phase 3 自检（动代码前必过）**：
```
对每个波次：
  若 wave.units.count >= 2 AND 无文件冲突 AND 无逻辑依赖：
    若 runtime 支持 subagent + 独立写入隔离:
      assert strategy == "parallel subagents"  # 否则停止，重新评估
    否则:
      ledger.review_notes += "runtime fallback: <原因>"
```

> **派活前的廉价护栏（可选，defense-in-depth）**：并行派发某一波前，对**该波**的 Unit `Files:` 求交集；若 plan 标称同波不冲突、实际却重叠 → 停下别盲目并行。范围只限那一波、O(读)，不是开工前全量重推；vj-plan-review 已审过依赖并行，这里仅兜底。

按波次推进。**单 Unit（或一波内每个并行 Unit）的执行循环**：

```
标记 in-progress
 → 读该 task 的 7 段文档 `T{NNN}.md`（主 brief：Technical Approach/AC/Affected Components/DoD），先读 Patterns 指向的现有文件照着写，并读本 Unit 要改的**目标文件当前状态**——顺带确认依赖文件存在、且 Unit 尚未被实现（已满足 Verification 就标 skip 不重复造；疑似别的分支/会话已 ship 时先跑一次 Verification 当探针）
 → 若是 UI Unit：先读现有前端 theme / layout / component patterns；读 `docs/project/DESIGN.md`（优先）或 `docs/project/design_guidelines.md`（fallback）；读 epic.md 的 `## 页面体验地图` 对应行和设计稿（如有）；缺设计合同时暂停 UI 实现，给出 Design Read / DESIGN.md 草案而不是自由发挥
 → 若 Execution note = test-first：先写失败测试（确认它失败）再实现
 → 按既有约定实现（信封 / DDD 垂直切片 / UoW / 软删除 等，匹配 plan 复用锚点）
 → 跑该 Unit 的 Verification 命令；失败立即修，**同一 Unit 修复尝试 ≤3 次仍不绿 → 🛑 停下报告用户**（贴最后一次失败输出 + 已试方案），不无限重试、不带病推进、不标 completed
 → 若是 UI Unit：启动/使用前端页面，按桌面和移动视口截图检查视觉验收；发现溢出、重叠、主操作不清晰、关键状态缺失或偏离 `DESIGN.md` 时先修再继续
 → System-Wide 检查：往外追两层——改动触发哪些回调/中间件/事务？是否有真实链路（非全 mock）的集成测试覆盖？失败是否留孤儿状态？
 → 标记 completed → 回写该 task 文档的「变更叙事」段（人话：实际做了什么/怎么满足 AC/权衡/commit）+ 更新 `_ledger.md` 该行状态 → 增量提交（conventional message，包含代码 + 对应 task 文档 + `_ledger.md`）
```

**并行波次的 subagent 调度**（一波 ≥2 个不冲突 Unit 时）：

- **隔离**：每个并行 subagent 必须具备独立写入空间。Claude Code：派 `Agent` 时传 `isolation: "worktree"` + `run_in_background: true`（先确认 `worktree_root` 已在 `.gitignore`）。Codex：仅在 `multi_agent_v1.spawn_agent` 提供 forked workspace / disjoint write set 集成能力时并行；否则退化为串行，并把 runtime fallback 写入 `_ledger.md`。
- **派发内容**：给每个 subagent 传 **① 该 task 的 7 段文档 `T{NNN}.md` 路径（主 brief，自包含）+ ② plan 路径（跨 unit 共享设计、Provides/Consumes）+ ③ `_ledger.md`（波次/依赖感知）**。task 文档已含 Approach/AC/Test/DoD，无需再逐字段拆传；指示它执行前确认测试类别（happy/边界/错误/集成）齐全。
- **task 文档 / `_ledger.md` 归编排器所有**：worktree 从已含 task 文档的主分支切出，subagent 把它当**只读上下文**，**只写代码、不改 task 文档与 ledger**。变更叙事段与 ledger 由**编排器在主树**回写——避免多 worktree 抢改 ledger 冲突，也让 Review 入口始终在当前目录。
- **subagent 返回契约**：subagent 完成后**必须返回一份结构化小结**，作为编排器写「变更叙事」的原料：
  - **实际改动**：实际新建/修改的文件 + 每个文件做了什么（人话）
  - **偏离规格之处 + 为什么**：与 task 文档规格不一致的地方及原因（没有就写"无偏离"）
  - **验证结果**：跑了哪些 Verification 命令、是否全绿（贴关键输出）
  - **遗留 / 风险**：未尽事项、踩到的坑、对后续 task 的影响
  > 编排器**不盲信此小结**：以它 + 实际 diff 交叉核对后再写变更叙事；小结与 diff 不符时以 diff 为准并在叙事里标注。
- **回合制收口**（一波全部完成后）：按**依赖序**逐个把 subagent 分支合并回主分支；每合并一个就跑该 Unit 的 Verification，绿了再由编排器**据 subagent 返回小结 + 实际 diff** 回写该 task 变更叙事段 + ledger，并确保代码与该 task 文档/ledger 同在一个 Unit commit 中。若平台已经产生不可改写的 merge commit，则紧跟一个 `docs: record TNNN execution` 提交；再合下一个。合并后清理 worktree 与分支。
- **不要在波次内并行执行有依赖或文件冲突的 Unit**——它们已被波次计划（§6/Appendix D）分到不同波次。

**⚠️ 失败收口分支（执行期 if-then，不得自由发挥 / 不得静默跳过）**：执行器必须按下表收口，绝不"卡住空转"或"假装成功推进"。

| 触发 | 一线处理 | 仍失败兜底 |
|------|----------|-----------|
| 并行 subagent 报错 / 超时 / 返回空小结 | 带失败上下文重派一次该 Unit（fresh context） | 仍失败 → 该 Unit 标 `blocked`、**不合并其分支**；本波其余成功 Unit 照常收口；🛑 **STOP** 报告用户：列出据 §6 DAG 被它阻塞的下游 Unit，问「修后重试 / 跳过下游 / 中止 epic」 |
| Unit Verification 修 ≤3 次仍不绿 | 见执行循环（贴最后一次失败输出 + 已试方案） | 🛑 **STOP** 问用户，不带病推进、不标 completed |
| 回合制 merge 回主分支冲突 | 先在该 subagent 分支 rebase 当前主分支后重跑 Verification | 仍冲突 → 🛑 **STOP** 报告冲突文件请用户裁决；**禁止 `-X ours/theirs` 盲猜合并** |
| worktree 创建失败 / `worktree_root` 不在 `.gitignore` | 补 `.gitignore` 后重试一次 | 仍失败 → 退化为 serial subagents / inline，并在 `_ledger.md` 写 runtime fallback 原因 |

**边做边简化**：每完成一波或 2-3 个 Unit，回看新改文件做一次去重/抽取/复用整理（子代理各自上下文隔离，看不到跨 Unit 浮现的重复）。早期"看似重复"可能后续有意分叉，别每个 Unit 都简化。

### Phase 4：收尾

1. **全量验证 + Lint**：跑全部 Unit 的 `Verification`（及 plan Appendix E 的整体校验命令）+ 项目 lint，确认全绿。命中 UI/路由变化时按 plan 指示做联调/视觉对齐，并保留桌面/移动截图证据：文本不溢出、元素不重叠、主操作清晰、空态/加载/错误/成功/无权限状态完整、符合 `docs/project/DESIGN.md`（或明确 fallback）。
2. **发布前 code review（优先后台，与步骤 3-5 并行）**：按运行时适配器派一个后台 review 任务（Claude `Agent run_in_background`；Codex `multi_agent_v1.spawn_agent`；无 subagent 能力则在步骤 5 后主上下文同步执行 review）。主 agent 可在后台 review 运行时继续执行步骤 3-5。

   **subagent prompt 模板**：
   > 使用 review skill 审查当前分支相对 main 的完整 diff。返回结构化 findings：① blocking 问题列表（每条：`file:line | 问题描述 | 修复建议`）；② non-blocking 问题列表（同格式）。不要修改任何代码，只输出 findings。

   命中**敏感面**（认证/鉴权、支付、数据迁移、加密/密钥、公共 API 契约、依赖清单）或**大改**（≥400 行且跨多子系统，或 ≥1000 行）时，在 subagent prompt 末尾追加："本次为高风险变更，升级为深度审查，重点检查 Pass 1 全部类别。"

   **review 结果处理**（步骤 3-5 完成后收取 subagent 结果）：
   - **有 blocking 问题**：主 agent 逐条修复，修完后重跑 lint + 受影响 Unit 的 Verification，全绿后继续。
   - **只有 non-blocking**：追加记录到 `_ledger.md` 末尾的"Review notes"段，不阻塞。
   - **无问题**：继续。

   注意：这是**执行后审实际 diff**，与（未来）`vj-plan-review` 审计划是两回事。
3. **完整性核对**：所有 task completed；**逐条核对 plan 的 `Requirements`(R-ID) 已满足**；**`Deferred to Implementation` 的问题已在执行中解决**；对照 `Scope Boundaries` 没越界、没漏交付。
4. **翻转 plan 状态**：plan frontmatter `status: active → completed`（唯一允许的 plan 改动）。
5. **总账收尾**：`_ledger.md` 更新为最终态（每 task 的 commit/验证/跳过原因）——Review 入口；每份 task 文档的「变更叙事」段已逐条回写，是 AI 实际改动的人话逐任务记录。
6. **收尾提交**：若 plan 状态、ledger、task 文档、Review notes 仍有未提交改动，创建最终 docs-only 提交（例：`docs: complete epic N execution ledger`）。收尾后 `git status` 不应留下本 skill 产生的未提交执行记录。
7. **沉淀提示**：若执行中踩了非平凡的坑或定了有理由的取舍，提示用户用 `vj-compound` 沉淀到 `docs/solutions/`，让下次 `vj-epic-plan` 经 `vj-learnings-researcher` 复用。

## 不做什么（边界）

- **不做计划级语义校验**（可行性深审、重复造轮子、风险 R1-R6、更优方案、标准合规、对抗性精修）——那是独立 skill `vj-plan-review` 的职责（剥离自 ln-310），跑在 vj-epic-plan 之后、vj-work 之前。本 skill 不做独立预检——存在性/已完成在 Phase 3 执行循环开工读代码时自然覆盖。
- **不重算波次/依赖**：波次计划由 vj-epic-plan 算（§6/Appendix D）、由 vj-plan-review 审；本 skill 只消费，不重新推导也不覆盖（旧 plan 无波次时才回退补算一次，见 Phase 2）。
- **不重写 AC / 不改 plan 正文 / 不改 epic.md**。
- **默认分支不作为 epic base**——无确认不以默认分支为 base，也不在其上 merge/提交。
