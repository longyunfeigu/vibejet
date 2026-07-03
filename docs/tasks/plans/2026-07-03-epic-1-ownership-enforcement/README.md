# Epic 1 Review Pack: 资源归属校验（Ownership Enforcement）

## One-Screen Summary

**解决什么**：五组资源端点（files / storage / conversations / chat / documents）目前任何登录用户可读写所有人的资源；本 Epic 让每个端点强制"只见自己、越权即 404"。
**不解决什么**：角色/租户、superuser 通道、agent-configs 归属（decisions.md D3/D5）。
**Reviewer 先看**：`decisions.md`（5 个假设待审批 + 1 个行为变更）→ `design.md` §6 决策表与 chat 时序 → `design.md` §8 端点表。
**Catalog touched**：`docs/project/api/conventions.md`、`api/documents.md`、新建 `api/conversations.md`、`api/files.md`、新建 `data/conversation.md`。
**Execution policy**：**strict**（命中：DB migration、权限/ownership、公共 API 行为变更）。

## Known Conflicts

- `docs/project/api/conventions.md` 鉴权段写"current base library does not provide a production authentication module"，与 AGENTS.md"JWT auth 已实现"不一致（文档陈旧）。本 Epic catalog 同步时一并修正该段落为现状。
- 其余无：story AC、catalog、代码基线一致。

## Reviewer Reading Path

1. `decisions.md` — D1(404伪装) / D2(服务层必填参数) / D3(无 superuser 通道) / D4(可空不回填) / D5(agent-configs 不含) / ACD-1(400→404 行为变更)
2. `design.md` — 10 段完整设计
3. `../../work/epic-1-ownership-enforcement/task-index.md` — 执行波次

## Execution Sketch

- **Barrier**: T001（U1：migration + conversation 实体/仓储 + 404 映射）——阻塞 U2
- **并行**: T002（U2 conversations+chat）等 T001；T003（U3 files+storage）、T004（U4 documents+catalog）立即可跑，写集与 U1/U2 隔离
- **收口**: 全量 pytest + lint-imports + flake8 + alembic up/down + `review` skill（strict gate）
- **Required gates**: migration gate（up/down 验证）、code review gate（安全面必审）、catalog sync gate

## Catalog Sync

| 文件 | 状态 |
|------|------|
| docs/project/api/conventions.md（鉴权段重写） | synced |
| docs/project/api/conversations.md（新建） | synced |
| docs/project/api/files.md（新建） | synced |
| docs/project/api/documents.md（owner 过滤 + 404 增补） | synced |
| docs/project/data/conversation.md（新建，owner_id delta） | synced |
