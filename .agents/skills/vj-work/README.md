# vj-work

消费 `vj-epic-plan` 产出的 **epic 实现计划**，把它落地成已实现、已验证、已记录的代码。

## 位置

```text
vj-epic-story (WHAT)
      ↓
vj-epic-plan  (HOW: 实现计划 + task packets——task doc 即执行包 + Epic Checklist)
      ↓
vj-work       (执行: auto/fast/strict + worktree + 并行派发 + Verification + Screen composition)
      ↓
vj-compound   (可选沉淀)
```

## v3 核心

- **task doc 即执行包**：不再生成 `_execution_context.md` 二次蒸馏层。Unit/Task 执行包
  （约束、pattern 指针、Risk/UI class、定向 Verification）由 vj-epic-plan 在 plan-time
  一次做对，写进 `T{NNN}.md` + `task-index.md` 的 Epic Execution Checklist；vj-work 装载
  即派发。mode 判定与执行档案记入 `_ledger.md`。
- **并行默认**：同波次写集无交集的 task 默认 parallel-isolation；相邻小 task 按 Batch 组
  合并派发；依赖链才 serial-isolation（共享 worktree 串行）。
- **冷读瘦身**：subagent 默认读集 = task doc + 注入的 Epic Checklist + 目标文件 + ≤3
  pattern files；guideline / DESIGN.md 全文只按精准指针风险触发展开。
- **审批集中**：参考图前置闸在 Phase 2 一次渲染全部 UI-critical 屏候选、一次审批；
  执行中不逐屏 STOP。
- **验证分层**：task 定向命令 → Unit 收口 `verify.sh {U-ID}` → Phase 4 Epic 全量
  （lint/typecheck/test 只跑一次）；subagent 禁跑全量套件。
- **风险触发质量门**：strict triggers 自动升级；UI 出口闸真相源 = `.claude/rules/frontend.md`，
  UI-critical 屏判定权独立于实现者（orchestrator 看截图或独立 visual-auditor）。

## 文件

- `SKILL.md` — v3 执行工作流（骨架 + 铁律）。
- `references/subagent-dispatch.md` — 派发契约：prompt 字段、return contract、worktree/ingest 规则、合批与 inline 例外。
- `references/ui-execution.md` — UI 执行闸：参考图批量闸、独立视觉审计、cross-screen polish。
- `references/ledger.template.md` — `_ledger.md` 模板（Mode Decision + Status Board + Entries + Final Execution Profile）。
- task 文档模板不在本目录：唯一副本是 `.agents/skills/vj-epic-plan/references/task-doc.template.md`（回退生成时读它）。
- `README.md` — 本文件。
