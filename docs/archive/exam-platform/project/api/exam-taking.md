# API · exam-taking 模块

> 范围：组卷与分配试卷、员工作答与一次性提交（幂等防重复）（Epic 4）。
> 全局约定见 [conventions.md](./conventions.md)。数据模型见 [../data/exam-taking.md](../data/exam-taking.md)。
> 上游：题目来自 [question.md](./question.md)（`status=confirmed` 题集）；身份/鉴权见 [identity.md](./identity.md)。
> 响应体均为统一信封，下表「Response」列描述 `data` 内结构。

## 权限

- 组卷 / 查看试卷（管理员视图）/ 员工列表：`Depends(require_admin)`
- 作答取卷 / 提交 / 我的试卷：`Depends(require_employee)`，且仅限分配给本人的试卷（未分配 → 403 FORBIDDEN）

---

## 组卷与分配（Papers）

### POST /api/v1/exam/papers

管理员用已确认题目组卷并分配给员工。单事务内落试卷 + 卷内题（顺序/分值快照）+ N 条分配。

- **Auth**：`require_admin`
- **Request**：`{ "question_ids": [int], "assignees": [int] }`
  - `question_ids`：按数组顺序确定题目顺序（`sort_order`）；每个 question_id 必须各自属于某个 `status=confirmed` 题集（允许跨题集混合组卷），列表非空
  - `assignees`：员工 `users.id` 列表（role=employee）
- **Response 201**（`data`）：`{ "paper_id": int, "order": [int], "total_score": int, "assignments": [{ "employee_id": int }] }`
  - `order`：题目 id 按 `sort_order` 排列；`total_score = Σ paper_questions.score`
- **错误**：
  - 题目含未确认题集 / 空题集 / question_id 不存在 → **422** `PAPER_INVALID_QUESTIONS`
  - 缺字段 / 类型错 → **422** `PARAM_VALIDATION_ERROR`

### GET /api/v1/exam/papers/{id}

取试卷及题目。**员工视图剥离答案**（不返回 `reference_answer`/`scoring_points`，且每个 `options` 项剥离正确性标记 `is_correct`，仅保留 `key`/`text`）；管理员可取完整。

- **Auth**：`require_employee`（须在该卷 `paper_assignments` 中，否则 403）；admin 亦可
- **Response 200**（`data`）：`{ "paper_id": int, "total_score": int, "questions": [{ "id": int, "type": str, "stem": str, "options": [{ "key": str, "text": str }]|null, "score": int, "sort_order": int }] }`
  - 题目按 `sort_order` 升序；员工视图**不含** `reference_answer`/`scoring_points`；`options` 仅含 `key`/`text`（**不含** `is_correct`，防答案泄漏 D2）。注：`questions.options` 在 epic-3 题库中存为 `{key,text,is_correct}`，员工视图必须剥离 `is_correct`
- **错误**：
  - 试卷不存在 → **404** `PAPER_NOT_FOUND`
  - 员工未被分配该卷 → **403** `FORBIDDEN`

### POST /api/v1/exam/papers/{id}/submit

员工一次性提交答卷。单事务建答卷 + 逐题作答；同员工同卷仅一次成功（幂等）。

- **Auth**：`require_employee`（须被分配该卷）
- **Request**：`{ "answers": [{ "question_id": int, "answer": str|null }] }`
  - 缺失或 `answer=null` 的题视为未作答，以 `answer_text=NULL` 落库（R4.4）
- **Response 201**（`data`）：`{ "submission_id": int, "user_id": int, "paper_id": int, "submitted_at": str, "unanswered": [int] }`
  - `unanswered`：未作答的 question_id 列表
  - 提交成功后 `submissions.grading_status='pending'`，供 Epic 5 阅卷接力
- **错误**：
  - 同员工对同卷重复提交 → **409** `DUPLICATE_SUBMISSION`（R4.3；并发由 DB 唯一约束兜底）
  - 员工未被分配该卷 → **403** `FORBIDDEN`
  - 试卷不存在 → **404** `PAPER_NOT_FOUND`
  - `answers` 含不属本卷的 question_id → **422** `PARAM_VALIDATION_ERROR`

---

## 辅助查询

### GET /api/v1/exam/employees

列出可分配的员工（供组卷页选考生）。

- **Auth**：`require_admin`
- **Response 200**（`data`）：`{ "items": [{ "id": int, "name": str, "email": str }] }`（role=employee）

### GET /api/v1/exam/my/papers

列出分配给当前员工的试卷（供员工进入作答）。

- **Auth**：`require_employee`
- **Response 200**（`data`）：`{ "items": [{ "paper_id": int, "total_score": int, "submitted": bool }] }`
  - `submitted`：当前员工是否已对该卷提交

---

## 错误码（本模块新增）

> 码值挂 6xxxx 段；实现时与 `backend/shared/codes/` 现有占用核对。

| 码 | 名称 | HTTP | 触发 |
|----|------|------|------|
| 60030 | `PAPER_NOT_FOUND` | 404 | `paper_id` 不存在 |
| 60031 | `PAPER_INVALID_QUESTIONS` | 422 | 组卷题目含未确认/空题集/不存在题 |
| 60032 | `DUPLICATE_SUBMISSION` | 409 | 同员工对同卷重复提交（R4.3） |

复用：`UNAUTHORIZED`(30001/401)、`FORBIDDEN`(30002/403，非 admin/未分配)、`PARAM_VALIDATION_ERROR`(10003/422)。
