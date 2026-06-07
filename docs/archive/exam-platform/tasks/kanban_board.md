<!--
  Kanban Board — 全局索引文件
  - 由 vj-epic-story skill 自动维护
  - 由 do-story 在 Story 完成时回写状态
  - 字段格式严格,grep 可解析,不要手工破坏表格列对齐
-->

# Kanban Board

**项目**: AI 驱动的内部业务考试平台
**最后更新**: 2026-06-05

---

## Tracker Configuration

| 字段 | 值 | 说明 |
|------|----|----|
| Next Epic Number | 7 | 下一个 Epic 的序号(创建后 +1) |
| Next Story Number | 16 | 下一个 Story 的全局序号 US{NNN}(跨 Epic 累加) |
| Storage Mode | file | 仅支持 file 模式 |

---

## Epic Story Counters

| Epic | 标题 | 状态 | 优先级 | Story 数 | 路径 |
|------|------|------|--------|---------|------|
| Epic 1 | 员工身份与登录 | draft | P0 | 2 | epics/epic-1-employee-identity-login.md |
| Epic 2 | 业务知识录入与知识点提取 | draft | P0 | 3 | epics/epic-2-knowledge-ingestion/ |
| Epic 3 | AI 出题与人工审核 | draft | P0 | 2 | epics/epic-3-ai-question-review.md |
| Epic 4 | 组卷与考试作答 | draft | P0 | 2 | epics/epic-4-exam-assembly-taking.md |
| Epic 5 | 自动阅卷与 AI 评分 | draft | P0 | 3 | epics/epic-5-grading/ |
| Epic 6 | 成绩分析、学习建议与记录保存 | draft | P0 | 3 | epics/epic-6-analysis-records/ |

**状态枚举**: `draft` / `in_progress` / `completed` / `archived`

---

## Story Index

> do-story 完成 Story 时把对应行的"状态"列改为 `Done`。
> 新 Story 由 vj-epic-story 在 Phase 5 追加到表尾。

| US 编号 | Epic | 标题 | 状态 | Owner | 文件 |
|---------|------|------|------|-------|------|
| US001 | Epic 1 | 模拟 Lark 登录 | Backlog | - | epics/epic-1-employee-identity-login.md |
| US002 | Epic 1 | 基于角色的访问控制 | Backlog | - | epics/epic-1-employee-identity-login.md |
| US003 | Epic 2 | 录入业务资料 | Backlog | - | epics/epic-2-knowledge-ingestion/stories/us003-input-business-material.md |
| US004 | Epic 2 | 创建考试目标 | Backlog | - | epics/epic-2-knowledge-ingestion/stories/us004-create-exam-objective.md |
| US005 | Epic 2 | AI 知识点提取与确认 | Backlog | - | epics/epic-2-knowledge-ingestion/stories/us005-ai-knowledge-point-extraction.md |
| US006 | Epic 3 | AI 生成结构化题目 | Backlog | - | epics/epic-3-ai-question-review.md |
| US007 | Epic 3 | 题目人工审核与确认 | Backlog | - | epics/epic-3-ai-question-review.md |
| US008 | Epic 4 | 组卷与分配试卷 | Backlog | - | epics/epic-4-exam-assembly-taking.md |
| US009 | Epic 4 | 员工作答与提交 | Backlog | - | epics/epic-4-exam-assembly-taking.md |
| US010 | Epic 5 | 客观题自动判分 | Backlog | - | epics/epic-5-grading/stories/us010-objective-auto-grading.md |
| US011 | Epic 5 | 主观题 AI 评分 | Backlog | - | epics/epic-5-grading/stories/us011-subjective-ai-scoring.md |
| US012 | Epic 5 | 主观题人工复核改终分 | Backlog | - | epics/epic-5-grading/stories/us012-subjective-manual-review.md |
| US013 | Epic 6 | 成绩与错题清单 | Backlog | - | epics/epic-6-analysis-records/stories/us013-score-and-wrong-questions.md |
| US014 | Epic 6 | 薄弱点聚合与学习建议 | Backlog | - | epics/epic-6-analysis-records/stories/us014-weakpoint-and-advice.md |
| US015 | Epic 6 | 记录保存与员工结果查看 | Backlog | - | epics/epic-6-analysis-records/stories/us015-records-and-employee-view.md |

**状态枚举**: `Backlog` / `Todo` / `In Progress` / `To Review` / `Done` / `Canceled`

---

## 使用说明

- 不要手工删除任何 Story 行,改状态即可
- Next Epic Number / Next Story Number 是单向递增,不重用已废弃编号
- 文件路径相对仓库根 `docs/tasks/`
