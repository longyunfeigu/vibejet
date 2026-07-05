---
title: "Epic {N} {name} Review Entry"
type: epic-review-pack-readme
status: active
date: YYYY-MM-DD
epic_id: "{N}"
epic_source: docs/tasks/epics/epic-{N}-{slug}/epic.md
execution_policy: "fast | strict"
---

# Epic {N} {name} Review Entry

这份 README 是 human reviewer 的入口。它只帮助人快速判断“我要审什么、先看哪里、哪些地方还冲突”。不要把 task 文件清单、逐步实现细节或完整 catalog 内容塞进这里。

## 1. One-Screen Summary

- **本 Epic 解决的问题**：
- **本 Epic 不解决的问题**：
- **设计主文档**：[design.md](design.md)
- **决策真相源**：[decisions.md](decisions.md)
- **执行入口**：`docs/tasks/work/epic-{N}-{slug}/task-index.md`
- **catalog touched**：API / Data / UI = yes/no
- **execution policy**：fast / strict

## 2. Known Conflicts

> 如果 story / review pack / catalog / 当前代码基线互相冲突，先列在这里。不要静默选一个覆盖另一个。无则写“无”。

| Conflict | Where it appears | Adopted review stance | Required follow-up |
|----------|------------------|-----------------------|--------------------|
| | | | |

## 3. Reviewer Reading Path

1. 先看 `Known Conflicts`，确认哪些偏离已经批准，哪些还要问。
2. 看 [design.md](design.md) 的 Problem Model、Target Architecture（模块小节）、Core Flows、Delta（API/Data/UI）。
3. 看 [decisions.md](decisions.md) 的 D/ACD，确认范围偏离和 rejected alternatives 是否合理。
4. 只在需要核对执行编排时看 `docs/tasks/work/epic-{N}-{slug}/task-index.md`。

## 4. Execution Sketch

> 只写能帮助 reviewer 理解顺序的高层路线。详细 Unit/Task DAG、共享文件冲突、done signal 在 task-index.md。

- Barrier：
- 可并行：
- 收口：
- Required gates：

## 5. Catalog Sync

| Area | Files | Status |
|------|-------|--------|
| API | | pending / synced / N/A |
| Data | | pending / synced / N/A |
| UI | | pending / synced / N/A |

## 6. Open Review Questions

| ID | Question | Why it matters | Owner |
|----|----------|----------------|-------|
| | | | |
