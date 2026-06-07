# Story 6.1 (US013): 成绩与错题清单

**用户故事**: 作为系统，我可以在整卷终分确定后展示总成绩与错题清单，以便员工知道得了多少分、错在哪些题

#### 验收标准

**Happy Path**
- [ ] 整卷 graded 后展示总成绩（得分/总分）与错题清单（题干、员工作答、正确答案或评分依据） `验证: API GET /api/v1/exam/results/{submission_id} → 200 + data.total_score/data.max_total + data.wrong_questions[] 含 stem/answer/correct_or_rationale`

**Edge Cases**
- [ ] 主观题得分率边界：< 60% 计错题，= 60% 不计错题（硬编码阈值，BVA） `验证: pytest test_wrong_question_threshold_boundary[59%→错,60%→不错,61%→不错] → PASSED`
- [ ] 客观题判错即错题；主观题得分率 ≥ 60% 不计错题 `验证: DB/pytest test_objective_wrong_and_subjective_pass_rule → PASSED`

**Error Paths**
- [ ] 终分未全确定（grading_status != graded）→ 不展示错题清单 `验证: API GET /api/v1/exam/results/{未graded submission} → data.wrong_questions 为空/未就绪标识 + 不报 500`

**Integration**
- [ ] 消费 Epic 5 的 submissions.total_score 与 question_scores 判错题，不重复计算总分 `验证: pytest test_results_consume_grading_total_score → PASSED（total_score 取自 submissions，不再求和重算）`

#### 前端验收标准
- [ ] 结果页展示总成绩与错题列表 `验证: Browser 访问结果页 → 总成绩文案 + 错题列表项渲染`
- [ ] 无错题时显示"全部答对"空态 `验证: Browser 满分卷结果页 → 空态文案存在`

#### Assumptions
- [SCOPE] 错题主观阈值硬编码 60%，不做 per-考试目标 配置（不改 exam_objectives schema） — Confidence: H — 失效影响: 若需每场可配阈值，须加字段 + migration（已与用户确认走硬编码）

**覆盖度自检**: 派生 ✓（BVA: 60% 阈值 59/60/61；决策表: 题型×对错）/ Happy ✓ / Edge ✓ / Error ✓ / Integration ✓ / FE ✓ / AC 总数 5 ≤7 ✓ / Assumptions 1 条
**参考**: docs/project/requirements.md §3 R6.1/R6.2; docs/project/data/grading.md（total_score/graded）; ⚠️ /exam/results/{id} 为待设计端点（delta）
**依赖**: 无（Epic 级依赖 Epic 5）
