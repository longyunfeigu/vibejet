# Story 5.2 (US011): 主观题 AI 评分

**用户故事**: 作为系统，我可以在答卷提交后对主观（简答）题异步调用 AI 评分并输出评分依据，以便管理员据此复核给终分

#### 验收标准

**Happy Path**
- [ ] 后台对主观题 AI 评分，依据评分重点 + 评分要点 + 学员作答 + 题干，落 ai_score + ai_rationale，status=pending_review `验证: API GET /api/v1/exam/submissions/{id}/scores → subjective_scores[].ai_score 非空 + rationale 非空 + status="pending_review"`

**Edge Cases**
- [ ] 空白答案不调 LLM，系统直接给 0 分 + 依据 `验证: DB SELECT FROM question_scores WHERE question_id=空白主观题 → ai_score=0 + ai_rationale 非空, 无 LLM 调用`

**Error Paths**
- [ ] AI 评分失败/不可解析/越界 → 该题保持 pending_manual，不阻塞客观判分与其余主观题 `验证: API GET .../scores (mock LLM 失败一题) → 该题 status="pending_manual"; 其余主观题 status="pending_review" 不受影响`

**Integration**
- [ ] 后台对预创建占位行做 UPDATE（非 INSERT），不撞 UNIQUE；逐题独立软失败隔离 `验证: pytest test_bg_scoring_updates_placeholder_not_insert → PASSED; 单题失败不回滚其余 UPDATE`

#### Assumptions
- [DEPENDENCY] 主观题 AI 评分单题 P95 < 30s（NFR §4.1） — Confidence: M — 失效影响: 评分慢需调超时/并发，前端需进行中状态
- [DEPENDENCY] LLM 输出可经 schema 校验为 {score, rationale} — Confidence: M — 失效影响: 不可解析转 pending_manual（已覆盖）

**覆盖度自检**: 派生 ✓（EP: 作答有效/空白/AI失败类）/ Happy ✓ / Edge ✓ / Error ✓ / Integration ✓ / FE N/A — 后台评分，展示在 Story 5.3 / AC 总数 4 ≤7 ✓ / Assumptions 2 条
**参考**: docs/project/api/grading.md（主观异步评分, 故障分流 R5.4, 评分输入 D4）, docs/project/data/grading.md（状态机, 软失败隔离）
**依赖**: 无（Epic 级依赖 Epic 4；与 5.1 并行）
