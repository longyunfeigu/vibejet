# Story 2.2 (US004): 创建考试目标

**用户故事**: 作为出题管理员，我可以在考试目标页填写六字段结构化目标，以便后续 AI 出题和主观题评分有明确约束

#### 验收标准

**Happy Path**
- [ ] 提交六字段后创建考试目标成功并回显创建者 `验证: API POST /api/v1/exam/objectives {六字段} → 201 + data.id + data.created_by + data.subjective_scoring_focus 回显`

**Edge Cases**
- [ ] `out_of_scope`（不考核范围）为空或省略时仍可创建成功 `验证: API POST /api/v1/exam/objectives {五个必填字段, out_of_scope 省略} → 201 + data.out_of_scope is null`
- [ ] 目标列表可用于后续出题选择，按创建时间可扫描 `验证: API GET /api/v1/exam/objectives → 200 + data.items[*].target_object 存在`

**Error Paths**
- [ ] 缺任一必填字段时返回 422，错误中指明缺项字段 `验证: API POST /api/v1/exam/objectives {缺 purpose} → 422 + error.field="purpose" + error.details.errors 非空`

**Integration**
- [ ] 保存后的 `subjective_scoring_focus` 可被 Epic 5 主观题评分读取 `验证: API GET /api/v1/exam/objectives/{id} → 200 + data.subjective_scoring_focus 非空`

#### 前端验收标准
- [ ] 考试目标页展示六字段表单，必填字段和可选字段视觉区分清晰 `验证: Browser 访问 /admin/objectives → 六字段 label 存在 + out_of_scope 标记可选`
- [ ] 必填项缺失时就地标红并阻止提交 `验证: Browser 留空 purpose click 提交 → purpose 错误提示出现 + 未创建列表项`
- [ ] 创建成功后目标出现在目标列表，且可被后续出题入口选择 `验证: Browser 提交后 → 目标列表含新建项 + 选择控件可见`
- [ ] 页面体验地图对齐：主操作清晰，六字段分组不拥挤，桌面/移动无重叠、无文字溢出 `验证: Browser 截图审查 /admin/objectives desktop+mobile → 无重叠/无溢出/提交按钮可见`

#### Assumptions
- [SCOPE] 单次 Demo 仅需一份考试目标即可跑通闭环 — Confidence: H — 失效影响: 多目标批量管理需新增筛选、编辑和归档交互

**覆盖度自检**: 派生 ✓（EP: 六字段有效/缺失；out_of_scope 可选） / Happy ✓ / Edge ✓ / Error ✓ / Integration ✓ / FE ✓ / AC 总数 5 ≤7 ✓ / Assumptions 1 条
**参考**: docs/project/api/exam.md（POST/GET objectives）, docs/project/data/exam.md（exam_objectives）
**依赖**: 无（Epic 级依赖 Epic 1）
