# 数据模型 · exam-taking 模块

> 范围：试卷、卷内题、试卷分配、答卷、逐题作答（Epic 4）。
> 全局持久化约定见 [overview.md](./overview.md)。API 契约见 [../api/exam-taking.md](../api/exam-taking.md)。
> 上游：题目来自 [question.md](./question.md)；身份来自 [identity.md](./identity.md)。

## 模块范围

| 聚合 | 表 | Domain 落点 |
|------|----|------------|
| 试卷（Paper） | `papers`、`paper_questions`、`paper_assignments` | `domain/exam_paper/entity.py` |
| 答卷（Submission） | `submissions`、`answers` | `domain/exam_submission/entity.py` |

---

## ERD

```mermaid
erDiagram
    users ||--o{ papers : "created_by(admin)"
    users ||--o{ paper_assignments : "employee_id"
    users ||--o{ submissions : "employee_id"
    questions ||--o{ paper_questions : "question_id"
    questions ||--o{ answers : "question_id"
    papers ||--o{ paper_questions : "paper_id"
    papers ||--o{ paper_assignments : "paper_id"
    papers ||--o{ submissions : "paper_id"
    submissions ||--o{ answers : "submission_id"

    papers {
        int id PK
        int created_by FK,NN "-> users.id(admin, R1.1)"
        int total_score NN "= sum(paper_questions.score)"
        datetime created_at NN
        datetime updated_at
        datetime deleted_at "软删除(SoftDeleteFilterMixin)"
    }
    paper_questions {
        int id PK
        int paper_id FK,NN "-> papers.id"
        int question_id FK,NN "-> questions.id"
        int sort_order NN "题目顺序(R4.1)"
        int score NN "分值快照(R4.1)"
    }
    paper_assignments {
        int id PK
        int paper_id FK,NN "-> papers.id"
        int employee_id FK,NN "-> users.id"
        datetime assigned_at NN
        datetime created_at NN
    }
    submissions {
        int id PK
        int paper_id FK,NN "-> papers.id"
        int employee_id FK,NN "-> users.id(身份关联 R1.1)"
        varchar grading_status NN "default 'pending'; Epic5 接力"
        datetime submitted_at NN
        datetime created_at NN
        datetime updated_at
        datetime deleted_at "软删除"
    }
    answers {
        int id PK
        int submission_id FK,NN "-> submissions.id"
        int question_id FK,NN "-> questions.id"
        text answer_text "nullable=未作答(R4.4)"
        datetime created_at NN
        datetime updated_at
    }
```

---

## 表详情

### `papers`

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| `id` | INT | PK, AUTO | — |
| `created_by` | INT | FK→users.id, NOT NULL | 组卷管理员（R1.1） |
| `total_score` | INT | NOT NULL | = Σ paper_questions.score |
| `created_at` | DATETIME | NOT NULL | TimestampMixin |
| `updated_at` | DATETIME | nullable | TimestampMixin |
| `deleted_at` | DATETIME | nullable | 软删除 |

**索引**：`ix_papers_created_by`

### `paper_questions`

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| `id` | INT | PK, AUTO | — |
| `paper_id` | INT | FK→papers.id, NOT NULL, ON DELETE CASCADE | 所属试卷 |
| `question_id` | INT | FK→questions.id, NOT NULL | 引用题目 |
| `sort_order` | INT | NOT NULL | 卷内题目顺序（R4.1） |
| `score` | INT | NOT NULL | 组卷时分值快照（R4.1） |

**约束**：UNIQUE(`paper_id`, `question_id`)；**索引**：`ix_paper_questions_paper_id`

### `paper_assignments`

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| `id` | INT | PK, AUTO | — |
| `paper_id` | INT | FK→papers.id, NOT NULL, ON DELETE CASCADE | 所属试卷 |
| `employee_id` | INT | FK→users.id, NOT NULL | 被分配员工 |
| `assigned_at` | DATETIME | NOT NULL | 分配时间 |
| `created_at` | DATETIME | NOT NULL | — |

**约束**：UNIQUE(`paper_id`, `employee_id`)（防重复分配）；**索引**：`ix_paper_assignments_paper_id`、`ix_paper_assignments_employee_id`

### `submissions`

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| `id` | INT | PK, AUTO | — |
| `paper_id` | INT | FK→papers.id, NOT NULL | 所属试卷 |
| `employee_id` | INT | FK→users.id, NOT NULL | 作答员工身份（R1.1） |
| `grading_status` | VARCHAR(20) | NOT NULL, default='pending' | Epic 5 阅卷接力位（D3）；Epic 4 只写 'pending' |
| `submitted_at` | DATETIME | NOT NULL | 提交时间 |
| `created_at` | DATETIME | NOT NULL | — |
| `updated_at` | DATETIME | nullable | — |
| `deleted_at` | DATETIME | nullable | 软删除 |

**约束**：UNIQUE(`paper_id`, `employee_id`)（防重复提交 R4.3，并发兜底）；**索引**：`ix_submissions_paper_id`、`ix_submissions_employee_id`

### `answers`

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| `id` | INT | PK, AUTO | — |
| `submission_id` | INT | FK→submissions.id, NOT NULL, ON DELETE CASCADE | 所属答卷 |
| `question_id` | INT | FK→questions.id, NOT NULL | 对应题目 |
| `answer_text` | TEXT | nullable | 员工作答；NULL=未作答（R4.4） |
| `created_at` | DATETIME | NOT NULL | — |
| `updated_at` | DATETIME | nullable | — |

**约束**：UNIQUE(`submission_id`, `question_id`)；**索引**：`ix_answers_submission_id`

---

## 不变量与一致性

- **防重复提交**（R4.3）：`submissions(paper_id, employee_id)` UNIQUE；application 层先查后插 + 捕获 IntegrityError → 409；并发竞态靠唯一约束兜底。
- **答卷关联身份**（R1.1）：`submissions.employee_id` 必须指向 `users.id`，可追溯作答员工。
- **组卷原子性**：`papers` + `paper_questions` + `paper_assignments` 在单个 `SQLAlchemyUnitOfWork` 事务内一次落地。
- **提交原子性**：`submissions` + `answers` 在单事务内一次落地。
- **总分一致**（R4.1）：`papers.total_score = Σ paper_questions.score`（组卷时快照计算）。
- **未作答语义**（R4.4）：`answers.answer_text IS NULL` 表示未作答；判分（客观=0、主观标记"未作答"）由 Epic 5 Story 5.1 实现，**不在本模块**。
- **题目引用快照**：`paper_questions.score` 快照组卷时分值；题目确认后不可编辑（题集须 pending_review 才能改题），快照与实时一致且抗未来变更。

---

## Migration

两个 migration（随 U1 / U2 分次）：

- **U1**（`add_paper_tables`）：`papers` → `paper_questions` → `paper_assignments`（依赖 `users`、`questions`）
- **U2**（`add_submission_tables`）：`submissions` → `answers`（依赖 `papers`、`users`、`questions`）

运行：`cd backend && alembic revision --autogenerate -m "..."` → `alembic upgrade head`

回滚 `alembic downgrade`：按 FK 逆序 drop（`answers` → `submissions` → `paper_assignments`/`paper_questions` → `papers`）

**新模型须在 `infrastructure/models/__init__.py` 导入**（`PaperModel`、`PaperQuestionModel`、`PaperAssignmentModel`、`SubmissionModel`、`AnswerModel`）才能被 Alembic autogenerate 发现。
