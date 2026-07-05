# US005 · Epic 1

### Story 1.5: 文本补录一餐

**用户故事**: 作为记录者，我可以在照片识别失败或服务不可用时用一句话描述这餐，以便这餐不会因为 AI 失败而漏记。

#### 验收标准

**Happy Path**
- [ ] 在识别失败态输入文本描述（如"牛肉面一碗"）发起补录，返回估算明细并进入与拍照相同的确认流程 `验证: API POST /api/v1/meal-recognitions {text} → 200 + data.items[0].calories exists`

**Edge Cases**
- [ ] 空文本无法提交 `验证: Browser 文本为空 → button[data-testid=submit-text] disabled`
- [ ] 超过 200 字的文本被拒绝并提示精简描述 `验证: API POST /api/v1/meal-recognitions (201字文本) → 422`

**Error Paths**
- [ ] 文本补录时 AI 服务不可用，提示稍后重试且已输入文本保留 `验证: Browser 模拟服务失败提交 → 错误提示可见且 textarea 值不变`

**Integration**
- [ ] 文本补录产生的明细走同一确认/保存链路，保存后记录与拍照记录同构可被聚合查询 `验证: pytest test_text_fallback_record_same_shape_as_photo_record → PASSED`

#### 前端验收标准
- [ ] 文本补录仅作为失败态的兜底入口，默认记录页不展示文本输入框 `验证: Browser 默认打开 /record → 无 [data-testid=text-fallback-input]；识别失败态 → [data-testid=text-fallback] exists`

#### Assumptions
- [FEASIBILITY] 文本描述与照片走同一 AI 估算通道（多模态模型可接受纯文本输入） — Confidence: M — 失效影响: 纯文本估算质量过差时需引入食物库映射，超出 V1 范围（假设待审批）
- [SCOPE] 文本补录仅在识别失败/服务不可用后可用，不作为一等录入方式（PRD §4 R3） — Confidence: H — 失效影响: 无

**覆盖度自检**: 派生 ✓（EP：文本空/正常/超长 + 单 Story 流程走查：失败态→补录→确认）/ Happy ✓ / Edge ✓ / Error ✓ / Integration ✓ / FE ✓ / 行为 AC 总数 5 ≤7 ✓ / FE AC 1≤4 ✓ / Assumptions 2 条
**参考**: docs/project/api/conventions.md, docs/reference/research/designs/prd-suishou-shiji/ui-mock-board.html
**依赖**: Story 1.2
