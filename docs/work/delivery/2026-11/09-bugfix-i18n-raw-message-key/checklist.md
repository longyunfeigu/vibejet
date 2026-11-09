# Bug 修复检查清单：错误提示返回原始翻译 key

> 由 `/bug-fix-checklist` 在**无人值守模式**下产出。HUMAN 项的判定是「自动确认，待你审」，每项附依据。

Bug: 11 个业务异常的翻译 key 不在中英翻译表里，接口把 key 原样当作提示返回
Type: T2 — Logic Extension（不冲突）
Generated: 2026-11-09
Design: [design.md](./design.md)
Release-Check: [edy-i18n-raw-message-key.md](../../../../../AutoTest/Release-Check/2026-11/bugfix/edy-i18n-raw-message-key.md)

Root cause: 异常处理器只认翻译表，缺翻译时把 key 当文案返回；而这 11 个 key 没进翻译表
Fix: 补翻译 + 缺翻译时退回默认文案 + 覆盖测试；另外，非流式聊天在大模型调用失败时改成统一文案
Side effects identified: 2 | Analogical fixes bundled: 1（上游报错原文） | Follow-up tasks: 3

---

## 检查清单与结果

### 根因验证

| # | 类型 | 项 | 结果 | 依据 |
|---|---|---|---|---|
| 1 | AUTO | 修复前复现症状 | PASS | 修复前用 curl 实测（design §1 的表）：`/auth/me` → `message='auth.required'`；`/conversations/999999999?lang=zh` → `message='conversation.not_found'`。新测试在旧代码上 3 项 FAILED（两份翻译表缺 key + 兜底） |
| 2 | AUTO | 修复后症状消失 | PASS | 同一组请求的修复后结果见下方证据块；`test_i18n_message_keys.py` 4 passed |
| 3 | HUMAN | 修在根因上，不是压住症状 | PASS（待审） | 根因的两半各有对应的修改：翻译表补齐（两份 `messages.po` 第 231 行起），处理器兜底（`backend/core/exceptions.py:93`）。以后再漏补翻译，覆盖测试会失败 |

修复后证据（经 Vite 代理请求真实前后端，翻译已编译）：

```
GET /api/v1/auth/me（不带 token）               → HTTP 401 code=30001 message='Authentication required'  message_key=auth.required       locale=en
同上 ?lang=zh                                   → HTTP 401 code=30001 message='需要登录'                 message_key=auth.required       locale=zh_Hans
GET /api/v1/auth/me（Bearer invalid-token）     → HTTP 401 code=30001 message='Invalid or expired token' message_key=auth.token.invalid  locale=en
同上 X-Lang: zh                                 → HTTP 401 code=30001 message='登录凭证无效或已过期'       message_key=auth.token.invalid  locale=zh_Hans
GET /api/v1/conversations/999999999（测试账号） → HTTP 404 code=60001 message='Conversation not found'   message_key=conversation.not_found locale=en
同上 ?lang=zh                                   → HTTP 404 code=60001 message='对话不存在'               message_key=conversation.not_found locale=zh_Hans
GET /api/v1/agent-configs/999999999             → HTTP 400 code=60005 message='Agent config not found'   message_key=agent_config.not_found locale=en
同上 ?lang=zh                                   → HTTP 400 code=60005 message='Agent 配置不存在'          message_key=agent_config.not_found locale=zh_Hans
对照：POST /api/v1/auth/login?lang=zh 错误密码   → HTTP 401 code=20003 message='用户名或密码错误'          message_key=auth.password.invalid locale=zh_Hans
```

### 副作用验证

| # | 类型 | 项 | 结果 | 依据 |
|---|---|---|---|---|
| 4 | AUTO | `code`、`message_key`、HTTP 状态不变 | PASS | 修复前后对照：401/30001、404/60001 一致，只有 `message` 变了 |
| 5 | HUMAN | 没有调用方依赖旧的 `message` | PASS（待审） | 前端只展示 `message`（`frontend/src/features/auth/helpers/authError.ts:12`）；在 `frontend/src` 里搜 `message_key`、`auth.required`、`conversation.not_found`、`message ===`、`message ==`，结果为 0 |
| 6 | HUMAN | 调用方传入的文案被统一文案取代 | 待你确认 | 实际只有一处传了自定义文案：非流式聊天把上游报错原文传给 `LLMProviderException`。`UnauthorizedException()` 唯一调用点用默认文案（`backend/api/dependencies.py:151`）；`InvalidTokenException` 的原因放在 `details.reason`，不在 `message` 里 |
| 7 | AUTO | 兜底不会把上游报错原文返回给调用方（本项执行时发现问题，已修） | PASS | 发现：兜底返回 `exc.message`，而非流式聊天把上游报错原文作为 message，没编译翻译的环境会原样返回。修法见 design §3 第 4 点（commit `d2fe08e`）。新测试 `test_sync_llm_failure_does_not_return_upstream_error_text`：旧代码 `1 failed, 5 passed`，新代码 `6 passed` |

### 类比排查验证

| # | 类型 | 项 | 结果 | 依据 |
|---|---|---|---|---|
| 8 | AUTO | 代码里用到的 key 全部有翻译 | PASS | 测试扫描到 43 个 key；`test_every_message_key_in_code_has_a_translation[en]` 和 `[zh_Hans]` 都 PASS |
| 9 | HUMAN | 后续任务：`HTTPException` 路径不翻译（`backend/core/exceptions.py:149`） | 已记录 | vibejet 没有任务跟踪系统，记在 design §4 和本清单 |
| 10 | HUMAN | 后续任务：本地没编译 `.mo` 时，中文退回英文 | 已记录 | 同上。兜底保证至少返回一句英文 |
| 11 | HUMAN | 后续任务：镜像构建时编译翻译失败会被静默跳过（`backend/Dockerfile:71` 末尾的 `\|\| true`） | 已记录 | Babel 是运行时依赖（`backend/pyproject.toml:243`），正常会编译成功；但失败时构建不会报错 |

### 回归（T2）

| # | 类型 | 项 | 结果 | 依据 |
|---|---|---|---|---|
| 12 | AUTO | 受影响模块的测试 | PASS | i18n、参数校验错误、登录、会话归属：22 passed；聊天服务：6 passed |
| 13 | AUTO | 全量后端测试：`uv run pytest` | PASS | 166 passed, 2 skipped（跳过的两项依赖没装的可选包 documents、anthropic） |
| 14 | AUTO | 真实端到端：`npm run test:all:local` | PASS | 7 passed（10.7s） |
| 15 | HUMAN | 原来坏掉的主流程现在正确 | PASS（待审） | 症状在接口响应字段上，已经通过 Vite 代理请求真实前后端验证（见证据块）。没有做浏览器点测 |

### 架构合规

| # | 类型 | 项 | 结果 | 依据 |
|---|---|---|---|---|
| 16 | AUTO | 没有新增 `print()` | PASS | `git diff 244609f..HEAD -- backend \| grep -c '^+.*print('` → 0 |
| 17 | AUTO | 新函数都有类型标注 | PASS | 对改动的文件跑 mypy：`no issues found` |
| 18 | AUTO | CI 对改动文件的整套 lint + 依赖方向契约 | PASS | black、isort、flake8、mypy、bandit 全部通过；`lint-imports` 5 kept, 0 broken。CI 只 lint 改动过的文件，所以一旦改动，这两个文件原有的 black/isort/mypy 违规就会暴露。本次顺带清理了 |

---

Total: 18 · AUTO: 11 | HUMAN: 7

## Gate Decision

- AUTO：11 PASS / 0 FAIL / 0 WARNING
- HUMAN：3 PASS（待审）/ 1 待你确认（#6，行为变化）/ 3 已记录的后续任务
- Gate：**PASS（自动确认，待你审）**。#6 是产品取舍：大模型调用失败时，响应不再带上游原文。如果你希望保留原文，就 revert `d2fe08e`，同时要接受「没编译翻译时原文会返回给调用方」。

复盘备注：
- 这个 bug 能存活，是因为测试只断言 `code`，不断言 `message`。建议在 T2 清单模板里加一项：错误响应类的改动，测试要断言 `message`，不能只断言 `code`。
- 兜底这种「失败时退回 X」的改动，要回头检查 X 的所有来源。第 7 项就是这样查出来的。

---

## Decision Log

### 自动确认的关卡

- Step 1（清单）、Step 2（AUTO 结果）、Step 3（HUMAN 项）、Step 4（Gate）：`Gate: auto-confirmed — pending user review`。
- Step 5.1：验证指导放在 `2026-11` 目录，作者 `edy`。默认文件名按分支生成，是 `edy-import-voice-agent-delivery.md`；但这个分支同时承载第一次试跑，用这个名字会误导，所以改用和本目录同一个 slug：`edy-i18n-raw-message-key.md`（满足 lint `path` 规则：作者开头）。

### Step 2 — 第 7 项发现上游报错原文外泄 — Decision Discussion

**Decision point (option comparison)**：保持原样 / 调用点改成默认文案 / 处理器加白名单。
**Rationale**：外泄发生在调用点，就在调用点修；上游原文已经记进日志和 run 记录。详见 design 的 Decision Log。
**Decision**：调用点改成默认文案（`d2fe08e`）。`Gate: auto-confirmed — pending user review`。
