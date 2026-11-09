# API-first 例外清单

记录测试数据实体的 REST API 可用性。有 API 的走 `core/api/entities/<x>.api.ts`;
无 API 的走 `core/api/entities/<x>.ui-fallback.ts`(仅语义定位),并在此说明原因。

| 实体 | create API | delete API | 状态 | 说明 |
|---|---|---|---|---|
| agent | POST /api/agents/import-snapshot | DELETE /api/agents/{id}?source_agent_region | ✅ 已实现 | baseline-snapshot.json 作模板;见 `entities/agent.api.ts` |
| case-set (ai-simulation TestSet) | POST /api/agents/{flow_id}/case-sets（+ POST .../scenarios、POST .../mix-from-existing） | DELETE /api/case-sets/{id}（archive，非硬删） | ✅ 已实现 | 见 `entities/case-set.api.ts`；tenant-testset-list 用例专用 |
| flow | POST /api/v1/flow/flows | DELETE /api/v1/flow/flows/{id} | ✅ 可用 | 现有代码已在用(多模块) |
| shared-link | POST /api/shared-links | (待确认) | 🔍 调研中 | 创建端点已在用;删除待批 2/3 确认 |
| kb | (待确认) | (待确认) | 🔍 调研中 | 批 3 迁移前确认 |
| phone-number | (待确认) | (待确认) | 🔍 调研中 | 批 3 迁移前确认 |
| mcp-registry | (待确认) | (待确认) | 🔍 调研中 | 批 3 迁移前确认 |
| whatsapp | (待确认) | (待确认) | 🔍 调研中 | 批 3 迁移前确认 |
| template | POST /api/templates | ❌ 不提供(系统级) | ✅ 特例 | 只 create/get,绝不 delete(系统级共享资源) |
| simulation (ai-simulation Simulation) | POST /api/simulations | DELETE /api/simulations/{id}（硬删） | ✅ 已实现 | 见 `entities/simulation.api.ts`；run-benchmark 用例专用；另提供 `seedAgentHasRun()` 包装 POST /api/case-sets/{suite_id}/runs,用于让 Agent 的 run_count>0(Manage Agents 选择器的 has_runs 过滤前提) |
| sim_agent_suite_rail (embedded rail visibility/order) | PUT /api/agents/{flow_id}/rail-suites | (随 case-set archive 级联,无独立 delete) | ✅ 已实现 | 见 `entities/rail-suite.api.ts`；embedded-rail 用例专用；`setVisibility()` 批量设可见性/顺序作前置状态；`seedCompletedEvaluationRun()` 用空 case set + auto_run 快速跑出一个真实 stage=evaluation/status=completed 的 run（无 LLM 调用),满足 rail 的"已评测过则默认可见"种子规则前置条件 |

> 状态:✅可用 / ⚠️UI-fallback / ❌无(系统级) / 🔍调研中。
> 批 1~3 迁移到对应实体前,把该行确认到 ✅ 或 ⚠️。
> 第 0 批仅确认 agent / flow / template;其余留待对应迁移批。
