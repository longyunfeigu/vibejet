# 技术设计 — Bug 修复：错误提示返回原始翻译 key

> 由 `/bug-fix-design` 在**无人值守模式**下产出。所有关卡都是「自动确认，待你审」，见文末 Decision Log。

| 关卡 | 结论 | 依据 |
|---|---|---|
| Pre-Step A 根因 | 见 §2 | 修复前实测（§1）+ 代码 + 翻译表比对 |
| Pre-Step B 修法 | 方案 C：补翻译 + 兜底 + 覆盖测试；检查清单阶段回改一次（不外泄上游报错） | 见 §3 与 Decision Log |
| Pre-Step C 类比排查 | 见 §4 | 扫描了代码里全部 43 个 key 和 4 个异常处理器 |
| Step 2 分级 | **T2 逻辑扩展**（不冲突） | 只改一个处理函数和两份翻译表 |

Bug: 11 个业务异常的翻译 key 不在中英翻译表里，接口把 key 原样当作提示返回
Type: T2
Date: 2026-11-09
Status: Confirmed（自动确认，待审）
Branch: `feat/import-voice-agent-delivery`（voice-agent 交付链的第二次试跑；可以单独拆出去合并）

---

## 1. 背景

跑 AutoTest E2E 时发现：错误响应的 `message` 字段是 key，而不是一句话。修复前实测（本地，翻译已编译）：

| 请求 | HTTP | `message` | `message_key` | locale |
|---|---|---|---|---|
| `GET /api/v1/auth/me`，不带 token | 401 | `auth.required` | `auth.required` | en |
| `GET /api/v1/auth/me`，`Authorization: Bearer invalid-token` | 401 | `auth.token.invalid` | `auth.token.invalid` | en |
| `GET /api/v1/conversations/999999999`（测试账号） | 404 | `conversation.not_found` | `conversation.not_found` | en |
| 同上加 `?lang=zh` | 404 | `conversation.not_found` | `conversation.not_found` | zh_Hans |
| 对照：密码错误，加 `?lang=zh` | 401 | `用户名或密码错误` | `auth.password.invalid` | zh_Hans |

前端直接把 `message` 显示给用户（`frontend/src/features/auth/helpers/authError.ts`）。

## 2. 根因（Pre-Step A）

**共同模式**：异常处理只认翻译表。翻译缺失时，它把 key 当作文案返回，异常类自带的英文默认文案被丢掉。

1. **现象**：`message` 等于 key。
2. **根因**：
   - `backend/core/exceptions.py` 的 `business_exception_handler` 执行 `t(message_key or exc.message, **params)`；`backend/core/i18n.py` 的 `t()` 查不到时返回 msgid，也就是 key 本身。
   - 有 11 个 key 只登记在代码里，两份翻译表（`backend/locales/{en,zh_Hans}/LC_MESSAGES/messages.po`）里都没有：`auth.required`、`auth.token.invalid`、`conversation.not_found`、`conversation.archived`、`run.not_found`、`agent_config.not_found`、`agent_config.name.exists`、`llm.provider.error`、`llm.timeout`、`idempotency.key.reused`、`idempotency.in_progress`。
3. **为什么没早发现**（审查阶段更正：初稿写的「没有任何检查」是错的）：其实有检查。`backend/scripts/validate_po.py` 会核对代码里用到的每个 key 在每份翻译表里都有非空译文，挂在 pre-commit 上。但它一直是坏的：两份翻译表的头部被写成了一行，polib 解析失败；就算能解析，它的正则也会把 `get("x")` 这类调用误认成 key。CI 又不跑 pre-commit，所以一直没人发现。另外，测试环境不编译 `.mo`，`t()` 总是返回 key，而现有测试只断言 `code`、不断言 `message`。
4. **孤立还是模式**：是模式。新增异常时漏补翻译，这种漂移还会继续发生。

## 3. 修复方案（Pre-Step B）

> **一句话**：补齐翻译，缺翻译时退回默认文案，再用测试把「代码里的 key 必须有翻译」锁住。

1. **补翻译**：两份 `.po` 各加 11 条。英文 msgstr 和异常类自带的英文默认文案逐字一致（`agent_config.name.exists` 用 `{name}` 占位，值来自异常的 `details`），所以不论编译与否，英文结果都一样。
2. **兜底**：`business_exception_handler` 在翻译缺失（`t()` 返回值等于 key）时，退回 `exc.message`。
3. **防复发**（审查阶段回改）：不再另写扫描，而是修好现有的 `backend/scripts/validate_po.py` 并接进 CI。具体做了四件事：把两份翻译表的头部还原成多行；正则加单词边界；扫描时排除 `tests/`；把 `main` 拆成几个小函数，满足 CI 的复杂度上限。`backend/tests/test_i18n_message_keys.py` 直接调用它的 `main()`，所以 CI 的 pytest 会跑到它。pre-commit 改成和相邻钩子一样用 `uv run` 调用。兜底行为也在同一个测试文件里测。
4. **不外泄上游报错**（检查清单阶段补上）：非流式聊天在大模型调用失败时，抛默认文案的 `LLMProviderException()`，上游报错原文只留在日志和 run 记录里（`backend/application/services/chat_service.py` 的 `send_message_sync`）。原因：兜底返回 `exc.message`，而这里的 message 原本是上游报错原文，没编译翻译的环境会把它原样返回给调用方。审查指出：run 记录的 `error_message` 会通过 `GET /api/v1/conversations/{id}/runs` 返回给会话所有者，所以上游原文其实仍然能被看到。这是早就存在的问题，列为后续任务（§4）。

**副作用**

- **调用方是否依赖旧行为**：前端只展示 `message`；机器判断应该看 `code` 和 `message_key`，这两个不变。没有找到依赖旧行为的调用方。
- **自定义文案被统一文案取代**：`LLMProviderException` 和 `UnauthorizedException` 都接受调用方传入的文案，但实际只有一处传了：非流式聊天把上游报错原文传给 `LLMProviderException`。`UnauthorizedException()` 的唯一调用点用的是默认文案（`backend/api/dependencies.py:151`）。修复前这里返回的是 key，调用方从没见过上游原文；修复后统一返回「LLM provider error」，第 4 点保证没编译翻译时也一样。这是行为变化，列为待审决策。
- **数据迁移**：不需要。
- **可回滚**：可以，revert 这个 commit 即可。
- **最坏情况**：某条翻译写错，提示文案不对；`code`、`message_key`、HTTP 状态都不受影响。

## 4. 类比排查（Pre-Step C）

模式：**key 只登记在代码里，没有同步进翻译表；或者某条错误路径根本不经过翻译。**

| 位置 | 查了吗 | 结果 | 处理 |
|---|---|---|---|
| 代码里全部 `message_key` / `t()` 字面量（43 个） | 是 | 11 个缺翻译，其余 32 个齐全 | 本次补齐 |
| `validation_exception_handler`（`validation.failed`）、`global_exception_handler`（`error.internal`） | 是 | 翻译存在 | 无 |
| `http_exception_handler` | 是 | 不经过翻译，直接返回 `exc.detail`（例如 FastAPI 自带的英文） | **后续任务**：是否翻译 HTTPException 需要单独决定 |
| 本地没编译 `.mo` | 是 | 所有 key 原样返回 | 兜底缓解（返回英文默认文案）；启动时自动编译列为**后续任务** |
| 兜底返回 `exc.message` 时，它会不会是上游原文 | 是（检查清单阶段补查） | 非流式聊天把上游报错原文作为 message | 本次修复（§3 第 4 点） |
| 镜像构建时编译翻译 | 是 | Babel 是运行时依赖（`backend/pyproject.toml:243`），镜像构建时会编译（`backend/Dockerfile:71`）；但命令末尾的 `\|\| true` 会让编译失败被静默跳过 | **后续任务**：编译失败应让构建失败 |
| 用 `docker-compose.yml` 起的环境 | 是（独立验证时发现） | 后端目录挂载进容器（`docker-compose.yml:33`），盖掉镜像里编译好的翻译文件；翻译文件被 `.gitignore` 和 `backend/.dockerignore` 排除。所以 compose 环境默认没有中文；修复前它的所有错误都返回 key，修复后返回英文默认文案 | **后续任务**：compose 环境启动时编译翻译 |
| run 记录里的上游报错原文 | 是（审查发现） | 两处大模型失败的收尾都把 `str(exc)` 写进 run 的 `error_message`，`GET /api/v1/conversations/{id}/runs` 会把它返回给会话所有者 | **后续任务**：改成清洗过的文案（参照 `document_service` 的做法），原文只进日志。这会改变 runs 接口返回的内容，触发 strict，所以不在本次做 |
| gRPC 错误处理 | 是（审查发现） | `backend/grpc_app/interceptors/exceptions.py:99`、`:102` 不经过翻译 | **后续任务** |
| 翻译表校验脚本本身 | 是（审查发现） | `validate_po.py` 头部解析失败，正则误报。修好后仍有盲区：换行写在括号里的 `message_key=(...)`、`message_key=x or "key"`、经变量传递的 key；也不检查 fuzzy 条目和中英占位符是否一致 | 头部和正则本次修；盲区列为**后续任务** |
| 前端是否用 `message` 做逻辑判断 | 是 | 只展示，不做判断 | 无 |

## 5. 影响面

- 文件：`backend/core/exceptions.py`；`backend/locales/en/LC_MESSAGES/messages.po`；`backend/locales/zh_Hans/LC_MESSAGES/messages.po`；新增 `backend/tests/test_i18n_message_keys.py`；`backend/application/services/chat_service.py`（`send_message_sync`）；`backend/tests/test_chat_service_stream.py`（加一个用例）；`backend/scripts/validate_po.py`；`.pre-commit-config.yaml`；`backend/tests/README.md`；两份 `messages.po` 的头部
- 模块：后端 core（异常处理）、i18n 翻译表
- 接口：所有接口错误响应的 `message` 字段，只改它的值；`code`、`message_key`、HTTP 状态不变
- 关键路径：鉴权失败、资源不存在等错误路径，只改提示文本

**strict 触发判断**：改的是错误响应的展示文本，不改信封结构、错误码和状态码，所以不视为公共 API 契约变化。这是待审的假设。

## 6. 提交计划

1. `fix(i18n): ...` —— 处理函数兜底 + 两份翻译表 + 覆盖测试
2. `fix(chat): ...` —— 非流式大模型调用失败时，不返回上游报错原文 + 测试
3. `docs(delivery): ...` —— 本设计的回改、检查清单、Release-Check 验证指导
4. `fix(i18n): ...` —— 审查阶段：改用现有的 `validate_po.py`，修好它并接进 CI
5. `docs(delivery): ...` —— 审查报告，以及文档的回改

---

## Decision Log

### 自动确认的关卡

- Pre-Step A / B / C、Step 1、Step 2：`Gate: auto-confirmed — pending user review`。

### Pre-Step B — 修法 — Decision Discussion

**Decision point (option comparison)**：
- A 只补翻译：修掉现象，但不防复发。
- B 只加兜底：不再漏出 key，但缺翻译时中文用户看到英文。
- C 补翻译 + 兜底 + 覆盖测试：漂移由机器检查拦住，漏网的 key 至少显示一句英文。
- D 启动时自动编译 `.mo`，或把 `.mo` 提交进仓库：解决「没编译」那一层，代价是运行期依赖 Babel 或提交构建产物。
- E（审查阶段补上）修好仓库里现有的 `validate_po.py` 并接进 CI。初稿不知道它存在，所以没列。

**Rationale**：根因是漂移，只有 C 用一条会失败的检查锁住它（vibejet 原则：「把散文规则升格为会失败的检查」）。D 解决的是另一层问题，而且有代价，列为后续任务。
**Decision**：C；其中「覆盖测试」在审查阶段改成 E，同一个能力只留一份实现。`Gate: auto-confirmed — pending user review`。

### Pre-Step B — 自定义文案被统一文案取代 — Decision Discussion

**Decision point**：保留调用方传入的文案（不给这两个 key 补翻译）/ 使用统一文案（补翻译）。
**Rationale**：上游 LLM 的报错文本可能带内部信息，统一文案更安全；具体信息在日志里（`llm_generate_failed`）。
**Decision**：使用统一文案。`Gate: auto-confirmed — pending user review`（行为变化，请你确认）。

### Pre-Step B（检查清单阶段回改）— 兜底与上游报错原文 — Decision Discussion

**Decision point (option comparison)**：
- 保持原样：非流式聊天继续把上游报错原文作为 message。没编译翻译的环境会把原文返回给调用方。
- 调用点改成默认文案：`send_message_sync` 抛 `LLMProviderException()`，原文只进日志和 run 记录。
- 处理器加白名单，只对部分异常兜底：要让 core 知道每个异常的情况，而问题出在调用点。

**Additional context**：检查清单第 7 项（副作用）查兜底时发现。修复前这里返回的是 key，所以调用方从没见过上游原文；改调用点只是保住这个事实。
**Rationale**：泄露发生在调用点，就在调用点修。上游原文已经记进日志（`llm_generate_failed`）和 run 记录，排查不受影响。
**Decision**：调用点改成默认文案。`Gate: auto-confirmed — pending user review`。

### 审查阶段 — 改用现有检查 — Decision Discussion

**Decision point (option comparison)**：
- 保留新写的扫描测试，旧脚本不管：仓库里会有两份同样的检查，而且新的那份更弱（不查空译文，漏掉换行写的 key），违反「每种能力只留一个 canonical 实现」。
- 删掉新扫描，修好旧脚本并接进 CI：只有一份实现；pytest 调用它，所以 CI 能跑到。

**Additional context**：修旧脚本时又发现，它的正则会把 `get("x")` 误认成 key，修之前会报 75 个假的缺失。
**Rationale**：AGENTS.md 的策展纪律：新增之前，先找已有的实现来扩展。
**Decision**：删掉新扫描，修好旧脚本。`Gate: auto-confirmed — pending user review`。

### 审查阶段 — run 记录里的上游原文 — Decision Discussion

**Decision point**：本次一起修 / 列为后续任务。
**Rationale**：问题早就存在，不是本分支引入的。修它会改变 runs 接口返回的内容，按 AGENTS.md 会触发 strict，应该单独决策。
**Decision**：列为后续任务；同时更正 §3 第 4 点和检查清单 #7 里「run 记录只在内部」的错误假设。`Gate: auto-confirmed — pending user review`。
