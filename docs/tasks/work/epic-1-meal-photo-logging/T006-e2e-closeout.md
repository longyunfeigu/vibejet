# T006 E2E 收口

**Epic:** [Epic 1 拍照记录一餐](../../epics/epic-1-meal-photo-logging/epic.md) · **Unit / Scope:** U1-U5 收口 + Epic gate（整合/验证 task，不新增业务代码） · **Depends:** T005 · **Wave:** 4

**Generated from:** Review Pack `docs/tasks/plans/2026-07-05-epic-1-meal-photo-logging/` · Unit `U1-U5 收口` · Design anchors `design.md#must-hold` · Decision anchors `decisions.md#D1 #D3` · Catalog anchors `docs/project/api/meal-log.md` `docs/project/data/meal-log.md` `docs/project/ui/surfaces.md`
**Task scope:** 收口 owner task：跑全量验证、记录 Unit Verification、复核 catalog、走 review gate。只修验证暴露的缺陷，不加新功能；大缺陷回报对应 task。

## 1. Context
### Source anchors
- Task Index: Required Gates 全表（本 task 的职责清单）
- Review Pack: design.md 合同区 Must Hold（逐条核验对象）
### 现状 / 目标态
- W1-W3 完成 → 全部 gates 绿、每个 Unit 的收口记录进 `_ledger.md`、Epic 可标 done
### Read first
- `docs/tasks/work/epic-1-meal-photo-logging/verify.sh` - 收口入口
- `docs/tasks/work/epic-1-meal-photo-logging/_ledger.md` - 已有记录
### Write scope
- May modify:
  - `docs/tasks/work/epic-1-meal-photo-logging/_ledger.md`
  - 缺陷修复涉及的 W1-W3 已有文件（每处修复须在 ledger 注明回指哪个 task）
- Do not modify: catalog（偏离时报告，不静默改）

## 2. Implementation Plan
### Phase 1: 全量验证
- [ ] `bash verify.sh all` 全绿（MANUAL 项走 UI QA 证据）；`alembic downgrade -1 && upgrade head` 双向
- [ ] 全量 pytest + lint-imports + flake8 + 前端 typecheck/vitest
### Phase 2: 端到端演示 + 异常态
- [ ] 浏览器完整业务演示：拍照→识别→修正→保存→（重复保存幂等）；三条降级路径实测（非食物图/超时模拟/服务 500）
- [ ] cross-screen visual polish pass N/A（单屏 epic），但对照 design.md 合同区 Must Hold 逐条核验（含"识别零副作用"DB 实查）
### Phase 3: 收口记录
- [ ] 每个 Unit 的 Unit Verification 记入 `_ledger.md`；review gate（strict 完整 diff review）；catalog 复核

## 3. Technical Approach
### Execution note
- Test policy: verification-only
- Risk class: low（收口验证，不新增业务代码）
- UI class: none（浏览器演示按 verify.sh MANUAL 项 + UI QA 证据执行，非 UI 构建）
- System-wide check: risk-triggered-two-hop（收口即全域：全量 pytest / lint-imports / flake8 / 前端 typecheck+vitest + Must Hold 逐条核验）
- Verification: `bash docs/tasks/work/epic-1-meal-photo-logging/verify.sh all`
- 复用声明: 无（不新增业务代码）
- Fallback 约束: MANUAL 项必须有截图/操作证据，不接受"应该没问题"
### Stop conditions
- 任何 Must Hold 不变量被打破（回报对应 task，不在收口 task 内打补丁掩盖）
- verify.sh 与 story AC 冲突（story 为准，登记差异）

## 4. Acceptance Criteria
- [ ] Given 完整实现 When `verify.sh all` Then RESULT: PASS（executed>0）
- [ ] Given review gate When 完整 diff review Then blocking findings 清零
- [ ] Given catalog 三处 When 与实现比对 Then 一致或差异已报告

## 5. Affected Components
- `_ledger.md` 收口记录；无业务代码新增

## 6. Existing Code Impact
- 仅缺陷修复；每处回指原 task 记录

## 7. Definition of Done
- [ ] verify.sh all 绿 + 全部 Required Gates 绿
- [ ] 每个 Unit 的 Story AC / Unit Verification 在 `_ledger.md` 有收口记录
- [ ] review blocking findings 已修复；catalog 复核完成
- [ ] Epic 可标 completed（review pack README frontmatter 由 vj-work 收尾翻转）
