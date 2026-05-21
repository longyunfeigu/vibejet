<!--
  Kanban Board — 全局索引文件
  - 由 vj-epic-story skill 自动维护
  - 由 do-story 在 Story 完成时回写状态
  - 字段格式严格,grep 可解析,不要手工破坏表格列对齐
-->

# Kanban Board

**项目**: {{PROJECT_NAME}}
**最后更新**: {{DATE}}

---

## Tracker Configuration

| 字段 | 值 | 说明 |
|------|----|----|
| Next Epic Number | 1 | 下一个 Epic 的序号(创建后 +1) |
| Next Story Number | 1 | 下一个 Story 的全局序号 US{NNN}(跨 Epic 累加) |
| Storage Mode | file | 仅支持 file 模式 |

---

## Epic Story Counters

| Epic | 标题 | 状态 | 优先级 | Story 数 | 路径 |
|------|------|------|--------|---------|------|
| <!-- 示例: Epic 1 | 用户认证 | in_progress | P0 | 5 | epics/epic-1-user-auth/ --> |

**状态枚举**: `draft` / `in_progress` / `completed` / `archived`

---

## Story Index

> do-story 完成 Story 时把对应行的"状态"列改为 `Done`。
> 新 Story 由 vj-epic-story 在 Phase 5 追加到表尾。

| US 编号 | Epic | 标题 | 状态 | Owner | 文件 |
|---------|------|------|------|-------|------|
| <!-- 示例: US001 | Epic 1 | 手机号注册 | Todo | - | epics/epic-1-user-auth/stories/us001-phone-register.md --> |

**状态枚举**: `Backlog` / `Todo` / `In Progress` / `To Review` / `Done` / `Canceled`

---

## 使用说明

- 不要手工删除任何 Story 行,改状态即可
- Next Epic Number / Next Story Number 是单向递增,不重用已废弃编号
- 文件路径相对仓库根 `docs/tasks/`
