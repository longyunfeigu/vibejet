# API · grading 模块

> 范围：客观题自动判分、主观题 AI 评分（环节③）、主观题人工复核改终分（Epic 5）。
> 全局约定见 [conventions.md](./conventions.md)。数据模型见 [../data/grading.md](../data/grading.md)。
> 上游：答卷来自 [exam-taking.md](./exam-taking.md)（`submissions`/`answers`，`grading_status='pending'` 接力位）；题目来自 [question.md](./question.md)；评分重点来自 [exam.md](./exam.md)（`exam_objectives.subjective_scoring_focus`）；身份/鉴权见 [identity.md](./identity.md)。
> 响应体均为统一信封，下表「Response」列描述 `data` 内结构。

## 权限

- 读分 / 复核：`Depends(require_admin)`（仅出题管理员）。

## 评分触发（无独立端点）

判分由提交端点 [`POST /api/v1/exam/papers/{id}/submit`](./exam-taking.md) 接力触发，**提交契约响应体不变**：
- 客观题（单选/判断）在提交请求内**同步**判分，即时落 `question_scores`（D1）。
- 主观题（简答）由 FastAPI **BackgroundTasks 异步** AI 评分（D1）；提交立即返回 201，分数随后落库，经下方 `GET …/scores` 读取。

---

## GET /api/v1/exam/submissions/{submission_id}/scores

读取某答卷的全部题得分（供管理员复核页 + 主观评分验收）。

- **Auth**：`require_admin`
- **Response 200**（`data`）：
  ```json
  {
    "submission_id": 1,
    "grading_status": "review_pending",
    "total_score": null,
    "objective_scores": [
      { "question_score_id": 10, "question_id": 100, "auto_score": 5, "final_score": 5, "max_score": 5, "status": "final" }
    ],
    "subjective_scores": [
      { "question_score_id": 11, "question_id": 101, "stem": "…", "ai_score": 7, "rationale": "…", "manual_score": null, "final_score": null, "max_score": 10, "status": "pending_review" }
    ]
  }
  ```
  - `grading_status ∈ {pending, grading, review_pending, graded}`；`total_score` 仅在 `graded` 时非空（= Σ final_score）。
  - `subjective_scores[].{ai_score, rationale}` 满足 R5.2 验收；AI 失败题 `status='pending_manual'` 且 `ai_score/rationale` 可为空。
  - `objective_scores[]` 也带 `status`：缺参考答案的客观题为 `needs_manual`，须在复核页可见并经 `manual` 动作定终分（D6）。
- **错误**：
  - `submission_id` 不存在 → **404** `SUBMISSION_NOT_FOUND`

## PUT /api/v1/exam/question-scores/{id}/review

管理员复核某题得分并定终分。保留 AI 原始给分与依据（R5.3）。

- **Auth**：`require_admin`
- **Request**：`{ "action": "confirm" | "adjust" | "manual", "score": int? }`
  - `confirm`：采纳 AI 分（`pending_review` → `final`，`final_score = ai_score`）。
  - `adjust`：改分覆盖（`pending_review` → `final`，`manual_score = final_score = score`，**保留** `ai_score`/`rationale`）；须带 `score`。
  - `manual`：对 AI 失败题（`pending_manual`）或缺答案客观题（`needs_manual`）人工给分（→ `final`，`final_score = score`）；须带 `score`。
- **Response 200**（`data`）：`{ "question_score_id": int, "final_score": int, "status": "final" }`
  - 若该 submission 全部 `question_scores` 转 `final`：同步算 `submissions.total_score = Σ final_score` 并置 `grading_status='graded'`（ACD1 触发成绩计算）。
- **错误**：
  - `id` 不存在 → **404** `QUESTION_SCORE_NOT_FOUND`
  - `score` 超出 `[0, max_score]` → **422** `SCORE_OUT_OF_RANGE`
  - `action` 非法 / `adjust`·`manual` 缺 `score` → **422** `INVALID_REVIEW_ACTION`

---

## 错误码（本模块新增）

> 码值挂 6xxxx 段；避开 question(60020-60023) 与 exam-taking(60030-60032)。

| 码 | 名称 | HTTP | 触发 |
|----|------|------|------|
| 60040 | `SUBMISSION_NOT_FOUND` | 404 | `submission_id` 不存在（读分） |
| 60041 | `QUESTION_SCORE_NOT_FOUND` | 404 | `question_score_id` 不存在（复核） |
| 60042 | `SCORE_OUT_OF_RANGE` | 422 | 改分超出 `[0, max_score]`（R5.3） |
| 60043 | `INVALID_REVIEW_ACTION` | 422 | `action` 非法或缺必需 `score` |

复用：`UNAUTHORIZED`(30001/401)、`FORBIDDEN`(30002/403，非 admin)、`PARAM_VALIDATION_ERROR`(10003/422)。

---

## 备注

- 评分输入：主观题 AI 评分喂入 `exam_objectives.subjective_scoring_focus`（考试目标级评分重点）+ `questions.scoring_points`（题目级评分要点）+ 学员 `answer_text` + `questions.stem`（D4）。空白答案不调 LLM，系统直接给 0 分 + 依据。
- 故障分流：复用 `LLMPort.generate_structured`；`LLMUnavailableError` / 不可解析 / 越界 → 该题 `pending_manual`，不阻塞客观判分与其余主观题（R5.4）。
- 满分基准：`max_score` 取 `paper_questions.score` 卷内分值快照（D5），改分上界即此值。
