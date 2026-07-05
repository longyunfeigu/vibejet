# conversations / messages / llm_runs / agent_configs 表

对话聚合的持久化模型。迁移：init `0001`（`20260704_0001_init.py`，squash 说明见该文件）。
ORM：`backend/infrastructure/models/conversation.py`。

## conversations 列

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| `id` | Integer | PK, autoincrement | 主键 |
| `title` | String(255) | not null | 对话标题 |
| `owner_id` | Integer | nullable | 归属用户（逻辑外键，未强制约束，与 file_assets/documents 一致；NULL 为归属列引入前的遗留孤儿行，对所有用户不可见） |
| `system_prompt` | Text | nullable | 系统提示词 |
| `model` | String(100) | nullable | 默认模型 |
| `status` | String(20) | not null, default `'active'`, CHECK `ck_conversations_status` | active / archived |
| `extra_metadata` | JSON | nullable | 扩展元数据（JSON） |
| `created_at` / `updated_at` | DateTime(tz) | not null, server_default now() | 时间戳 |
| `deleted_at` | DateTime(tz) | nullable | 软删除标记 |

## conversations 索引

- `ix_conversations_owner_updated` (owner_id, updated_at)：列表按 updated_at desc
  排序（聊天 bump updated_at，最近活跃优先），索引与排序键对齐
- 不建单列 `status` / `created_at` 索引（2026-07-03 性能审计结论）：无查询独立
  使用，现有查询全部以 owner_id 打头，由 owner 复合索引服务

## messages / llm_runs 索引

- messages：仅 `ix_messages_conversation_created` (conversation_id, created_at)；
  不另建 conversation_id 单列索引——复合索引前缀已覆盖（messages 为写入
  最频繁表，避免写放大）
- llm_runs：仅 `ix_llm_runs_conversation_created` (conversation_id, created_at)，对齐
  list_by_conversation 的 filter+sort；`status` 无查询使用不建索引

## 归属语义（Epic-1）

- 创建即写 `owner_id`；application service 的 route-facing 方法用 `Conversation.belongs_to(owner_id)` 断言归属。
- 可空、不回填是刻意决策：基础库无生产数据，下游各有回填策略；被拒绝的替代方案是
  非空 + 回填到某个系统用户（会伪造归属语义）。
- messages / llm_runs 不带 owner 列：经由 conversation 聚合根访问，归属由聚合根裁决。
- agent_configs 无 owner 语义（共享配置资源，D5）。

## messages / llm_runs / agent_configs

结构见 init 迁移 `0001` 与 ORM 定义；本文件仅记录归属与索引的设计意图。

- 封闭枚举列均带 CHECK 约束（`ck_messages_role`、`ck_llm_runs_status`），DB 层兜底脏值。
- agent_configs 无 `deleted_at`：共享配置资源，删除即硬删，无恢复语义。
- 约束名统一由 `infrastructure/models/base.py` 的 naming_convention 派生，
  create_all 与迁移建出的名字跨方言一致。
