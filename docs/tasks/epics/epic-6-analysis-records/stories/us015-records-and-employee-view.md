# Story 6.3 (US015): 记录保存与员工结果查看

**用户故事**: 作为员工考生，我可以在分析结果经管理员确认后查看本人的成绩、错题、薄弱点与学习建议，以便回顾本次考试；作为系统，须持久化记录并隔离他人数据

#### 验收标准

**Happy Path**
- [ ] 管理员确认薄弱点与学习建议后持久化，分析对员工可见 `验证: API PUT /api/v1/exam/results/{submission_id}/confirm (admin) → 200 + data.confirmed=true; DB analysis 记录 confirmed=true`
- [ ] 员工查看本人结果展示成绩/错题/薄弱点/学习建议 `验证: API GET /api/v1/exam/my/results (employee Cookie) → 200 + data 含 score/wrong_questions/weak_points/advice`

**Edge Cases**
- [ ] 分析未确认时，员工结果页不显示分析（薄弱点/建议） `验证: API GET /api/v1/exam/my/results (分析未确认) → data 不含 weak_points/advice 或标记未就绪`

**Error Paths**
- [ ] 员工访问他人记录 → 拒绝/不展示（数据边界） `验证: API GET /api/v1/exam/results/{他人submission_id} (employee Cookie) → 403 或不返回他人数据`

**Integration**
- [ ] 每次考试记录（成绩/逐题作答/各题得分/AI 评分与依据及人工终分/薄弱点/建议）持久化并关联员工身份，可重看 `验证: pytest test_exam_record_persisted_and_reviewable_by_owner → PASSED（重新 GET 仍返回完整记录, 关联 employee_id）`

#### 前端验收标准
- [ ] 员工结果页展示本人完整结果；未确认分析时显示"分析待出"空态 `验证: Browser 员工结果页 → 成绩/错题渲染; 未确认分析 → 分析区空态文案`
- [ ] 员工无法访问他人结果 `验证: Browser employee 访问他人 results URL → 拒绝/跳转, 不渲染他人数据`

#### Assumptions
- 无

**覆盖度自检**: 派生 ✓（决策表: 确认状态×访问者身份）/ Happy ✓ / Edge ✓ / Error ✓ / Integration ✓ / FE ✓ / AC 总数 5 ≤7 ✓ / Assumptions "无"
**参考**: docs/project/requirements.md §3 R6.5/R6.6; docs/project/api/conventions.md（/exam/my/results 预告, 数据可见性边界）; ⚠️ analysis 端点/表为待设计 delta
**依赖**: Story 6.1, Story 6.2
