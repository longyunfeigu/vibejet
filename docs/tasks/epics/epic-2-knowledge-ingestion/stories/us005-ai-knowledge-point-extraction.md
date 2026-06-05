# Story 2.3 (US005): AI 知识点提取与确认

**用户故事**: 作为出题管理员，我可以对已录入资料触发 AI 知识点提取，并编辑、删除、新增后确认知识点，以便得到可进入出题环节的知识点基准

> 注：提取与人工确认必须一起交付。PRD §9.2 明确「AI 提取知识点 + 人工确认须一起，AI 输出必须可干预」，所以本 Story 不拆成“只提取”和“只确认”两个独立能力。

#### 验收标准

**Happy Path**
- [ ] 触发提取后立即返回 processing，前端可轮询至 completed 并取得结构化知识点列表 `验证: API POST /api/v1/exam/materials/{id}/knowledge-points → 202 + data.extraction_status="processing"; API GET .../knowledge-points → data.extraction_status="completed" + data.items 非空`
- [ ] 管理员编辑、删除、新增后全量替换确认，提交项均以 `confirmed=true` 保存 `验证: API PUT /api/v1/exam/materials/{id}/knowledge-points {items:[{name:"KP1"}]} → 200 + data.items[0].confirmed==true`

**Edge Cases**
- [ ] material 已 processing 时重复触发不重复调度后台任务，仍返回 processing `验证: API POST .../knowledge-points 连续两次 → 均 202 + extraction_status="processing"; 后台调度次数=1`
- [ ] 空数组全量替换合法但不可作为出题输入 `验证: API PUT .../knowledge-points {items:[]} → 200 + data.items=[]; API GET .../knowledge-points?confirmed=true → items=[]`

**Error Paths**
- [ ] 空资料、AI 提取失败、返回不可解析或轮询超过 60s 时，状态进入 failed 或页面展示失败，并提供重试/人工补充入口 `验证: API GET .../knowledge-points (mock 提取失败) → extraction_status="failed"; Browser 轮询>60s → 失败 UI + 重试按钮 + 人工补充入口`
- [ ] material_id 不存在时返回 404 `验证: API POST /api/v1/exam/materials/999999/knowledge-points → 404 + error.message_key="material.not_found"`

**Integration**
- [ ] confirmed gate：Epic 3 只能消费 `confirmed=true` 知识点，未确认或空知识点不得进入出题 `验证: pytest test_unconfirmed_kp_not_consumed_by_generate → PASSED; API GET .../knowledge-points?confirmed=true → 仅返回 confirmed 行`

#### 前端验收标准
- [ ] 知识点确认面板展示 material 状态、提取按钮和轮询中的 processing 状态 `验证: Browser 访问材料详情 → 提取按钮存在; click 提取 → processing 状态出现`
- [ ] completed 后以可编辑列表展示知识点，支持逐项编辑、删除、新增和确认 `验证: Browser extraction_status=completed → 可编辑列表存在 + 新增按钮存在 + 删除按钮存在 + 确认按钮存在`
- [ ] failed/空结果状态给出重试和人工补充入口，不出现空白页 `验证: Browser extraction_status=failed 或 items=[] → 失败/空态文案存在 + 重试按钮存在 + 人工补充入口存在`
- [ ] 页面体验地图对齐：确认按钮只在有有效知识点时突出，长列表可扫描，桌面/移动无重叠、无溢出 `验证: Browser 截图审查 知识点确认面板 desktop+mobile → 无重叠/无溢出/主操作清晰`

#### Assumptions
- [DEPENDENCY] LLM 能返回可解析的结构化知识点列表 — Confidence: M — 失效影响: 失败率高时管理员主要依赖人工补充入口，AI 提取价值下降
- [DATA] 切块后的资料足以覆盖本次 Demo 的知识点提取 — Confidence: M — 失效影响: 超长资料可能漏提，需要调切块或摘要策略
- [SCOPE] BackgroundTasks 不持久化任务，进程重启后依赖 60s 超时和重试兜底 — Confidence: H — 失效影响: 生产化需换成持久化任务队列

**覆盖度自检**: 派生 ✓（状态迁移: null→processing→completed/failed；重复触发；空确认） / Happy ✓ / Edge ✓ / Error ✓ / Integration ✓ / FE ✓ / AC 总数 7 ≤7 ✓ / Assumptions 3 条
**参考**: docs/project/api/exam.md（POST/GET/PUT knowledge-points）, docs/project/data/exam.md（knowledge_points, confirmed gate）
**依赖**: Story 2.1
