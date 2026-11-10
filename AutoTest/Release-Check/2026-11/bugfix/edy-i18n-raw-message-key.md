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
接口出错时，响应信封里的 `message` 是给人看的提示（`backend/core/response.py:42`）；前端登录相关的报错会直接显示它（`frontend/src/features/auth/helpers/authError.ts:12`）。修复前，有 11 种业务错误把翻译 key 原样当作 `message` 返回，例如 `conversation.not_found`。修复后 `message` 是一句话，按请求语言给中文或英文。

## 入口
- 所有接口都挂在 `/api/v1` 下（`backend/main.py:187`）。本地开发时，前端的 `/api` 请求由 Vite 代理到后端（`frontend/vite.config.ts:29`）。
- `POST /api/v1/auth/login`（`backend/api/routes/auth.py:54`）：请求体是 `{"username": …, "password": …}`（`backend/application/dto.py:214`），用 `e2e-fixture-user-a` 登录；token 在响应的 `data.access_token`（`backend/application/dto.py:239`）。
- `GET /api/v1/auth/me`（`backend/api/routes/auth.py:111`）：不带 token 时报 `auth.required`（抛出处 `backend/api/dependencies.py:151`，定义 `backend/domain/common/exceptions.py:108`）；token 无效时报 `auth.token.invalid`（`backend/domain/common/exceptions.py:120`）。
- `GET /api/v1/conversations/{conversation_id}`（`backend/api/routes/conversations.py:77`）：id 不存在时报 `conversation.not_found`（`backend/domain/conversation/exceptions.py:23`）。
- `GET /api/v1/agent-configs/{config_id}`（`backend/api/routes/conversations.py:188`）：id 不存在时报 `agent_config.not_found`（`backend/domain/conversation/exceptions.py:59`）。
- 语言的优先级：查询参数 `?lang=zh` > 请求头 `X-Lang: zh`（`backend/api/middleware/locale.py:89`）> `Accept-Language` > 英文（`backend/api/middleware/locale.py:92`）。响应的 `error.locale` 是实际使用的语言。

## 怎么算对
1. [P0] 用 `e2e-fixture-user-a` 的 token 请求 `GET /api/v1/conversations/999999999?lang=en`（`backend/api/routes/conversations.py:77`；测试账号名下不存在的 id）→ HTTP 404，`code` = `60001`，`error.message_key` = `conversation.not_found`，`message` = `Conversation not found`。
2. [P0] 同一请求改成 `?lang=zh` → HTTP 404，`error.locale` = `zh_Hans`，`message` = `对话不存在`。
3. [P0] `GET /api/v1/auth/me?lang=en`（`backend/api/routes/auth.py:111`）不带 token → HTTP 401，`code` = `30001`，`error.message_key` = `auth.required`，`message` = `Authentication required`；去掉 `?lang=en`、加请求头 `X-Lang: zh` 再请求一次 → `message` = `需要登录`。
4. [P0] `GET /api/v1/auth/me?lang=en`（`backend/api/routes/auth.py:111`）带请求头 `Authorization: Bearer invalid-token` → HTTP 401，`code` = `30001`，`error.message_key` = `auth.token.invalid`，`message` = `Invalid or expired token`；改成 `?lang=zh` 再请求一次 → `message` = `登录凭证无效或已过期`。
5. [P1] 用测试账号的 token 请求 `GET /api/v1/agent-configs/999999999?lang=en`（`backend/api/routes/conversations.py:188`；agent 配置没有归属、所有账号共用，这个 id 万一存在就换一个更大的）→ HTTP 400，`code` = `60005`，`error.message_key` = `agent_config.not_found`，`message` = `Agent config not found`；改成 `?lang=zh` → `message` = `Agent 配置不存在`。

## 绝不能坏的底线
- 已经有翻译的错误保持原样：`POST /api/v1/auth/login?lang=zh`（`backend/api/routes/auth.py:54`），用户名 `e2e-fixture-user-a`，配一个错误密码 → HTTP 401，`code` = `20003`，`error.message_key` = `auth.password.invalid`（`backend/domain/common/exceptions.py:77`），`message` = `用户名或密码错误`。

## 前置数据与清理
只读，不建数据。用常驻测试账号 `e2e-fixture-user-a`（见 `_shared/fixtures.md`）登录拿 token。`999999999` 只是测试账号名下不存在的 id，不需要创建，也不需要清理。

## 容易误判的地方
- `message` 是英文不一定是 bug，先看 `error.locale`。用 curl 不传语言时就是英文；用中文浏览器时，`Accept-Language` 会让它变成中文。想稳定拿到中文，显式传 `?lang=zh` 或 `X-Lang: zh`；检查项里的英文期望都显式带了 `?lang=en`，不受浏览器语言影响。
- `error.locale` 是 `zh_Hans`，`message` 却是英文：多半是环境里的翻译文件有问题，不是本次修复失效。分两种情况。已经有翻译的 `auth.password.invalid` 也返回英文 `Invalid username or password`，说明翻译根本没编译；它返回 `用户名或密码错误`，只有本次新增的 key 是英文，说明翻译文件是用修复前的翻译表编译的，已经过期。两种情况都先重新编译翻译（在 `backend/` 下 `pybabel compile -d locales`），再验证。
- 用仓库自带的 `docker-compose.yml` 起的环境，会把宿主机的后端目录挂载进容器（`docker-compose.yml:33`），盖掉镜像里编译好的翻译文件；而翻译文件不进 git，所以这种环境默认没有中文。这是现有的部署问题，不是本次引入的。
- agent 配置不存在时返回 HTTP 400，不是 404。这是现有行为：错误码 `60005` 不在错误码到 HTTP 状态的映射里。和本次修复无关。
- 判断是哪种错误，看 `code` 和 `error.message_key`，不要看 `message` 的文字。

## 本次改动
- 中英两份翻译表各补了 11 个 key，从第 231 行开始：`backend/locales/en/LC_MESSAGES/messages.po`、`backend/locales/zh_Hans/LC_MESSAGES/messages.po`。
- 业务异常处理器：翻译表里没有这个 key 时，退回异常自带的英文默认文案，不再返回 key 本身（`backend/core/exceptions.py:93`）。翻译齐全的环境里走不到这条路径，所以不列为验证项；证据是单测 `test_missing_translation_falls_back_to_default_message_not_the_key`（`backend/tests/test_i18n_message_keys.py:58`）。
- 非流式聊天在大模型调用失败时，`message` 固定为 `LLM provider error`，不再带上游报错原文（`backend/application/services/chat_service.py` 的 `send_message_sync`）。要触发它得让大模型调用失败，所以不列为验证项；证据是单测 `test_sync_llm_failure_does_not_return_upstream_error_text`。
- 修好现有的翻译表校验脚本 `backend/scripts/validate_po.py`，并通过 `backend/tests/test_i18n_message_keys.py` 接进 CI：代码里用到的每个 key，都必须在每份翻译表里有非空译文。两份翻译表的头部也从一行还原成了多行。
- 部署前提没变，以下都不是本次引入的：镜像构建时编译翻译（`backend/Dockerfile:71`），但命令末尾的 `|| true` 让编译失败时被静默跳过；用 `docker-compose.yml` 起的环境，会用宿主机的后端目录盖掉镜像里的翻译文件，所以要先在宿主机上编译。

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
| `GET /api/v1/agent-configs/999999999`（测试账号） | 400 | `agent_config.not_found` |

## 修复后应有的现象

| 请求 | HTTP | `message`（`?lang=en`） | `message`（`?lang=zh` 或 `X-Lang: zh`） |
|---|---|---|---|
| `GET /api/v1/auth/me`，不带 token | 401 | `Authentication required` | `需要登录` |
| `GET /api/v1/auth/me`，token 无效 | 401 | `Invalid or expired token` | `登录凭证无效或已过期` |
| `GET /api/v1/conversations/999999999`（测试账号） | 404 | `Conversation not found` | `对话不存在` |
| `GET /api/v1/agent-configs/999999999`（测试账号） | 400 | `Agent config not found` | `Agent 配置不存在` |

## 根因
异常处理器只认翻译表，查不到就把 key 当文案返回；而这 11 个 key 只写在代码里，从没加进翻译表。
