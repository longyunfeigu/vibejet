# Story 5.1 (US010): 客观题自动判分

**用户故事**: 作为系统，我可以在员工提交答卷时对客观题（单选/判断）按参考答案自动判分，以便客观成绩即时确定且为主观评分预备得分行

#### 验收标准

**Happy Path**
- [ ] 提交时同步对客观题按 reference_answer 判分，落 question_scores.auto_score，status=final `验证: API POST /api/v1/exam/papers/{id}/submit → 201; DB SELECT FROM question_scores WHERE submission_id=X AND question_type IN('single_choice','true_false') → auto_score 已填, status="final"`

**Edge Cases**
- [ ] 未作答客观题（answer_text NULL）→ 计 0 分 `验证: DB SELECT auto_score FROM question_scores WHERE question_id=未作答客观题 → auto_score=0, status="final"`

**Error Paths**
- [ ] 客观题缺 reference_answer（数据异常）→ 该题 needs_manual，不崩溃，复核页可见 `验证: API GET /api/v1/exam/submissions/{id}/scores → objective_scores 含 status="needs_manual" 项; 提交未抛 500`

**Integration**
- [ ] 提交同步步骤预创建全部卷内题 question_scores 行（主观题先 pending_manual 占位），保证 bg 失败/重启不留"无行"主观题 `验证: pytest test_submit_precreates_all_question_score_rows → PASSED; DB COUNT(question_scores WHERE submission_id=X) == 卷内题数`

#### Assumptions
- [DATA] 客观题（单选/判断）在 Epic 3 出题时必带 reference_answer — Confidence: M — 失效影响: 缺答案题落 needs_manual，需管理员 manual 兜底（已覆盖）

**覆盖度自检**: 派生 ✓（决策表: 题型×是否作答×有无参考答案）/ Happy ✓ / Edge ✓ / Error ✓ / Integration ✓ / FE N/A — 纯后端判分，结果展示在 Story 5.3 复核页 / AC 总数 4 ≤7 ✓ / Assumptions 1 条
**参考**: docs/project/api/grading.md（评分触发, GET scores）, docs/project/data/grading.md（question_scores 预创建 D6, 状态机）
**依赖**: 无（Epic 级依赖 Epic 4）
