# US004 · Epic 1

### Story 1.4: 确认保存饮食记录

**用户故事**: 作为记录者，我可以把确认后的识别明细保存为一条饮食记录，以便今日摄入与历史查看有数据可用。

#### 验收标准

**Happy Path**
- [ ] 确认保存后生成一条饮食记录，包含照片引用、菜品明细、记录时间与餐次 `验证: API POST /api/v1/meal-records → 201 + data.record_id exists`
- [ ] 保存的记录字段完整且餐次取值合法，含可聚合的营养快照（Epic 2 今日总览的消费前提） `验证: DB SELECT meal_type, recorded_at, total_calories, total_protein, total_fat, total_carbs FROM meal_records WHERE id=<record_id> → 1 row, meal_type IN ('breakfast','lunch','dinner','snack') 且 4 个 total_* 非 NULL`

**Edge Cases**
- [ ] 重复提交同一确认（双击/网络重试）只产生一条记录 `验证: pytest test_save_meal_record_idempotent → PASSED`
- [ ] 未手动选择餐次时按记录时间给默认值且可修改 `验证: Browser 12:30 进入确认区 → [data-testid=meal-type-select] 默认值为"午餐"且可切换`

**Error Paths**
- [ ] 明细为空时保存被拒绝 `验证: API POST /api/v1/meal-records (items=[]) → 422`
- [ ] 未登录保存被拒绝 `验证: API POST /api/v1/meal-records (无凭证) → 401`

**Integration**
- [ ] 饮食记录 owner-scoped：用户 B 查询用户 A 的记录返回 404（复用既有归属约定） `验证: pytest test_meal_record_ownership_cross_user_404 → PASSED`

#### 前端验收标准
- [ ] 保存成功给出明确反馈并提供"再记一餐"入口 `验证: Browser 保存成功 → [data-testid=save-success] visible 且 [data-testid=record-again] exists`
- [ ] 保存请求期间按钮禁用防重复点击 `验证: Browser 保存请求进行中 → button[data-testid=save-meal] disabled`

#### Assumptions
- [SCOPE] 餐次由用户选择、按时间段给默认值；自动推断算法延后（PRD §11.2 可延后能力） — Confidence: H — 失效影响: 无
- [DATA] 记录时间取保存时刻的本地时间，V1 不支持补记历史时间 — Confidence: M — 失效影响: 晚归漏记的餐会归入错误日期，需后续支持修改记录时间（假设待审批）

**覆盖度自检**: 派生 ✓（EP：明细空/非空、凭证有/无 + 决策表：时间段×餐次默认值 + 幂等并发）/ Happy ✓ / Edge ✓ / Error ✓ / Integration ✓ / FE ✓ / 行为 AC 总数 7 ≤7 ✓ / FE AC 2≤4 ✓ / Assumptions 2 条
**参考**: docs/project/api/conventions.md, docs/project/data/overview.md, docs/reference/research/designs/prd-suishou-shiji/ui-mock-board.html
**依赖**: Story 1.2
