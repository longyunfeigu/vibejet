# Epic 1 Task Index — 资源归属校验

**Review Pack**: `docs/tasks/plans/2026-07-03-epic-1-ownership-enforcement/`
**Execution policy**: strict（DB migration + ownership/安全 + 对外行为变更）
**Required gates**: migration up/down 验证 · 全量 pytest + lint-imports + flake8 · `review` skill 审查 · catalog sync 复核

## Unit DAG（= epic.md 依赖行）

U1(Story 1.1) → U2(Story 1.2)；U3(Story 1.3)、U4(Story 1.4) 独立。

## Task DAG / 波次

| Wave | Task | Unit | Depends | 写集 |
|------|------|------|---------|------|
| 1 | T001 conversations 归属地基 | U1 | 无 | alembic/versions/0004、domain/conversation/entity.py、infrastructure/models/conversation.py、domain+infra conversation repository、core/exceptions.py、tests/test_conversation_ownership.py（entity/repo/映射部分） |
| 1 | T003 files+storage 归属闭环 | U3 | 无 | application/services/file_asset_service.py、api/routes/files.py、api/routes/storage.py、tests/test_file_ownership.py、tests/test_idempotency_presign.py（Fake 跟签名） |
| 1 | T004 documents 归属闭环 | U4 | 无 | application/services/document_service.py、api/routes/documents.py、tests/test_document_ownership.py |
| 2 | T002 conversations+chat 归属闭环 | U2 | T001 | application/services/conversation_service.py、application/services/chat_service.py、api/routes/conversations.py、api/routes/chat.py、tests/test_conversation_ownership.py（service/route 部分）、tests/test_chat_ownership.py、tests/test_chat_service_stream.py（跟签名） |
| 3 | T005 catalog 同步 + Epic 收口验证 | U4 收口 + Epic gate | T001-T004 | docs/project/api/*、docs/project/data/conversation.md |

**Barrier / owner tasks**: T001 是唯一 barrier（U2 依赖其实体/仓储/404 映射）。T005 是收口 owner task。
**共享文件冲突**: `core/exceptions.py` 仅 T001 写；`tests/test_conversation_ownership.py` 由 T001 创建、T002 追加（同 Unit 链路串行，无并发写）；无 `unit_of_work.py` / `main.py` / `dto.py` 改动。
**task done ≠ Unit done**: U1 done = Story 1.1 全部 AC `验证:` 通过；U2/U3/U4 同理；Epic done 还需 T005 gates 全绿。

## Unit → Task 映射

| Unit | Story | Tasks | Unit done 信号 |
|------|-------|-------|----------------|
| U1 | 1.1 | T001 | story-1.1 AC 全过 + migration up/down 通过 |
| U2 | 1.2 | T002 | story-1.2 AC 全过（含 chat 零副作用） |
| U3 | 1.3 | T003 | story-1.3 AC 全过 |
| U4 | 1.4 | T004+T005 | story-1.4 AC 全过 + catalog synced |
