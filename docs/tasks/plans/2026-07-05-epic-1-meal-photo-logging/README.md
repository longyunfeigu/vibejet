---
title: "Epic 1 拍照记录一餐 Review Entry"
type: epic-review-pack-readme
status: active
date: 2026-07-05
epic_id: "1"
epic_source: docs/tasks/epics/epic-1-meal-photo-logging/epic.md
execution_policy: "strict"
---

# Epic 1 拍照记录一餐 Review Entry

这份 README 是 human reviewer 的入口。它只帮助人快速判断"我要审什么、先看哪里、哪些地方还冲突"。

## 1. One-Screen Summary

- **本 Epic 解决的问题**：把"记录一餐"的成本压到 30 秒内——拍照 → AI 识别菜品与营养 → 修正 → 保存为饮食记录；识别失败走文本补录兜底。
- **本 Epic 不解决的问题**：今日聚合/首页总览（Epic 2）、目标设置（Epic 3）、历史趋势（Epic 4）、餐次自动推断、照片清理策略。
- **设计主文档**：[design.md](design.md)
- **决策真相源**：[decisions.md](decisions.md)（⚠️ 无人值守生成，D1–D9 全部为"假设待审批"）<!-- vj-plan-review: applied [human-design/1] -->
- **执行入口**：`docs/tasks/work/epic-1-meal-photo-logging/task-index.md`
- **catalog touched**：API yes（新 `api/meal-log.md`）/ Data yes（新 `data/meal-log.md`）/ UI yes（首建 `ui/surfaces.md` + `ui/routes.md`）
- **execution policy**：strict（新 DB schema + migration、外部 AI 服务接入、新公共 API 契约、owner-scoped 资源面）

## 2. Known Conflicts

| Conflict | Where it appears | Adopted review stance | Required follow-up |
|----------|------------------|-----------------------|--------------------|
| DESIGN.md §Richness Floor 只有 front-of-house 行，operational 屏无全局富度地板 | `docs/project/DESIGN.md:115-119` vs 本 Epic `/record`（operational） | 本 Epic 的富度地板由 design.md §7 Screen Contract 承载，不在 plan 里发明全局规则 | 后续跑 `vj-design-md-matcher` 时补 operational 行 |
| 设计稿路径不符 `designs/{epic-id}/` 约定 | 实际在 `designs/prd-suishou-shiji/` | 按 D8 引用现路径，参考图前置闸产物落 `designs/epic-1/` | reviewer 批准 D8 |

## 3. Reviewer Reading Path

1. 先看本页 One-Screen Summary 与 [decisions.md](decisions.md) 的 D1–D9（全部待审批；**D7 LLMPort 扩 ImageBlock 是本 Epic 最大的公共契约变更**，与 D1 识别服务选型、D3 同步识别并列必看）。<!-- vj-plan-review: applied [human-design/1] -->
2. 读 [design.md](design.md)：先读叙事区（为什么做/怎么做/最容易搞错的四件事/要拍板什么，大白话），再查合同区（术语表、API/Data/UI Delta、Must Hold、Risks）。
3. 只在需要核对执行编排时看 `docs/tasks/work/epic-1-meal-photo-logging/task-index.md`。

## 4. Execution Sketch

- **Barrier**：T001（meal 域模型 + migration + DTO/路由骨架 + 共享注册点一次占位）。
- **可并行**：T002 照片上传薄端点 / T003 识别能力（photo+text）/ T004 保存记录——写集隔离，W2 并行。
- **收口**：T005 `/record` 整屏 frontend composition（API 合同稳定后）→ T006 E2E polish + Unit 收口验证 + catalog 复核。
- **Required gates**：migration up/down 验证 · `verify.sh all` 全绿 · `/record` 屏 B 轨截图闸（operational）· review skill · catalog sync 复核 · plan_lint exit 0。

## 5. Catalog Sync

| Area | Files | Status |
|------|-------|--------|
| API | docs/project/api/meal-log.md（新建）, docs/project/api/conventions.md（模块索引已追加） | synced |
| Data | docs/project/data/meal-log.md（新建）, docs/project/data/README.md（索引已追加） | synced |
| UI | docs/project/ui/surfaces.md, docs/project/ui/routes.md（本 Epic 首建） | synced |

## 6. Research Coverage Note

Phase 2 研究：Agent A（design-context）✅ · Agent B（upstream-contracts）N/A（无上游 Epic，Consumes 为空）· Agent C（codebase-scout）**API 故障降级**——复用锚点由 Agent A 结果 + 主上下文对关键路径的直接验证补齐（file_asset/storage 契约、LLM provider 文件、conventions 全文），并有 plan_lint R7 对全部 Read first 路径做存在性兜底 · Agent D N/A（docs/solutions/ 无条目）。

## 7. Open Review Questions

| ID | Question | Why it matters | Owner |
|----|----------|----------------|-------|
| Q1 | D1 用通用多模态模型做营养估算，质量是否达到"量级感知"底线？ | 不达标则整个产品假设不成立（PRD §8 高优先验证项） | edy |
| Q2 | D3 同步识别 + 10s 超时在真实弱网下的体验是否可接受？ | 决定是否需要改为异步 + 轮询/推送 | edy |
