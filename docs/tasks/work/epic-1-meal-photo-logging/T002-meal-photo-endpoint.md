# T002 照片上传薄端点

**Epic:** [Epic 1 拍照记录一餐](../../epics/epic-1-meal-photo-logging/epic.md) · **Unit / Scope:** U1 Story 1.1（后端部分；FE AC 归 T005） · **Depends:** T001 · **Wave:** 2

**Generated from:** Review Pack `docs/tasks/plans/2026-07-05-epic-1-meal-photo-logging/` · Unit `U1` · Story `1.1` · Design anchors `design.md#api-delta` · Decision anchors `decisions.md#D2` · Catalog anchors `docs/project/api/meal-log.md` `docs/project/api/files.md`
**Task scope:** 本文档是执行投影。本 task 只做 `POST /api/v1/meal-photos` 后端闭环；U1 done 还需 T005 的 FE AC + T006 收口（task done != Unit done）。

## 1. Context
### Source anchors
- Review Pack: design.md 合同区 API Delta（端点约束行）+ decisions.md D2（薄端点委托 file_asset 的完整论证）
- Task Index: `task-index.md` Wave 2（与 T003/T004 并行，写集隔离）
- Catalog: `docs/project/api/files.md`（被委托的 storage 契约）
- Story AC: `docs/tasks/epics/epic-1-meal-photo-logging/stories/us001-meal-photo-upload.md`
### 现状
- T001 已建 `api/routes/meal_photos.py` 骨架并注册；file_asset 上传链路（owner-scoped、kind 列）可用
### 目标态
- 薄端点完成：meal 特定校验（仅 image/*、≤10MB、非空）→ 委托 file_asset 上传服务（kind=meal-photo）→ 统一信封返回 `data.photo_id`
### 继承假设
- A1 (D2): photo_id 即 file asset id，不建 meal 侧照片表
### Read first
- `backend/application/services/file_asset_service.py` - 被委托的上传服务与 owner 传参模式
- `backend/api/routes/storage.py` - 既有上传端点的 I/O 绑定模式
- `docs/tasks/epics/epic-1-meal-photo-logging/stories/us001-meal-photo-upload.md` - AC 全文
### Write scope
- May modify:
  - `backend/api/routes/meal_photos.py`
  - `backend/application/services/meal_photo_service.py`（若薄到不需要独立 service 则直接在路由层委托，记录取舍）
  - `backend/tests/test_meal_photos.py`
- Do not modify: `backend/main.py`（T001 已注册）、file_asset 模块任何文件、其他 meal 路由文件

## 2. Implementation Plan
### Phase 1: test-first
- [ ] `tests/test_meal_photos.py`：201 happy / 0 字节 422 / 10MB+1 422 / text-plain 422 / 无凭证 401 / 跨用户 404（AC 逐条映射）
### Phase 2: 实现
- [ ] 校验（content-type 白名单 + 大小）→ 委托 file_asset（kind=meal-photo, owner_id=current_user.id 必填关键字）→ 信封返回

## 3. Technical Approach
### 方案
- FastAPI multipart + 既有 file_asset 服务；无新依赖
### 关键 API / 集成点
- `file_asset_service.relay_upload_stream(*, user_id, file_stream, filename, kind="meal-photo", content_type, size_hint) -> StorageUploadResponseDTO` - 委托点（`api/routes/storage.py` upload_file 端点同款调用）；`data.photo_id` = 返回 DTO 的 `file_id`<!-- vj-plan-review: applied [feasibility/1] -->
### 错误处理
| Error | HTTP | When | message_key |
|------|------|------|------|
| PARAM_VALIDATION_ERROR | 422 | 空/超限/非图片 | 复用既有 |
| UNAUTHORIZED | 401 | 无凭证 | 复用既有 |
| NOT_FOUND | 404 | 跨用户访问照片 | 复用既有（与不存在同响应） |
### 日志
| Event | Level | Fields |
|------|------|------|
| meal_photo.uploaded | info | photo_id, size, content_type |
### 备选（Rejected，引自 `decisions.md`）
- 前端直用 `/storage/upload` — meal 校验规则无处安放（D2）
### Execution note
- Test policy: test-first（ownership/校验面）
- 复用声明: 必须委托 file_asset 上传服务；禁止重写存储/归属逻辑
- Fallback 约束: 无
### Stop conditions
- file_asset 服务签名与假设不符且改造超出 write scope
- 发现与 Story AC / catalog / design.md / decisions.md anchors 冲突

## 4. Acceptance Criteria
> 投影自 Story 1.1（本 task 覆盖行为 AC 全部 6 条；FE AC 4 条由 T005 覆盖）
- [ ] Given 已登录 When 上传 ≤10MB 图片 Then 201 + `data.photo_id`（信封内）
- [ ] Given 0 字节 / >10MB / 非图片 / 无凭证 When 上传 Then 422 / 422 / 422 / 401
- [ ] Given 用户 B When 访问用户 A 的照片 Then 404（`test_meal_photo_ownership_cross_user_404`）

## 5. Affected Components
### 实现
- `backend/api/routes/meal_photos.py` - 填实骨架；无 DB 写（委托 file_asset 落库）
### 文档（必更）
- 无（`api/meal-log.md` 已由 plan 同步；实现偏离时报告）

## 6. Existing Code Impact
### 需重构
- 无
### 现有测试受影响
- 无
### 测试新增（test-first，本 task 要写）
- `tests/test_meal_photos.py`：happy ×1 + edge ×2 + error ×2 + ownership ×1

## 7. Definition of Done
- [ ] `pytest tests/test_meal_photos.py -q` 全绿（= `verify.sh U1` 的可执行部分）
- [ ] test-first 执行；记录入 `_ledger.md`
- [ ] task done != U1 done：已在 ledger 标注 FE AC 归 T005、收口归 T006
- [ ] 未引入新决策；未修改 write scope 之外文件
