# conversations / messages / runs / agent_configs 表

对话聚合的持久化模型。迁移：baseline `0001` + `20260703_0004_conversations_owner.py`
（补归属列）+ `20260703_0007_index_tuning.py`（索引调优）。
ORM：`backend/infrastructure/models/conversation.py`。

## conversations 列

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| `id` | Integer | PK, autoincrement | 主键 |
| `title` | String(255) | not null | 对话标题 |
| `owner_id` | Integer | nullable | 归属用户（逻辑外键，未强制约束，与 file_assets/documents 一致；NULL 为 0004 迁移前的遗留孤儿行，对所有用户不可见） |
| `system_prompt` | Text | nullable | 系统提示词 |
| `model` | String(100) | nullable | 默认模型 |
| `status` | String(20) | not null, default `'active'` | active / archived |
| `metadata` | JSON | nullable | 扩展元数据（ORM 属性名 `extra_metadata`） |
| `created_at` / `updated_at` | DateTime(tz) | not null, server_default now() | 时间戳 |
| `deleted_at` | DateTime(tz) | nullable | 软删除标记 |

## conversations 索引

- `ix_conversations_owner_updated` (owner_id, updated_at) — 0006 替换 0004 的
  `ix_conversations_owner_created`：列表按 updated_at desc 排序（聊天 bump
  updated_at，最近活跃优先），索引与排序键对齐
- 0007（性能审计索引调优）删除了无查询使用的单列索引
  `ix_conversations_status` / `ix_conversations_created_at`：现有查询全部以
  owner_id 打头，由 owner 复合索引服务

## messages / runs 索引（0007 调优后）

- messages：`ix_messages_conversation_created` (conversation_id, created_at)；
  原单列 `ix_messages_conversation_id` 是复合索引的前缀冗余（messages 为写入
  最频繁表），0007 删除
- runs：`ix_runs_conversation_created` (conversation_id, created_at) — 0007 以
  复合替换单列 `ix_runs_conversation_id`，对齐 list_by_conversation 的
  filter+sort；无查询使用的 `ix_runs_status` 一并删除

## 归属语义（Epic-1）

- 创建即写 `owner_id`；application service 的 route-facing 方法用 `Conversation.belongs_to(owner_id)` 断言归属。
- 可空、不回填是刻意决策（基础库无生产数据；下游各有回填策略），见
  `docs/tasks/plans/2026-07-03-epic-1-ownership-enforcement/decisions.md` D4。
- messages / runs 不带 owner 列：经由 conversation 聚合根访问，归属由聚合根裁决。
- agent_configs 无 owner 语义（共享配置资源，D5）。

## messages / runs / agent_configs

结构见 baseline 迁移 `0001` 与 ORM 定义；本文件仅记录归属相关 delta，
其余列自 0001 起未变化。
