# Story 2.1 (US003): 录入业务资料

**用户故事**: 作为出题管理员，我可以在业务材料页粘贴文本或上传 txt/md/pdf 资料，以便系统保存本次考试的知识来源并为后续知识点提取准备切块内容

#### 验收标准

**Happy Path**
- [ ] 粘贴文本录入成功，资料落库并切块到 `material_chunks` `验证: API POST /api/v1/exam/materials {content:"..."} → 201 + data.status="ready"; DB SELECT COUNT(*) FROM material_chunks WHERE material_id=X → ≥1`
- [ ] 上传 txt/md/pdf 文件录入成功，文件名和提取文本可回显 `验证: API POST /api/v1/exam/materials (multipart file=a.pdf) → 201 + data.filename="a.pdf" + data.content 非空`

**Edge Cases**
- [ ] 资料列表按创建时间倒序返回，列表项不返回全文，仅返回 100 字以内预览 `验证: API GET /api/v1/exam/materials → 200 + data.items[0].content_preview.length ≤100 + items 按 created_at 倒序`

**Error Paths**
- [ ] 空内容（无文本且无文件）时拒绝录入 `验证: API POST /api/v1/exam/materials {content:""} → 422 + error.message_key="param.validation_error"`
- [ ] 不支持的文件格式时拒绝录入 `验证: API POST /api/v1/exam/materials (multipart file=a.docx) → 422 + error.message_key="unsupported_format"`

**Integration**
- [ ] 切块顺序从 0 连续，供知识点提取和 grounded 出题复用 `验证: DB SELECT ordinal FROM material_chunks WHERE material_id=X ORDER BY ordinal → [0..N] 连续`

#### 前端验收标准
- [ ] 业务材料页同时提供文本粘贴区、文件上传入口和资料列表 `验证: Browser 访问 /admin/materials → textarea 存在 + input[type=file] 存在 + materials list region 存在`
- [ ] 空态展示录入引导，不出现空白页面 `验证: Browser 无资料访问 /admin/materials → empty state 文案存在 + 主操作按钮存在`
- [ ] 上传或粘贴提交中显示 loading，成功后最新资料出现在列表首位 `验证: Browser 提交资料 → loading 状态出现; 请求完成 → 列表首项为新资料`
- [ ] 页面体验地图对齐：列表行展示提取状态、文件名/预览和创建时间，桌面/移动无重叠、无溢出 `验证: Browser 截图审查 /admin/materials desktop+mobile → 无重叠/无溢出/status 可见`

#### Assumptions
- [DEPENDENCY] `pypdf` 能从常规文本 PDF 提取可用文字 — Confidence: M — 失效影响: 扫描版 PDF 提取为空时，管理员需改用文本粘贴
- [SCOPE] MVP 不支持 docx/OCR/对象存储，资料内容直接入库 — Confidence: H — 失效影响: 大文件或复杂格式需要新增解析与存储链路

**覆盖度自检**: 派生 ✓（EP: 文本/txt/md/pdf/空/非法格式） / Happy ✓ / Edge ✓ / Error ✓ / Integration ✓ / FE ✓ / AC 总数 6 ≤7 ✓ / Assumptions 2 条
**参考**: docs/project/api/exam.md（POST/GET materials）, docs/project/data/exam.md（materials/material_chunks）
**依赖**: 无（Epic 级依赖 Epic 1）
