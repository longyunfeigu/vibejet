---
type: bugfix
source_branch: feat/import-voice-agent-delivery
author: edy
services: [backend]
safety: readonly
risk: medium
tools: [api]
---

## 背景与目标
接口出错时，响应信封里的 `message` 是给人看的提示（`backend/core/response.py:74`），前端直接把它显示给用户（`frontend/src/features/auth/helpers/authError.ts:12`）。修复前，有 11 种业务错误把翻译 key 原样当作 `message` 返回，例如 `conversation.not_found`。修复后 `message` 是一句话，按请求语言给中文或英文。

## 入口
- 所有接口都挂在 `/api/v1` 下（`backend/main.py:187`）。本地开发时，前端的 `/api` 请求由 Vite 代理到后端（`frontend/vite.config.ts:29`）。
- `POST /api/v1/auth/login`（`backend/api/routes/auth.py:53`）：用 `e2e-fixture-user-a` 登录，拿到 bearer token。
- `GET /api/v1/auth/me`（`backend/api/routes/auth.py:111`）：不带 token 时报 `auth.required`（抛出处 `backend/api/dependencies.py:151`，定义 `backend/domain/common/exceptions.py:108`）；token 无效时报 `auth.token.invalid`（`backend/domain/common/exceptions.py:120`）。
- `GET /api/v1/conversations/{conversation_id}`（`backend/api/routes/conversations.py:77`）：id 不存在时报 `conversation.not_found`（`backend/domain/conversation/exceptions.py:23`）。
- `GET /api/v1/agent-configs/{config_id}`（`backend/api/routes/conversations.py:188`）：id 不存在时报 `agent_config.not_found`（`backend/domain/conversation/exceptions.py:59`）。
- 语言：查询参数 `?lang=zh` 或请求头 `X-Lang: zh`（`backend/api/middleware/locale.py:89`）；都不传时默认英文（`backend/api/middleware/locale.py:8`）。响应的 `error.locale` 是实际使用的语言。

## 怎么算对
1. [P0] 用 `e2e-fixture-user-a` 的 token 请求 `GET /api/v1/conversations/999999999`（`backend/api/routes/conversations.py:77`；测试账号名下不存在的 id）→ HTTP 404，`code` = `60001`，`error.message_key` = `conversation.not_found`，`message` = `Conversation not found`。
2. [P0] 同一请求加 `?lang=zh` → HTTP 404，`error.locale` = `zh_Hans`，`message` = `对话不存在`。
3. [P0] `GET /api/v1/auth/me`（`backend/api/routes/auth.py:111`）不带 token → HTTP 401，`code` = `30001`，`error.message_key` = `auth.required`，`message` = `Authentication required`；加请求头 `X-Lang: zh` 再请求一次 → `message` = `需要登录`。
4. [P0] `GET /api/v1/auth/me`（`backend/api/routes/auth.py:111`）带请求头 `Authorization: Bearer invalid-token` → HTTP 401，`code` = `30001`，`error.message_key` = `auth.token.invalid`，`message` = `Invalid or expired token`；加 `?lang=zh` 再请求一次 → `message` = `登录凭证无效或已过期`。
5. [P1] 用测试账号的 token 请求 `GET /api/v1/agent-configs/999999999`（`backend/api/routes/conversations.py:188`）→ HTTP 400，`code` = `60005`，`error.message_key` = `agent_config.not_found`，`message` = `Agent config not found`；加 `?lang=zh` → `message` = `Agent 配置不存在`。

## 绝不能坏的底线
- 已经有翻译的错误保持原样：`POST /api/v1/auth/login?lang=zh`（`backend/api/routes/auth.py:53`），用户名 `e2e-fixture-user-a`，配一个错误密码 → HTTP 401，`code` = `20003`，`error.message_key` = `auth.password.invalid`（`backend/domain/common/exceptions.py:77`），`message` = `用户名或密码错误`。

## 前置数据与清理
只读，不建数据。用常驻测试账号 `e2e-fixture-user-a`（见 `_shared/fixtures.md`）登录拿 token。`999999999` 只是测试账号名下不存在的 id，不需要创建，也不需要清理。

## 容易误判的地方
- `message` 是英文不一定是 bug：不传语言时默认英文。想看中文，要显式传 `?lang=zh` 或 `X-Lang: zh`，并确认 `error.locale` 是 `zh_Hans`。
- 环境没编译翻译文件时，修复后英文仍然正确（兜底返回默认英文），但中文也会变成英文。分辨办法：已经有翻译的 `auth.password.invalid` 在 `?lang=zh` 下如果也返回英文 `Invalid username or password`，说明是翻译没编译。这是部署问题（镜像构建时编译，`backend/Dockerfile:71`），不是本次修复失效。
- agent 配置不存在时返回 HTTP 400，不是 404。这是现有行为：错误码 `60005` 不在错误码到 HTTP 状态的映射里。和本次修复无关。
- 判断是哪种错误，看 `code` 和 `error.message_key`，不要看 `message` 的文字。

## 本次改动
- 中英两份翻译表各补了 11 个 key，从第 231 行开始：`backend/locales/en/LC_MESSAGES/messages.po`、`backend/locales/zh_Hans/LC_MESSAGES/messages.po`。
- 业务异常处理器：翻译表里没有这个 key 时，退回异常自带的英文默认文案，不再返回 key 本身（`backend/core/exceptions.py:93`）。
- 非流式聊天在大模型调用失败时，`message` 固定为 `LLM provider error`，不再带上游报错原文（`backend/application/services/chat_service.py` 的 `send_message_sync`）。要触发它得让大模型调用失败，所以不列为验证项；证据是单测 `test_sync_llm_failure_does_not_return_upstream_error_text`。
- 新增测试 `backend/tests/test_i18n_message_keys.py`：代码里用到的每个 key，都必须在每份翻译表里有条目。
- 部署前提没变：镜像构建时编译翻译（`backend/Dockerfile:71`）。

## 深度提示
- 本次补的另外 7 个 key 要构造特定状态才能触发：`conversation.archived`、`run.not_found`、`agent_config.name.exists`、`llm.provider.error`、`llm.timeout`、`idempotency.key.reused`、`idempotency.in_progress`。例如归档一个会话，或重复使用同一个 Idempotency-Key。想多测，就建 `e2e-` 前缀的临时会话，测完删掉。
- `agent_config.name.exists` 的文案里带名字：`Agent config name '<名字>' already exists`。
- 同类问题还可能出在 `HTTPException` 路径：它不经过翻译（`backend/core/exceptions.py:149`），例如 FastAPI 自带的 `Not Found`。不在本次范围内。

## 旧版本的错误现象

| 请求 | HTTP | 旧版本的 `message` |
|---|---|---|
| `GET /api/v1/auth/me`，不带 token | 401 | `auth.required` |
| `GET /api/v1/auth/me`，token 无效 | 401 | `auth.token.invalid` |
| `GET /api/v1/conversations/999999999`（测试账号） | 404 | `conversation.not_found` |
| 同上，加 `?lang=zh` | 404 | `conversation.not_found`（`error.locale` 已经是 `zh_Hans`，文案仍然是 key） |

## 修复后应有的现象

| 请求 | HTTP | `message`（默认英文） | `message`（`?lang=zh` 或 `X-Lang: zh`） |
|---|---|---|---|
| `GET /api/v1/auth/me`，不带 token | 401 | `Authentication required` | `需要登录` |
| `GET /api/v1/auth/me`，token 无效 | 401 | `Invalid or expired token` | `登录凭证无效或已过期` |
| `GET /api/v1/conversations/999999999`（测试账号） | 404 | `Conversation not found` | `对话不存在` |
| `GET /api/v1/agent-configs/999999999`（测试账号） | 400 | `Agent config not found` | `Agent 配置不存在` |

## 根因
异常处理器只认翻译表，查不到就把 key 当文案返回；而这 11 个 key 只写在代码里，从没加进翻译表。
