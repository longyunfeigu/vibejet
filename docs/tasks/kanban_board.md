<!--
  Kanban Board — 全局索引文件
  - 由 vj-epic-story skill 自动维护
  - 由 vj-work 在对应 task 完成时回写状态
  - 字段格式严格,grep 可解析,不要手工破坏表格列对齐
-->

# Kanban Board

**项目**: 随手食记
**最后更新**: 2026-07-05

---

## Tracker Configuration

| 字段 | 值 | 说明 |
|------|----|----|
| Next Epic Number | 2 | 下一个 Epic 的序号(创建后 +1) |
| Next Story Number | 6 | 下一个 Story 的全局序号 US{NNN}(跨 Epic 累加) |
| Storage Mode | file | 仅支持 file 模式 |

---

## Epic Story Counters

| Epic | 标题 | 状态 | 优先级 | Story 数 | 路径 |
|------|------|------|--------|---------|------|
| Epic 1 | 拍照记录一餐 | draft | P0 | 5 | epics/epic-1-meal-photo-logging/ |

**状态枚举**: `draft` / `in_progress` / `completed` / `archived`

---

## Story Index

> vj-work 完成对应 task 时把对应行的"状态"列改为 `Done`。
> 新 Story 由 vj-epic-story 在 Phase 5 追加到表尾。

| US 编号 | Epic | 标题 | 状态 | Owner | 文件 |
|---------|------|------|------|-------|------|
| US001 | Epic 1 | 拍摄或上传餐食照片 | Backlog | - | epics/epic-1-meal-photo-logging/stories/us001-meal-photo-upload.md |
| US002 | Epic 1 | AI 识别菜品与营养估算 | Backlog | - | epics/epic-1-meal-photo-logging/stories/us002-ai-recognition.md |
| US003 | Epic 1 | 修正识别明细 | Backlog | - | epics/epic-1-meal-photo-logging/stories/us003-edit-recognition.md |
| US004 | Epic 1 | 确认保存饮食记录 | Backlog | - | epics/epic-1-meal-photo-logging/stories/us004-save-meal-record.md |
| US005 | Epic 1 | 文本补录一餐 | Backlog | - | epics/epic-1-meal-photo-logging/stories/us005-text-fallback-entry.md |

**状态枚举**: `Backlog` / `Todo` / `In Progress` / `To Review` / `Done` / `Canceled`

---

## 使用说明

- 不要手工删除任何 Story 行,改状态即可
- Next Epic Number / Next Story Number 是单向递增,不重用已废弃编号
- 文件路径相对仓库根 `docs/tasks/`
