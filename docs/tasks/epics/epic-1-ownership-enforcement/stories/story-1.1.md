# Story 1.1: conversations 获得归属（schema + domain + repo + 404 映射修正）

**As a** 平台运营者
**I want** 会话数据带有归属用户，且"资源不存在"类错误返回正确的 404
**So that** 后续端点可以按归属过滤与断言，越权表现与不存在一致

**依赖**: 无（本 Epic 的 barrier Story）

## 范围

- Alembic migration `0004`：`conversations` 表加 `owner_id`（Integer，可空）+ `ix_conversations_owner_created (owner_id, created_at)` 索引
- `domain/conversation/entity.py`：`Conversation` 增加 `owner_id: Optional[int]` 字段 + `belongs_to(user_id)` 方法（对齐 FileAsset / Document）
- `infrastructure/models/conversation.py`：`ConversationModel` 增加 owner_id 列 + 索引
- `domain/conversation/repository.py` + `infrastructure/repositories/conversation_repository.py`：`list` / `count` 增加 `owner_id` 过滤 kwarg（对齐 file_asset / document 仓储形状）
- `core/exceptions.py`：`CONVERSATION_NOT_FOUND`、`DOCUMENT_NOT_FOUND` 加入 HTTP 映射 → 404（当前落到默认 400，语义错误）

#### 验收标准

**Happy Path**
- [ ] Conversation 实体带 owner_id 且 belongs_to 判断正确 `验证: pytest tests/test_conversation_ownership.py -k entity → passed`
- [ ] 仓储 list/count 传 owner_id 时只返回该 owner 的会话 `验证: pytest tests/test_conversation_ownership.py -k repo_filter → passed`

**Edge Cases**
- [ ] owner_id 为 NULL 的遗留行不匹配任何用户的 belongs_to / owner 过滤 `验证: pytest tests/test_conversation_ownership.py -k legacy_null → passed`
- [ ] 不传 owner_id 时 list/count 行为与现状一致（内部调用兼容） `验证: pytest tests/test_conversation_ownership.py -k no_filter → passed`

**Error Paths**
- [ ] ConversationNotFoundException 渲染为 HTTP 404（原 400） `验证: pytest tests/test_conversation_ownership.py -k not_found_404 → passed`
- [ ] DocumentNotFoundException 渲染为 HTTP 404（原 400） `验证: pytest tests/test_conversation_ownership.py -k document_404 → passed`

**Integration**
- [ ] migration 0004 可升可降 `验证: cd backend && uv run alembic upgrade head && uv run alembic downgrade 0003 && uv run alembic upgrade head → exit 0`
