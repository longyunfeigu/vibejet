# US002 · Epic 1

### Story 1.2: AI 识别菜品与营养估算

**用户故事**: 作为记录者，我可以让系统识别照片中的菜品并估算营养，以便不用手动查库就得到这餐的热量与宏量营养素。

#### 验收标准

**Happy Path**
- [ ] 提交已上传照片发起识别，返回菜品列表，每项含名称、预估份量、热量与蛋白质/脂肪/碳水 `验证: API POST /api/v1/meal-recognitions {photo_id} → 200 + data.items[0].name/portion/calories/protein/fat/carbs exists`
- [ ] 识别端到端（提交 → 结果返回）在正常网络下不超过 10 秒 `验证: pytest test_recognition_completes_within_10s → PASSED`

**Edge Cases**
- [ ] 照片含多道菜时返回多个明细项 `验证: pytest test_recognition_multi_dish_returns_multiple_items → PASSED`
- [ ] 对同一照片重复发起识别各自返回结果，且识别本身不产生饮食记录 `验证: DB SELECT count(*) FROM meal_records → 0 rows`

**Error Paths**
- [ ] 非食物照片或低置信度时返回"无法识别"业务态与原因说明，不返回伪造明细 `验证: API POST /api/v1/meal-recognitions (风景照) → 200 + data.status=unrecognized + data.reason exists`
- [ ] AI 服务超时或 5xx 时返回"服务暂不可用"业务错误，照片保留可稍后重试 `验证: pytest test_recognition_downstream_failure_keeps_photo → PASSED`

**Integration**
- [ ] 识别失败路径不留任何饮食记录/明细残留（无孤儿副作用） `验证: pytest test_recognition_failure_no_side_effects → PASSED`

#### 前端验收标准
- [ ] 识别期间展示识别进行态 `验证: Browser 识别期间 [data-testid=recognizing] → visible`
- [ ] 识别失败态展示原因，并提供"重试"与"文本补录"两个恢复入口 `验证: Browser 模拟识别失败 → [data-testid=retry] 与 [data-testid=text-fallback] exists`
- [ ] 结果就绪时展示明细列表与该餐总热量 `验证: Browser 识别成功 → [data-testid=meal-items] 与 [data-testid=total-calories] visible`

#### Assumptions
- [DEPENDENCY] 多模态 AI 识别服务正常网络下 P95 延迟 ≤8 秒 — Confidence: L — 失效影响: 超时降级成为常态路径，单餐记录耗时超 30 秒目标（PRD §8 高优先验证项）
- [DATA] 营养估算误差 ±20–30% 对"量级感知"目标可接受 — Confidence: M — 失效影响: 用户对数字失去信任，需更换识别服务或引入校准
- [FEASIBILITY] 通用多模态模型可按结构化 schema 稳定返回菜品明细 — Confidence: M — 失效影响: 需加解析兜底或改用专用食物识别 API（PRD §10.3 开放问题，假设待审批）

**覆盖度自检**: 派生 ✓（状态迁移：识别中/成功/无法识别/服务不可用 + 决策表：置信度×服务可用性）/ Happy ✓ / Edge ✓ / Error ✓ / Integration ✓ / FE ✓ / 行为 AC 总数 7 ≤7 ✓ / FE AC 3≤4 ✓ / Assumptions 3 条
**参考**: docs/project/api/conventions.md, docs/project/requirements.md §5.1, docs/reference/research/designs/prd-suishou-shiji/ui-mock-board.html
**依赖**: Story 1.1
