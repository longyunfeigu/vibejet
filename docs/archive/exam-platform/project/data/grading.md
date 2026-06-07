# 数据模型 · grading 模块

> 范围：每题得分记录 + 复核状态机（Epic 5）。
> 全局持久化约定见 [overview.md](./overview.md)。API 契约见 [../api/grading.md](../api/grading.md)。
> 上游：答卷来自 [exam-taking.md](./exam-taking.md)（`submissions`/`answers`）；题目来自 [question.md](./question.md)；身份来自 [identity.md](./identity.md)。

## 模块范围

| 聚合 | 表 | Domain 落点 |
|------|----|------------|
| 题目得分（QuestionScore） | `question_scores` | `domain/exam_grading/entity.py` |

> 另在 exam-taking 的 `submissions` 上**增列** `total_score`，并扩展 `grading_status` 的取值（见下）。

---

## ERD

```mermaid
erDiagram
    submissions ||--o{ question_scores : "每题一行得分"
    questions ||--o{ question_scores : "评分引用题目"
    users ||--o{ question_scores : "reviewed_by(复核人)"

    submissions {
        int id PK
        varchar grading_status NN "pending|grading|review_pending|graded (Epic5 扩展)"
        int total_score "Σ final_score; 仅 graded 时非空(ACD1)"
    }
    question_scores {
        int id PK
        int submission_id FK,NN "-> submissions.id ON DELETE CASCADE"
        int question_id FK,NN "-> questions.id"
        varchar question_type NN "single_choice|true_false|short_answer 快照"
        int max_score NN "paper_questions.score 快照(D5); 改分上界"
        int auto_score "客观自动判分; nullable"
        int ai_score "主观 AI 给分; nullable; 不被人工覆盖(R5.3)"
        text ai_rationale "AI 评分依据; nullable; 保留(R5.3)"
        int manual_score "人工改分/给分; nullable"
        int final_score "终分; nullable until 确定"
        varchar status NN "final|pending_review|pending_manual|needs_manual"
        int reviewed_by FK "-> users.id; nullable"
        datetime reviewed_at "nullable"
        datetime created_at NN
        datetime updated_at
        datetime deleted_at "软删除(沿用基类)"
    }
```

---

## 表详情

### `question_scores`

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| `id` | INT | PK, AUTO | — |
| `submission_id` | INT | FK→submissions.id, NOT NULL, ON DELETE CASCADE | 所属答卷；随答卷级联删除 |
| `question_id` | INT | FK→questions.id, NOT NULL | 对应题目 |
| `question_type` | VARCHAR(20) | NOT NULL | 题型快照（路由客观/主观 + 展示） |
| `max_score` | INT | NOT NULL | `paper_questions.score` 卷内分值快照（D5）；改分上界 |
| `auto_score` | INT | nullable | 客观题自动判分结果 |
| `ai_score` | INT | nullable | 主观题 AI 给分；人工改分时**不覆盖**（R5.3） |
| `ai_rationale` | TEXT | nullable | 主观题 AI 评分依据；**保留**（R5.3） |
| `manual_score` | INT | nullable | 人工改分 / 人工给分 |
| `final_score` | INT | nullable | 终分；未确定前为 NULL |
| `status` | VARCHAR(20) | NOT NULL | `final` / `pending_review` / `pending_manual` / `needs_manual` |
| `reviewed_by` | INT | FK→users.id, nullable | 复核管理员（R1.1 可追溯） |
| `reviewed_at` | DATETIME | nullable | 复核时间 |
| `created_at` | DATETIME | NOT NULL | TimestampMixin |
| `updated_at` | DATETIME | nullable | TimestampMixin |
| `deleted_at` | DATETIME | nullable | 软删除（沿用基类，无业务软删需求） |

**约束**：UNIQUE(`submission_id`, `question_id`)（一题一得分行，防重复落库）；**索引**：`ix_question_scores_submission_id`

### `submissions`（本模块增量）

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| `total_score` | INT | nullable | **新增列**：最简总分 Σ final_score；仅 `grading_status='graded'` 时写入（ACD1） |
| `grading_status` | VARCHAR(20) | NOT NULL | **取值扩展**（无 DDL）：`pending`(Epic4) → `grading` → `review_pending` → `graded` |

---

## 状态机

**`question_scores.status`**（逐题）：
- 提交同步步骤为全部卷内题**预创建**行（D6）：客观题即时判分 → `final`（缺 `reference_answer` 数据异常 → `needs_manual`，S5.1 Error，不崩溃）；主观题先落 `pending_manual` 占位。
- 主观 AI 评分（bg）对占位行 **UPDATE**：AI 成功 / 空白答案系统给分 → `pending_review`；AI 失败 / 不可解析 / 越界 → 保持 `pending_manual`（R5.4，不阻塞其余）。
- 人工复核（确认 / 改分 / 人工给分）后 → `final`（`needs_manual` 与 `pending_manual` 均经 `manual` 动作定终分）。

**`submissions.grading_status`**（整卷）：
- `pending`（Epic 4 提交时写）
- `grading`（客观已判，主观 AI 评分进行中）
- `review_pending`（AI 评分完成，待人工复核主观题）
- `graded`（全部题 `final`，已算 `total_score`）

---

## 不变量与一致性

- **保留 AI 原始**（R5.3）：`adjust`/`manual` 写 `manual_score`/`final_score`，**不修改** `ai_score`/`ai_rationale`。
- **判分满分基准**（D5）：`max_score` 取 `paper_questions.score` 快照，非 `questions.score`；改分范围校验上界即此值。
- **一题一行**：UNIQUE(`submission_id`,`question_id`) 兜底重复落库；bg 重触发须 skip/upsert 已存在行。
- **软失败隔离**（R5.4）：主观题逐题独立 UPDATE，单题 AI 失败保持 `pending_manual` 不影响客观行与其余主观题。
- **恢复保证**（D6）：主观行在提交时已预创建，bg 失败/进程重启不会留下"无行"主观题；停在 `pending_manual` 的行由管理员 `manual` 给分兜底。bg 重跑对行做 UPDATE 而非 INSERT，不撞 UNIQUE。
- **终分触发总分**（ACD1）：某 submission 全部 `question_scores` 转 `final` 时，算 `total_score = Σ final_score` 并**条件更新**置 `grading_status='graded'`（`WHERE grading_status != 'graded'`，并发只翻转一次）。
- **可追溯**（R1.1）：`question_scores` → `submission_id` → `submissions.employee_id` → `users.id`。

---

## Migration

单条 migration（随 U1）：

- 建 `question_scores` 表（依赖 `submissions`、`questions`、`users`）
- `submissions` 增列 `total_score INT nullable`

`down_revision = 'c2d3e4f5a6b7'`（当前唯一 head：`add_question_source_quote`）。

运行：`cd backend && alembic revision --autogenerate -m "add question_scores"` → `alembic upgrade head`
回滚 `alembic downgrade -1`：drop `question_scores` + drop `submissions.total_score`。

**新模型须在 `infrastructure/models/__init__.py` 导入**（`QuestionScoreModel`）才能被 Alembic autogenerate 发现。
