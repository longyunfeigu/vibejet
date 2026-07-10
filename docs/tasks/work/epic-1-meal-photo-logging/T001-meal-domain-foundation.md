# T001 meal 域地基（barrier）

**Epic:** [Epic 1 拍照记录一餐](../../epics/epic-1-meal-photo-logging/epic.md) · **Unit / Scope:** barrier/owner task，服务 U1-U5 共享地基 · **Depends:** 无 · **Wave:** 1

**Generated from:** Review Pack `docs/tasks/plans/2026-07-05-epic-1-meal-photo-logging/` · Design anchors `design.md#data-delta` `design.md#术语表` · Decision anchors `decisions.md#D2 #D5` · Catalog anchors `docs/project/data/meal-log.md` `docs/project/api/conventions.md`
**Task scope:** 本文档是执行投影，不是新需求层。本 task 是 barrier：独占全部共享注册点，产出被 T002/T003/T004 消费的稳定地基；不实现任何端点业务逻辑。与 Story AC / catalog / design.md / decisions.md 冲突时 STOP 并报告。

## 1. Context
### Source anchors（先看这些，不全文读 review pack）
- Review Pack: `docs/tasks/plans/2026-07-05-epic-1-meal-photo-logging/` design.md 合同区 Data Delta/术语表 + decisions.md D2/D5
- Task Index: `task-index.md` Shared File Coordination 表（本 task 独占清单）
- Catalog: `docs/project/data/meal-log.md`（本 plan 已同步的表设计）
- Story AC: `docs/tasks/epics/epic-1-meal-photo-logging/stories/`
### 现状
- meal 业务域不存在；conversation 模块是 owner-scoped 聚合的 canonical 参考（entity 的 `belongs_to`、repository、复合索引、CHECK 约束命名）
### 目标态
- `domain/meal_log`（MealRecord 聚合 + MealItem + MealType 值对象 + repository 接口）、ORM 模型、repository 实现、UoW 注册、Alembic 增量 revision（两表）、meal DTO、3 个路由骨架文件已注册 `main.py`（骨架返回 501 或空实现，W2 各 task 填实）
### 继承假设
- A1 (D5): 餐次封闭枚举 `breakfast/lunch/dinner/snack`，DB CHECK 约束
- A2 (D2): 照片以 `photo_asset_id` 逻辑引用 file_assets，不建 FK
### Read first
- `backend/domain/conversation/entity.py` - `belongs_to` 归属断言模式
- `backend/infrastructure/models/conversation.py` - owner_id nullable + 复合索引 + CHECK 命名模式
- `backend/infrastructure/unit_of_work.py` - repository 注册点
- `backend/main.py` - 路由注册模式
### Write scope
- May modify:
  - `backend/domain/meal_log/`（新建）
  - `backend/infrastructure/models/meal_log.py`
  - `backend/infrastructure/models/__init__.py`
  - `backend/infrastructure/repositories/meal_log_repository.py`
  - `backend/infrastructure/unit_of_work.py`
  - `backend/alembic/versions/`（新 revision）
  - `backend/application/dto.py`（追加 meal DTO 区段——dto 是扁平单文件模块，不建包、不动既有 DTO）
  - `backend/api/routes/meal_photos.py`
  - `backend/api/routes/meal_recognitions.py`
  - `backend/api/routes/meal_records.py`
  - `backend/main.py`
- Do not modify: `backend/application/ports/llm.py`（T003 owner）、`frontend/`（T005 owner）、既有模块任何文件（唯一例外：`application/dto.py` 允许追加 meal 区段）

## 2. Implementation Plan
### Phase 1: domain + 持久化（barrier 核心）
- [ ] `domain/meal_log/entity.py`：MealRecord 聚合（items 组合、`belongs_to(owner_id)`、items 非空校验）+ MealType 值对象
- [ ] `domain/meal_log/repository.py` 接口；ORM 两表按 design.md 合同区 Data Delta（列/CHECK/复合索引 `ix_meal_records_owner_recorded`）
- [ ] repository 实现 + `unit_of_work.py` 注册；`alembic revision --autogenerate` 并人工核对
### Phase 2: 契约骨架
- [ ] meal DTO（识别明细 item 结构与 API Design 表一致）
- [ ] 3 个路由骨架文件 + `main.py` 注册（router 级 JWT 闸门照抄既有模块）

## 3. Technical Approach
### 方案
- SQLAlchemy async + Alembic（既有栈）；聚合根模式照抄 conversation
### 关键 API / 集成点
- `MealRecord.belongs_to(owner_id) -> bool` - application service 归属断言用
### 错误处理
| Error | HTTP | When | message_key |
|------|------|------|------|
| PARAM_VALIDATION_ERROR | 422 | items 空/取值非法 | 复用既有 |
### 日志
| Event | Level | Fields |
|------|------|------|
| meal_log.migration | info | revision |
### 备选（Rejected，引自 `decisions.md`）
- items 存 JSON 列 — Epic 4 按菜品维度查询可能性 > 写入便利（design.md §6）
### Execution note
- Test policy: test-first（domain 不变量 + migration）
- Risk class: strict-trigger:db-migration（新表 + 增量 revision；task-index Required Gates 的 migration 双向验证）
- UI class: none
- System-wide check: direct-neighbors（独占共享注册点 main.py / models/__init__.py / unit_of_work.py，lint-imports + 既有 pytest 全量兜底）
- Verification: `cd backend && uv run pytest tests/test_meal_domain.py -q && uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head`（barrier 另跑 `uv run lint-imports`；既有 pytest 全量不回归见 DoD）
- 复用声明: 归属/索引/CHECK 模式必须照抄 conversation 模块，不发明新模式
- Fallback 约束: 无
### Stop conditions
- 需要改 write scope 之外文件且非本 task owner
- autogenerate 产出与 design.md Data Delta 表结构不一致且无法解释
- 发现 task packet 与 Story AC / catalog / design.md / decisions.md anchors 冲突

## 4. Acceptance Criteria
> barrier task 无独立 Story AC；done = 地基验证
- [ ] Given 空库 When `alembic upgrade head` Then 两表建立、CHECK 与复合索引存在；`downgrade -1` 干净回滚
- [ ] Given 既有全量 pytest When 运行 Then 零回归；`lint-imports` 通过

## 5. Affected Components
### 实现
- 见 Write scope；副作用：DB schema +2 表
### 文档（必更）
- 无（catalog 已由 plan 同步；偏离时报告）

## 6. Existing Code Impact
### 需重构
- 无
### 现有测试受影响
- 无（纯新增）
### 测试新增（test-first，本 task 要写）
- domain：items 非空校验、belongs_to、MealType 取值（`tests/test_meal_domain.py`）
- migration up/down 冒烟

## 7. Definition of Done
- [ ] 本 task 覆盖的 AC / 局部验证满足；migration up/down 通过
- [ ] 按本文档 Execution note 的 Test policy 执行：test-first
- [ ] Verification 全绿；失败修复尝试和结果已由 vj-work 记入 `_ledger.md`
- [ ] 共享注册点（main.py / models/__init__.py / unit_of_work.py）一次占位完成，W2 task 无需再碰
- [ ] 未引入新决策；投影错误已 STOP 回 review pack
- [ ] 未修改 write scope 之外文件
