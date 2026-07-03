# Story 1.2: conversations + chat 端点归属闭环

**As a** 登录用户
**I want** 只能查看和操作自己的会话，别人无法向我的会话发消息
**So that** 我的对话内容不被他人读取，我的账号不为他人的 LLM 调用买单

**依赖**: Story 1.1

## 范围

- `application/services/conversation_service.py`：`create_conversation` 增加必填 `owner_id`（写入实体）；`list_conversations` 增加必填 `owner_id`（强制过滤）；`get/update/delete_conversation`、`list_messages`、`list_runs` 增加必填 `owner_id`（load 后 `belongs_to` 断言，失败抛 `ConversationNotFoundException`）
- `application/services/chat_service.py`：`send_message_stream` / `send_message_sync` 增加必填 `owner_id`，`_start_run` 校验归属（在会话存在性校验之后、落用户消息之前）
- `api/routes/conversations.py` / `api/routes/chat.py`：handler 改为 `current_user: UserDTO = Depends(get_current_user)` 参数形式并传 `owner_id=current_user.id`（agent-configs 端点不动）

#### 验收标准

**Happy Path**
- [ ] 创建会话写入 owner_id=当前用户，owner 全链路可读写（详情/更新/消息/runs/chat） `验证: pytest tests/test_conversation_ownership.py -k owner_full_access → passed`
- [ ] 会话列表只含当前用户的会话 `验证: pytest tests/test_conversation_ownership.py -k list_scoped → passed`

**Edge Cases**
- [ ] owner 访问不存在的会话 ID → 404（与越权同表现） `验证: pytest tests/test_conversation_ownership.py -k missing_id → passed`

**Error Paths**
- [ ] 非 owner 访问他人会话（GET/PATCH/DELETE/messages/runs）→ 404 `验证: pytest tests/test_conversation_ownership.py -k non_owner_404 → passed`
- [ ] 非 owner chat（stream 与 sync）→ 404，且不落用户消息、不创建 Run、不调 LLM `验证: pytest tests/test_chat_ownership.py → passed`

**Integration**
- [ ] chat stream 的归属校验在 StreamingResponse 之前抛出（4xx 而非 200 断流） `验证: pytest tests/test_chat_ownership.py -k before_stream → passed`
