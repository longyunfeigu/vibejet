# T004 保存饮食记录

**Epic:** [Epic 1 拍照记录一餐](../../epics/epic-1-meal-photo-logging/epic.md) · **Unit / Scope:** U4 Story 1.4（后端全部）+ U5 记录同构测试（partial） · **Depends:** T001 · **Wave:** 2

**Generated from:** Review Pack `docs/tasks/plans/2026-07-05-epic-1-meal-photo-logging/` · Unit `U4`+`U5(partial)` · Story `1.4`/`1.5` · Design anchors `design.md#api-delta` `design.md#data-delta` · Decision anchors `decisions.md#D4 #D5 #D9` · Catalog anchors `docs/project/api/meal-log.md` `docs/project/data/meal-log.md`
**Task scope:** 本文档是执行投影。本 task 交付 `POST /api/v1/meal-records` 后端闭环（幂等 + 归属 + 校验）；U4 done 还需 T005 FE AC + T006 收口。

## 1. Context
### Source anchors
- Review Pack: design.md 合同区 API Delta 保存失败表 + decisions.md D9（幂等机制）/D4（不重算）/D5（餐次）
- Task Index: Wave 2 并行；写集与 T002/T003 隔离
- Story AC: `stories/us004-save-meal-record.md` + `stories/us005-text-fallback-entry.md`（Integration AC）
### 现状
- T001 已建 domain 聚合/repository/migration 与 `api/routes/meal_records.py` 骨架；`IdempotencyService` 在 presign-upload 有现成用法
### 目标态
- 保存用例完成：幂等检查（Idempotency-Key 头）→ items 校验 → 聚合构建（含营养快照）→ UoW 落库 → 201 信封
### 继承假设
- A1 (D9): 幂等 key 由前端生成、重试沿用；(owner, key) 维度缓存首次结果
- A2 (D4): 后端校验结构与取值合法（items 非空、portion>0、营养 ≥0），不重新估算；**记录 totals 由服务端从 items 求和，API body 不收也不采信任何客户端 total 字段**（design.md 合同区 Must Hold）<!-- vj-plan-review: applied [adversarial/5] -->
### Read first
- `backend/api/routes/storage.py` - presign-upload 的 IdempotencyService 用法（照抄）
- `backend/application/services/conversation_service.py` - owner_id 必填关键字 + belongs_to 断言模式
- `docs/tasks/epics/epic-1-meal-photo-logging/stories/us004-save-meal-record.md` - AC 全文
### Write scope
- May modify:
  - `backend/application/services/meal_record_service.py`
  - `backend/api/routes/meal_records.py`
  - `backend/tests/test_meal_records.py`
- Do not modify: `backend/main.py`、识别相关文件、`domain/meal_log`（T001 已定；发现地基缺口走 Stop condition）

## 2. Implementation Plan
### Phase 1: test-first
- [ ] `tests/test_meal_records.py`：201+DB 字段快照 / 幂等（同 key 两次 → 一条记录同响应）/ items=[] 422 / 无凭证 401 / 跨用户 404 / `test_text_fallback_record_same_shape_as_photo_record`（source=text 的记录与 photo 记录同构可聚合）
### Phase 2: 实现
- [ ] service（service-local UoW Protocol）+ 路由填实

## 3. Technical Approach
### 方案
- 既有 UoW + IdempotencyService；聚合快照落 `meal_records` + `meal_record_items`
### 关键 API / 集成点
- 幂等照抄 `api/routes/storage.py` 的路由级模式：`idempotency_for("meal:save-record")` 依赖 + `IdempotencyContext`（`api/utils/idempotency.py`）；底层 `IdempotencyService` 的 `decide/persist_result/release` 不直接手调<!-- vj-plan-review: applied [feasibility/2] -->
### 错误处理
| Error | HTTP | When | message_key |
|------|------|------|------|
| PARAM_VALIDATION_ERROR | 422 | items 空/portion≤0/meal_type 非法 | 复用既有 |
| UNAUTHORIZED | 401 | 无凭证 | 复用既有 |
| NOT_FOUND | 404 | photo_id 非本人 | 复用既有 |
### 日志
| Event | Level | Fields |
|------|------|------|
| meal_record.saved | info | record_id, source, meal_type, item_count, total_calories |
### 备选（Rejected，引自 `decisions.md`）
- 仅前端禁用按钮防重复 / DB 唯一约束去重 — D9
### Execution note
- Test policy: test-first（事务/幂等/归属面）
- Risk class: strict-trigger:transaction-idempotency（幂等/事务一致性 + owner 归属面）
- UI class: none
- System-wide check: none（写集与同 wave task 隔离；IdempotencyService 只读复用）
- Verification: `cd backend && uv run pytest tests/test_meal_records.py -q`
- 复用声明: 幂等必须复用 IdempotencyService（照 presign-upload 模式）；归属断言用聚合 `belongs_to`
- Fallback 约束: DB 写失败必须回滚且幂等 key 不落缓存（可重试）；禁止吞错返回假 201
### Stop conditions
- 发现 T001 地基缺字段/缺方法（回报 barrier 缺口，不在本 task 内改 domain）
- 幂等语义与 design.md API Delta 保存失败表冲突
- 与 Story AC / catalog / anchors 冲突

## 4. Acceptance Criteria
> 投影自 Story 1.4 行为 AC 全部 7 条（其中"餐次默认值" Browser AC 归 T005）+ Story 1.5 Integration AC 1 条
- [ ] Given 确认明细 When POST /meal-records Then 201 + record_id；DB 行含照片引用/明细/时间/合法餐次
- [ ] Given 同一 Idempotency-Key 两次提交 Then 仅一条记录、同响应
- [ ] Given items=[] / 无凭证 / 跨用户查询 Then 422 / 401 / 404
- [ ] Given source=text 的保存 Then 记录与 photo 记录同构（同表同字段可聚合）

## 5. Affected Components
### 实现
- 见 Write scope；副作用：DB 写（两表，事务内）
### 文档（必更）
- 无（catalog 已同步；偏离时报告）

## 6. Existing Code Impact
### 需重构
- 无
### 现有测试受影响
- 无
### 测试新增（test-first）
- happy ×2 + 幂等 ×1 + error ×2 + ownership ×1 + text 同构 ×1

## 7. Definition of Done
- [ ] `pytest tests/test_meal_records.py -q` 全绿（= `verify.sh U4` 可执行部分 + U5 的 `-k text_fallback`）
- [ ] test-first 执行；strict 逐 task 记录入 `_ledger.md`
- [ ] task done != U4 done：ledger 标注 FE 归 T005、收口归 T006
- [ ] 未引入新决策；未修改 write scope 之外文件
