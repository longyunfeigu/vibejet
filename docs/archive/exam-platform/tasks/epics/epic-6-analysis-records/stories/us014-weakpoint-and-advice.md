# Story 6.2 (US014): 薄弱点聚合与学习建议

**用户故事**: 作为系统，我可以按错题关联的知识点聚合薄弱知识点并调用 AI 生成学习建议，以便员工得到针对性的改进方向

#### 验收标准

**Happy Path**
- [ ] 错题按关联知识点聚合为薄弱点（去重，按关联错题数降序），并调 AI 生成针对性学习建议 `验证: API GET /api/v1/exam/results/{submission_id} → data.weak_points[] 按关联错题数降序去重 + data.advice 非空`

**Edge Cases**
- [ ] 无错题 → 无薄弱点（空态），不阻塞成绩展示 `验证: pytest test_no_wrong_questions_yields_empty_weakpoints → PASSED + 成绩仍可展示`

**Error Paths**
- [ ] AI 薄弱点/建议失败或不可解析 → 管理员可手工填写薄弱点与建议，不阻塞成绩/错题展示 `验证: API (mock LLM 失败) GET .../results → 成绩/错题正常返回 + 提供人工填写入口标识; 管理员 PUT 手工建议 → 200`

**Integration**
- [ ] 薄弱点聚合来源固定为错题 questions.knowledge_point_names（名称快照）去重 `验证: pytest test_weakpoints_aggregated_from_wrong_question_kp_snapshot → PASSED`

#### 前端验收标准
- [ ] 分析页展示薄弱点（按错题数降序）与学习建议 `验证: Browser 分析页 → 薄弱点列表降序 + 学习建议文本渲染`
- [ ] AI 失败时展示人工填写薄弱点/建议入口 `验证: Browser AI 失败态 → 人工编辑薄弱点/建议控件存在`

#### Assumptions
- [DEPENDENCY] LLM 能基于薄弱点生成可用学习建议 — Confidence: M — 失效影响: 建议质量差，依赖管理员人工编辑兜底（已覆盖）

**覆盖度自检**: 派生 ✓（EP: 有错题/无错题/AI失败）/ Happy ✓ / Edge ✓ / Error ✓ / Integration ✓ / FE ✓ / AC 总数 4 ≤7 ✓ / Assumptions 1 条
**参考**: docs/project/requirements.md §3 R6.3/R6.4; docs/project/data/question.md（knowledge_point_names 快照）; ⚠️ analysis 持久化为待设计 schema（delta）
**依赖**: Story 6.1
