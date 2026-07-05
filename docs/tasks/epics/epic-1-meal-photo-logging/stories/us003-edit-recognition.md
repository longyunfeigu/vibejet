# US003 · Epic 1

### Story 1.3: 修正识别明细

**用户故事**: 作为记录者，我可以修改菜品名称、调整份量或删除误识别项，以便让保存的数字接近真实吃下的量。

#### 验收标准

**Happy Path**
- [ ] 调整某菜品份量后，该餐总热量与三大宏量营养素即时按比例重算 `验证: Browser 份量 1 改为 1.5 → [data-testid=total-calories] 数值变为原值×1.5（±1 取整误差）`
- [ ] 删除误识别项后，明细行消失且总数值即时扣减该项 `验证: Browser 点击某项删除 → 该行消失且 [data-testid=total-calories] 减少该项热量值`

**Edge Cases**
- [ ] 份量输入 0 或负数被拒绝并保留原值 `验证: Browser 份量输入 -1 失焦 → 行内校验提示出现且总热量不变`
- [ ] 删除全部明细后保存按钮禁用并提示至少保留一项或改用文本补录 `验证: Browser 删光全部明细 → button[data-testid=save-meal] disabled 且 [data-testid=empty-items-hint] visible`

**Error Paths**
- [ ] 菜品名称清空后无法提交修改 `验证: Browser 清空名称输入失焦 → 行内校验提示出现且原名称恢复`

#### 前端验收标准
- [ ] 修正控件符合页面体验地图（明细紧凑列表、单手可达、总热量优先级最高） `验证: Browser 截图审查 → 符合本 Epic 页面体验地图信息优先级与 DESIGN.md 密度规则`

#### Assumptions
- [SCOPE] V1 不支持手动新增菜品行（只能修改/删除识别结果；漏识别的菜走 Story 1.5 文本补录） — Confidence: M — 失效影响: 漏识别时用户需绕道补录，单餐记录耗时上升（假设待审批）
- [FEASIBILITY] 营养重算是明细项的份量比例计算，可即时完成、无需服务端往返 — Confidence: H — 失效影响: 需要服务端重算接口，修正交互出现可感知延迟

**覆盖度自检**: 派生 ✓（BVA：份量 0/负数边界 + EP：名称空/非空 + 状态迁移：明细集合空/非空）/ Happy ✓ / Edge ✓ / Error ✓ / Integration N/A — 修正发生在确认前的前端交互层，不产生跨层副作用（保存链路归 Story 1.4）/ FE ✓ / 行为 AC 总数 5 ≤7 ✓ / FE AC 1≤4 ✓ / Assumptions 2 条
**参考**: docs/project/DESIGN.md, docs/reference/research/designs/prd-suishou-shiji/ui-mock-board.html
**依赖**: Story 1.2
