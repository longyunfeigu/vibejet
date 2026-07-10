# Subagent 派发契约（vj-work Phase 3）

> SKILL.md 定骨架，本文件是派发的完整技术契约：prompt 必含字段、return contract、
> worktree / ingest 规则、合批与 inline 例外。

## Prompt 必含字段（所有 task）

- review pack 目录 path（只按 anchors 回读，不全读）。
- task doc path + `task-index.md` path。
- Unit ID / Task ID、task scope（barrier | owner | capability | screen | integration）。
- **Epic Execution Checklist 原文**（从 task-index 复制注入 prompt，不是只给路径）。
- write scope：允许修改路径 + Do not modify（照抄 task doc）。
- 默认读集声明：task doc 全文 + 目标文件 + ≤3 个 pattern files；guideline / DESIGN.md
  全文**不在默认读集**，只按 task doc Read first 的精准指针、或碰到清单外风险面时展开对应小节。
- Verification 命令（定向，只跑本 task 触碰面；**禁跑全量套件**）+ Unit 收口 task 的
  `bash verify.sh {U-ID}`。
- plan anchors / catalog anchors / stop conditions（照抄 task doc）。
- return contract（见下）。

即使运行时支持 `fork_context` / isolation 继承上下文，也必须显式传以上字段；
父 agent 的隐式理解不算执行合同。

## UI task 追加字段

- Screen context 注入块整体照抄 task doc：Screen ID / Route / Screen type / Primary Job /
  Covered Units / Regions / Information priority / Richness floor / Forbidden patterns /
  API-for-UI / Screen done / 同屏 sibling Units。
- 所属 app shell + 全局导航契约（source: `DESIGN.md` §Layout / 共享 layout 组件）——
  告知子代理该屏套在哪个外壳、复用哪个共享 layout，不得自造导航 frame。
- Reference image 路径（Phase 2 批量闸已批准；有则必传）：实现目标 = 复刻该图 + 接真实数据，
  再按 Screen Contract 补交互与状态，不是照散文自由发挥。
- 出口闸轨道声明：front-of-house = `.claude/rules/frontend.md` A 轨；operational = B 轨。
  并注明：自评 "passes" 不构成过闸，独立判定由 orchestrator 侧执行。

## Batch dispatch（多 task 一次派发）

- 条件：task-index 的 Batch 列同组；或执行期发现相邻小 task 满足——同 lane、
  写集无交集或完全共享、预计合计 diff <300 行、共享 pattern files。
- prompt 按依赖顺序列出每个 task 的完整字段；要求逐 task 跑各自 Verification、
  逐 task 返回独立小结条目。
- Unit 验收边界不变：合批只合并派发开销，不合并 done signal。

## Return contract（结构化小结，orchestrator 唯一 ingest 面）

- changed files。
- verification commands + 结果（合批时逐 task）。
- deviations from task packet（含原因；无则"无"）。
- risks / blockers。
- UI task 另附：截图文件路径（桌面必须）+ Screen Contract 覆盖情况
  （Primary Job / Regions / Key States / API-for-UI / Screen done）。

## worktree / ingest 规则

- **serial-isolation**：依赖型 / 共享文件 / owner task 的 subagent 在 orchestrator 当前
  执行 worktree 内工作（cwd 即该 worktree），**不传 `isolation: worktree`**——否则下游
  看不到上游已落盘代码。上游返回并（strict 下）commit 后再派下游，下游 prompt 注明
  "上游 task 已完成、读已落盘状态"。
- **parallel-isolation**：仅无依赖 + 冲突表写集无交集的同波次 task；各自
  `isolation: worktree`，完成后按 Task DAG merge 回执行分支。
- orchestrator 只消费 return contract 小结，**绝不 Read 子代理 transcript / `.output`**
  （完整对话 JSONL 会撑爆主上下文）。例外：UI-critical 屏的截图 artifact 必须亲自 Read
  （轻量 PNG）或派独立 visual-auditor——不得仅凭小结文字 "passes" 就 commit UI 屏
  （协议见 `ui-execution.md`）。
- subagent 内部跑 Task Loop（实现 + Verification），return 变更叙事素材；orchestrator 负责
  append `_ledger.md`（strict 逐 task、fast 收尾统一）、commit（子代理未提交时）、
  review gate、跨 task / Unit 编排。

## inline 执行（不派 subagent 的三种例外，须在 ledger 记录原因）

- 运行时 / 平台不支持 subagent 或 Task 工具。
- task trivial（派发 + ingest 开销 > 收益）：纯配置、单文件小改、纯文案。
- orchestrator 已完整持有该 task 精确上下文且实现过半（中途转交浪费已加载上下文）。

这是正常策略，不是失败。
