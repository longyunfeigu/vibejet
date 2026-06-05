# Epics 索引

AI 驱动的内部业务考试平台的 Epic / Story 资产。编号与状态唯一源见 [../kanban_board.md](../kanban_board.md)。
由 `vj-epic-story` 生成；`do-story` 完成 Story 时回写 kanban 状态。

| Epic | 标题 | 优先级 | Story 数 | 结构 | 文件 |
|------|------|--------|---------|------|------|
| 1 | 员工身份与登录 | P0 | 2 | 平铺 | [epic-1-employee-identity-login.md](epic-1-employee-identity-login.md) |
| 2 | 业务知识录入与知识点提取① | P0 | 3 | 展开 | [epic-2-knowledge-ingestion/epic.md](epic-2-knowledge-ingestion/epic.md) |
| 3 | AI 出题与人工审核② | P0 | 2 | 平铺 | [epic-3-ai-question-review.md](epic-3-ai-question-review.md) |
| 4 | 组卷与考试作答 | P0 | 2 | 平铺 | [epic-4-exam-assembly-taking.md](epic-4-exam-assembly-taking.md) |
| 5 | 自动阅卷与 AI 评分③ | P0 | 3 | 展开 | [epic-5-grading/epic.md](epic-5-grading/epic.md) |
| 6 | 成绩分析、学习建议与记录④ | P0 | 3 | 展开 | [epic-6-analysis-records/epic.md](epic-6-analysis-records/epic.md) |

**依赖链**: Epic 1 ← 2 ← 3 ← 4 ← 5 ← 6（单向，MVP 闭环顺序见 PRD §9.1）。

**设计契约**: API 见 [../../project/api/](../../project/api/)，数据模型见 [../../project/data/](../../project/data/)。
Epic 6（分析/记录）尚无 api/data 模块，其端点与表为 `vj-epic-plan` 待设计的 delta。
