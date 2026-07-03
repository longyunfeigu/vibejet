# Conversations & Chat API

会话与聊天模块公共接口。端点无模块前缀（直接挂在 `/api/v1` 下），要求 Bearer 认证，
返回统一业务信封（见 [conventions.md](conventions.md)）。

**归属**：全部会话端点 owner-scoped——创建写 `owner_id=当前用户`，列表只返回自己的会话，
详情/变更/消息/Run/chat 越权 → `CONVERSATION_NOT_FOUND (60001)` / HTTP 404（与不存在同响应）。

## 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/conversations` | 创建会话（title 必填；system_prompt / model / metadata 可选） |
| GET | `/api/v1/conversations` | 分页列表（`page`/`size`/`status`），仅当前用户 |
| GET | `/api/v1/conversations/{id}` | 详情 |
| PATCH | `/api/v1/conversations/{id}` | 更新 title / system_prompt / model |
| DELETE | `/api/v1/conversations/{id}` | 软删除（状态转 archived） |
| GET | `/api/v1/conversations/{id}/messages` | 消息历史（分页） |
| GET | `/api/v1/conversations/{id}/runs` | Run 列表 |
| POST | `/api/v1/conversations/{id}/chat` | 发消息；`stream=true` 走 SSE |

## Chat 行为

- `stream=true`：SSE 事件序列 `message_created → message_delta* → message_complete → run_complete → done`；
  会话不存在/越权/已归档的校验在流开始**之前**完成（4xx，而非 200 断流）。
- `stream=false`：同步返回 `{ message, run }`。
- 已归档会话 → `CONVERSATION_ARCHIVED (60002)`；越权 chat 不产生任何副作用（不落消息、不建 Run、不调 LLM）。
- `message` 长度 1..32000 字符，超限 422（防超大文本直通 LLM/DB）。
- 发消息会刷新会话 `updated_at`（列表按"最近活跃"排序）。

## agent-configs（同 router，无归属）

`/api/v1/agent-configs` CRUD 为共享配置资源，仅要求登录，暂无 owner 边界
（见 conventions.md 鉴权与归属的已知例外）。
