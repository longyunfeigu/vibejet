# US001 · Epic 1

### Story 1.1: 拍摄或上传餐食照片

**用户故事**: 作为记录者，我可以在手机浏览器上拍摄或从相册上传一张餐食照片，以便用最低成本发起一餐记录。

#### 验收标准

**Happy Path**
- [ ] 已登录记录者上传一张 10MB 以内的 JPEG/PNG/HEIC 餐食照片，返回照片资源标识且照片可再次访问 `验证: API POST /api/v1/meal-photos → 201 + data.photo_id exists`

**Edge Cases**
- [ ] 空文件（0 字节）被拒绝并返回校验错误 `验证: API POST /api/v1/meal-photos (0字节文件) → 422`
- [ ] 超过 10MB 的照片被拒绝并提示图片过大 `验证: API POST /api/v1/meal-photos (10MB+1B) → 422`

**Error Paths**
- [ ] 非图片文件（如 text/plain 伪装扩展名）被拒绝 `验证: API POST /api/v1/meal-photos (text/plain) → 422`
- [ ] 未登录上传照片被拒绝 `验证: API POST /api/v1/meal-photos (无凭证) → 401`

**Integration**
- [ ] 照片资源 owner-scoped：用户 B 访问用户 A 的照片返回 404（复用既有归属约定） `验证: pytest test_meal_photo_ownership_cross_user_404 → PASSED`

#### 前端验收标准
- [ ] 记录页有拍照/上传主入口且首屏可见 `验证: Browser /record input[type=file][accept*="image"] → exists`
- [ ] 上传期间展示上传进行态 `验证: Browser 上传大图期间 [data-testid=photo-uploading] → visible`
- [ ] 浏览器不支持相机时仅提供相册上传方式 `验证: Browser 模拟无 getUserMedia 打开 /record → 无拍照按钮且 input[type=file] 存在`
- [ ] 页面体验地图与设计合同对齐（拍照主操作单手可达） `验证: Browser 截图审查 → 无重叠/无溢出/拍照主操作首屏可见`

#### Assumptions
- [SCOPE] V1 一餐仅支持单张照片 — Confidence: M — 失效影响: 多菜大餐需分多次记录，录入成本上升（假设待审批）
- [DATA] 手机照片经前端压缩后 ≤10MB 足以覆盖日常拍摄 — Confidence: M — 失效影响: 原图直传被 422 拒绝，需在前端加压缩步骤
- [FEASIBILITY] 复用既有文件存储端口即可承载照片上传 — Confidence: H — 失效影响: 需新建存储通道，范围扩大

**覆盖度自检**: 派生 ✓（EP：文件类型/大小等价类 + BVA：0/10MB 边界）/ Happy ✓ / Edge ✓ / Error ✓ / Integration ✓ / FE ✓ / 行为 AC 总数 6 ≤7 ✓ / FE AC 4≤4 ✓ / Assumptions 3 条
**参考**: docs/project/api/conventions.md, docs/project/DESIGN.md, docs/reference/research/designs/prd-suishou-shiji/ui-mock-board.html
**依赖**: 无
