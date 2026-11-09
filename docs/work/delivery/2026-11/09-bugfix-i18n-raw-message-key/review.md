# Code Review Report

**Change**: `feat/import-voice-agent-delivery`（只审 `244609f..HEAD` 的 4 个 commit：`08aa3bc` `526dd47` `d2fe08e` `00d387e`）→ `master`
**Change type**: bug fix
**Design document**: `docs/work/delivery/2026-11/09-bugfix-i18n-raw-message-key/design.md`
**Date**: 2026-11-09
**模式**：无人值守，由 `delivery-code-review` 执行。每个关卡都自行裁决，并标注 `Gate: auto-confirmed — pending user review`。

---

## 结论先行

- **0 CRITICAL、7 WARNING、9 INFO**。按本 skill 的定义 Verdict = **PASS**：没有阻断合并的问题。
- 核心修复是对的。11 个 key 已补进两份翻译表，`pybabel compile` 能通过，中英文都能渲染出来。处理器在缺翻译时退回默认文案，逻辑覆盖所有 `BusinessException` 子类，`{name}` 占位符也正确。新测试在修复前的代码上确实会失败。
- 合并前有两件事要么修，要么由你明确接受：
  1. **上游大模型的报错原文仍会返回给调用方**，走的是 `GET /api/v1/conversations/{id}/runs` 的 `error_message` 字段，所以 checklist #7 的 PASS 不成立（C1）。这不是本分支引入的问题，但 `d2fe08e` 的目的就是堵这个口子，现在只堵了一半。
  2. **仓库里早有一个做同样检查的脚本**：`backend/scripts/validate_po.py`，挂在 pre-commit 上。它一直是坏的，因为翻译表第 5 行的头部格式错误。设计里"没有任何检查"的说法不对；本次又造了第二个检查，而且比旧脚本弱（C2、C3、C4、D-W1）。

## Review Context

```
Design document: docs/work/delivery/2026-11/09-bugfix-i18n-raw-message-key/design.md
Target branch: master（Gate: auto-confirmed — pending user review。分支上 244609f 及之前的 commit 属于另一项改动，按任务要求排除；Step 3 实际使用的 diff 范围是 244609f..HEAD）
Change type: bug fix（文件名含 bugfix）
Current branch: feat/import-voice-agent-delivery
工作区未提交改动：无
```

## 本次复核的证据（都是我自己重跑的，不是引用 checklist）

| 检查 | 命令 / 方法 | 结果 |
|---|---|---|
| 新测试与改动的测试 | `uv run --python 3.11 pytest tests/test_i18n_message_keys.py tests/test_chat_service_stream.py` | 10 passed |
| 新测试在旧代码上会失败 | `git archive 244609f backend` 解到临时目录，拷入两个新测试文件后用同一个 venv 运行 | 4 failed：覆盖测试 `[en]`、`[zh_Hans]`，兜底测试，非流式 LLM 测试 |
| 全量后端测试 | `uv run --python 3.11 pytest` | 166 passed, 2 skipped |
| 分层契约 | `uv run --python 3.11 lint-imports` | 5 kept, 0 broken |
| CI 对改动文件的 lint | black / isort / flake8 / mypy / bandit，参数与 `ci.yml` 一致，覆盖 4 个改动的 .py | 全部通过 |
| 翻译表能否编译 | `pybabel compile -i <po> -o /tmp/...`，en 和 zh_Hans 各一次 | 两份都是 82/82；用 `gettext` 读出的 11 条新条目正确，含 `{name}` |
| 处理器行为 | 内存 FastAPI + 8 种异常 × en/zh × 编译/未编译 | 编译时中英正确；未编译时退回 `exc.message`，没有 key 外漏 |
| 旧检查脚本 | `uv run --python 3.11 python scripts/validate_po.py` | exit 1：两份 po 第 5 行 `unescaped double quote found`（244609f 时已经如此） |
| 上游原文去向 | 用测试里的 `_FailingGenerateLLM` 调 `send_message_sync` | 响应 message = `LLM provider error`；`RunDTO.error_message` = `upstream 401 from https://llm-gateway.internal/v1` |
| 语言解析 | 进程内对真实 `main.app` 用 `TestClient` 请求 `/api/v1/auth/me` | 只带 `Accept-Language: zh-CN,zh;q=0.9` → `需要登录`, `locale=zh_Hans` |
| Release-Check lint | `npm run lint:release-check` | 1 份指导，0 错误，0 警告 |
| 指南里的 file:line | 20 处逐行 `sed -n` 核对 | 全部指向所述代码 |
| 设计中的数字 | 用测试自身的扫描函数，对照 244609f 的 po | 43 个 key，两份 po 各缺 11 个，名单与设计一致 |

---

## Design Review Result

CRITICAL: 0 | WARNING: 2 | INFO: 4

### Step 1: Design Document Review

Document: `docs/work/delivery/2026-11/09-bugfix-i18n-raw-message-key/design.md`

#### 1a: Required Sections

| Section | Status | Finding |
|---------|--------|---------|
| Feature / problem description | PRESENT | §1 用修复前的实测表说清了现象 |
| Background and motivation | PRESENT | AutoTest E2E 发现；前端直接展示 `message` |
| Change plan | PRESENT | §3 四点，具体到函数和文件 |
| Key logic | PRESENT | 兜底条件"`t()` 返回值等于 key"讲清楚了，也说明了 en 的 msgstr 与默认文案逐字一致 |
| Modules / files affected | PRESENT | §5 列出了文件路径 |
| Risks and trade-offs | PRESENT | 列了副作用、最坏情况和回滚方式 |
| Test and acceptance criteria | THIN | 设计里只有修复前的值；修复后的期望值只在 checklist 和指南里，设计也没有链接过去（I-D1） |
| Non-functional requirements | THIN | 没有性能和数据量的说明，即使是"可忽略"也该写一句；安全只在 LLM 那一点上谈到（I-D2） |
| Data model / API definitions | PRESENT | §5 写明只改 `message` 的值，`code`、`message_key`、HTTP 状态不变，并给出不触发 strict 的理由 |
| Root cause analysis | PRESENT | 有完整链路：handler → `t()` 返回 msgid → 11 个 key 缺翻译 |
| Why not caught earlier | PRESENT，但事实错误 | 见 D-W1 |
| Analogical investigation | THIN | 漏了 3 处，见 D-W2 |

#### 1b: Self-containment Findings

- [INFO] I-D3 顶部关卡表 / §3：「方案 C」在 Decision Log 定义之前就出现了；「T2 逻辑扩展」没有解释；「vibejet 原则：把散文规则升格为会失败的检查」没有注明出处（实际出自 AGENTS.md：「写'必须'的规则要有会失败的检查兜底」）。冷读者需要回翻或猜。

#### 1c: Decision Quality Findings

- [WARNING] **D-W1** `design.md:42`（§2 第 3 点）与 Pre-Step B 决策：「没有任何检查保证代码里用到的 key 在翻译表里存在」**不成立**。
  - 事实：`backend/scripts/validate_po.py:36-80` 做的正是这件事。它扫描 `t("…")` 和 `message_key="…"`，要求每份 po 都有对应条目，还额外检查空 msgstr（`:67`）。它通过 `.pre-commit-config.yaml:120-125` 挂在每次 commit 上。
  - 为什么它没拦住：两份 `messages.po` 第 5 行把头部的换行写成了字面量 `\n"`，polib 解析直接报错。所以这个 hook 对**每一次** commit 都以 exit 1 失败，大家只能跳过或不装 hook。CI（`.github/workflows/ci.yml`）又不跑 pre-commit。这才是"为什么没早发现"的真实原因：规范的检查本来存在，但已经失效，而且不在 CI 里。
  - 后果：决策选项 A–D 里缺了最直接的一项："修好并接入已有检查"。结果仓库里多了第二个检查（见 C2）。
  - 建议：改写 §2 第 3 点，在 §4 加一行，在决策里补上这个选项并说明取舍；checklist 开头的根因段也要同步改。
  - `Gate: auto-confirmed — pending user review`：我判为 WARNING 而不是 CRITICAL。产品层面的根因（缺翻译，加上处理器把 key 当文案）判断正确，修复也对；错的是"为什么没被拦住"这一层，影响的是维护，不是正确性。
- [WARNING] **D-W2** §4 类比排查漏了 3 处：
  - (a) 「兜底返回 `exc.message` 时，它会不会是上游原文」这一行只查了响应里的 message，没继续追上游原文最后去了哪里。原文写进了 `Run.error_message`，再经 `GET /conversations/{id}/runs` 返回给调用方（见 C1）。Decision Log 的依据「上游原文已记进日志和 run 记录，排查不受影响」是把 run 记录当成了内部数据，这个前提不成立。
  - (b) 设计说扫描了「4 个异常处理器」，但 gRPC 拦截器 `backend/grpc_app/interceptors/exceptions.py:99,102` 是第 5 个渲染 `BusinessException` 的地方。它直接用 `exc.message`，从不翻译，这一点没记录。目前 gRPC 没有聊天服务，所以没有上游原文外泄，但同类排查应该列出来。
  - (c) 语言解析还会读取 `Accept-Language`（`backend/api/middleware/locale.py:8`、`:89-92`），设计和指南都按"不传就是英文"处理（见 G1）。
- [INFO] I-D4 `design.md:113`：「`details` 仍保留具体信息」在 `d2fe08e` 之后已经不成立。`LLMProviderException()` 不带 `details`，上游信息只在日志里（以及 C1 说的 run 记录里）。
- 其他决策：方案 C 与 A/B/D 的对比、调用点修复与处理器白名单的对比都有替代方案和理由，推理成立。

### Design Review Result

CRITICAL: 0 | WARNING: 2 | INFO: 4（含 1a 的 I-D1、I-D2）

Design review PASSED — proceeding to code review.（`Gate: auto-confirmed — pending user review`）

---

## Code Review Result

### Step 2: Code Review

Files reviewed（每个都读了全文，并追了调用方）：
- `backend/core/exceptions.py`，关联：`backend/core/i18n.py`、`backend/core/response.py`、`backend/domain/common/exceptions.py`、`backend/domain/conversation/exceptions.py`、`backend/domain/document/exceptions.py`、`backend/api/middleware/locale.py`、`backend/grpc_app/interceptors/exceptions.py`
- `backend/locales/en/LC_MESSAGES/messages.po`、`backend/locales/zh_Hans/LC_MESSAGES/messages.po`
- `backend/tests/test_i18n_message_keys.py`，关联：`backend/scripts/validate_po.py`、`.pre-commit-config.yaml`、`.github/workflows/ci.yml`、`backend/babel.cfg`
- `backend/application/services/chat_service.py`，关联：`backend/application/dto.py`、`backend/application/services/conversation_service.py`、`backend/api/routes/conversations.py`、`backend/domain/conversation/entity.py`、`backend/infrastructure/external/llm/openai_provider.py`、`backend/application/services/document_service.py`
- `backend/tests/test_chat_service_stream.py`、`backend/tests/README.md`
- 所有带 `message_key` 的抛出点：`idempotency_service.py`、`file_asset_service.py`、`document_service.py`、`domain/*/entity.py`

#### 2a: Standards Compliance

- [INFO] **C5** `backend/core/exceptions.py:5-19,76-78,124-126`、`backend/application/services/chat_service.py:226`：与修复无关的 import 重排、black 折行和 `int(...)` 包裹，会碰到 AGENTS.md「不重排无关代码」的红线。但理由是真的：CI 只 lint 改动过的文件，一碰这个文件，旧违规就会让 CI 失败。commit 里也带了 `Constraint:` trailer，我复跑的五项 lint 全部通过。可以接受，只是让 diff 噪音变大。
- [INFO] **C6** `backend/tests/README.md:20`：文件索引没有更新。新文件 `test_i18n_message_keys.py` 不在表里；`test_chat_service_stream.py` 那一行仍写「SSE 流式聊天」，而文件头已改成「流式/非流式」。两个文件头都写着"一旦我被更新…务必更新所属文件夹的 md"。建议补两行。
- 没有其他问题：没有 `print`；`lint-imports` 通过；没有新增端点或输入边界；commit 信息是祈使句，并带 `Constraint:` / `Rejected:` / `Not-tested:` trailer。
- review-checklist 的最小七问：分层 ✓，越权（`/runs` 本身按 owner 隔离，本次未改）✓，并发 N/A，副作用（先把 run 置为失败再抛异常，顺序未变）✓，外部输入 N/A，只测 happy path？否 ✓，静默吞错（没有新增）✓。

#### 2b: Functional Correctness

- 处理器兜底（`backend/core/exceptions.py:90-94`）我逐一核对了所有子类，没有发现正确性问题：
  - 有 key、编译了 .mo：返回译文。`agent_config.name.exists` 的 `{name}` 取自 `details`，中英都正确；名字里带 `{}` 也安全，因为 `str.format` 不会二次解析参数值。
  - 有 key、没编译或缺条目：`t()` 返回 key（无占位符时 format 不会改变它），条件命中，退回 `exc.message`。
  - 没有 key：行为与修复前一致。
  - `RateLimitException(None)` 的 `format_params={}` 走无参分支，结果正确。
- [INFO] **C10** `backend/core/exceptions.py:93-94`：在没编译 .mo 的环境里，兜底对**所有**异常返回 `exc.message`。`DomainValidationException` 会因此返回 `Invalid run status: x` 这类内部 f-string（`domain/conversation/entity.py:36`）；文档相关校验会对英文用户返回中文（`application/services/document_service.py:83`、`domain/document/entity.py:47`）。修复前这些环境返回的是 key，现在是可读但没有本地化的文本，属于设计内的取舍，记一笔即可，不需要改。

#### 2c: Implementation Simplicity

- [WARNING] **C2** `backend/tests/test_i18n_message_keys.py:20-47` 与 `backend/scripts/validate_po.py:36-80`、`.pre-commit-config.yaml:118-125`：**同一个能力有两份实现**，而且新的那份更弱（旧脚本还检查空 msgstr）。
  - 旧脚本没修也没删，在 HEAD 上仍然 exit 1，原因是两份 po 第 5 行的头部格式错误。所以 pre-commit hook 对每次 commit 都失败，等于逼所有人跳过 hook。
  - 这违反 AGENTS.md 的「每种能力只保留一个 canonical 参考；新增前先找既有实现扩展，不造第二个」和「弃用即删除」。
  - 故障场景：之后有人修好 po 头部、装上 hook，就会出现两套规则不一致的检查。一套只在本地跑（并且要求非空译文），另一套在 CI 跑（不要求）。
  - 建议：二选一作为 canonical。我倾向保留 pytest 版，因为 CI 会跑它，而 CI 不跑 pre-commit。把旧脚本的空 msgstr 检查合并进来（见 C3），然后删掉 `validate_po.py` 的覆盖检查和对应 hook，或者让 hook 改为运行这个 pytest。同时修好两份 po 的第 5 行头部。

#### 2d: Data Compatibility

No findings。只改了 `message` 字段的值；`code`、`message_key`、HTTP 状态和信封结构都没变。`docs/project/api/conventions.md:37-43` 本来就规定"判别错误用 `error.message_key` 或 `code`"，与本次改动一致。前端只展示 `message`（`frontend/src/features/auth/helpers/authError.ts:12`），没有任何逻辑依赖它。

#### 2e: Robustness

No findings。

#### 2f: Maintainability

No findings（重复实现记在 C2）。

#### 2g: Performance and Efficiency

- [INFO] **C9** `backend/tests/test_i18n_message_keys.py:29-31`：`rglob("*.py")` 会把整个 `.venv` 遍历完才过滤掉，而且每个用例各扫一遍，共 3 次。实测两个测试文件合计约 1.4 秒，可以接受。想省的话可以加 `functools.cache`，并用 `os.walk` 剪掉目录。

#### 2h: Security

- [WARNING] **C1** `backend/application/services/chat_service.py:370-374`（非流式）和 `:326-331`（流式）：**上游大模型的报错原文仍会返回给调用方**。
  - 链路：`_fail_run_safely(run_id, str(exc))` → `Run.mark_failed` 写入 `error_message`（`domain/conversation/entity.py:143-145`）→ `RunDTO.error_message`（`application/dto.py:321`）→ `GET /api/v1/conversations/{id}/runs` 原样返回给会话 owner（`api/routes/conversations.py:138-154`）。
  - 复现：用测试里的 `_FailingGenerateLLM` 调 `send_message_sync`。响应 message 是 `LLM provider error`，但 `RunDTO.model_validate(run).error_message` 是 `upstream 401 from https://llm-gateway.internal/v1`。
  - `openai_provider.py` 没有包装 SDK 异常。所以在真实环境里，这里存的是 SDK 的完整报错串。（推断，未在本地复现：这类报错串常带网关地址、模型名，401 时还可能带脱敏后的 key 片段。）
  - 为什么不判 CRITICAL：修复前就是这样，本分支没有让暴露面变大。但 `d2fe08e` 的目的、design §3 第 4 点和 checklist #7 的 PASS，都建立在"run 记录是内部数据"这个错误前提上。
  - 建议：照仓库已有的做法改（`application/services/document_service.py:176-178` 的注释写明「error_message 会经 DocumentDTO 暴露给 API，不落 str(exc)」）。run 里只存归一化的文本（比如 `llm provider error: <异常类名>`），原文只写日志，流式和非流式两条路径一起改，并给 `test_sync_llm_failure_does_not_return_upstream_error_text` 加一条断言：`run.error_message` 不含上游原文。如果决定这次不修，就把 checklist #7 改成"部分通过"，在 design §4 加一条后续任务，并在 PR 里写明。
  - `Gate: auto-confirmed — pending user review`（严重度由我判定）。

#### 2i: Readability

No findings。新加的两处注释准确解释了"为什么"。

#### 2j: Testability and Test Coverage

- [WARNING] **C3** `backend/tests/test_i18n_message_keys.py:24,44-47`：测试名叫"每个 key 都有翻译"，实际只检查 `msgid` 这一行存在。以下三种情况都能通过测试，但运行时仍然坏：
  1. `msgstr ""`：`pybabel compile` 不收录空译文，运行时 `t()` 返回 key。成功响应里的 `t("…")`（比如 `api/routes/storage.py:162`）没有兜底，会把 key 原样当作 message 返回，这正是本 bug 的形态。
  2. `#, fuzzy` 条目：compile 默认丢弃。
  3. 中英 msgstr 的占位符不一致（比如 zh 写成 `{nmae}`）：`t()` 格式化失败后返回原始模板，用户会看到带 `{nmae}` 的文案。
  - CI 不编译 .mo，所以这 11 条新译文在 CI 里一次都没被执行过。我是手工 `pybabel compile` 再用 `gettext` 读出来验证的。
  - 建议：用 Babel（已经是运行时依赖）的 `babel.messages.pofile.read_po` 解析 po，要求 msgstr 非空且不是 fuzzy；再断言每个 key 在各语言里的 `{占位符}` 集合和 en 一致。
- [WARNING] **C4** `backend/tests/test_i18n_message_keys.py:23,32-34`：正则是逐行匹配的，跨行写法会全部漏扫。我逐一实测确认漏掉的写法：
  - `t(\n    "key", ...)`：行宽超过 100 字符时 black 就会这样折行，而 CI 强制 black，所以这是现实会发生的路径；
  - `message_key=(\n    "key"\n)`；
  - `message_key=message_key or "validation.domain"`（`domain/common/exceptions.py:140`）：这个默认 key 从来没被扫到过，今天只是恰好在翻译表里；
  - 通过变量传入的 key；
  - `t( "key")`。
  - 漏扫意味着测试安静地通过，这正是本 bug 当初能活下来的方式。反方向也有一个小问题：注释里写 `message_key="x"` 会被误报，不过误报会直接失败，影响很小。
  - 建议：改用 `ast` 扫描。取函数名为 `t` 的调用的第一个字符串常量参数，以及 `keyword.arg == "message_key"` 的值里所有字符串常量（包括 `BoolOp`）。再加一个小的自测样例，覆盖折行写法。

#### 2k: Extensibility

No findings。

### Code Review Summary

| Dimension | CRITICAL | WARNING | INFO |
|-----------|----------|---------|------|
| Standards compliance | 0 | 0 | 2 |
| Functional correctness | 0 | 0 | 1 |
| Implementation simplicity | 0 | 1 | 0 |
| Data compatibility | 0 | 0 | 0 |
| Robustness | 0 | 0 | 0 |
| Maintainability | 0 | 0 | 0 |
| Performance | 0 | 0 | 1 |
| Security | 0 | 1 | 0 |
| Readability | 0 | 0 | 0 |
| Testability | 0 | 2 | 0 |
| Extensibility | 0 | 0 | 0 |
| **TOTAL** | **0** | **4** | **4** |

---

## Git Diff Coverage

### Step 3: Git Diff Coverage Check

`git diff 244609f..HEAD --name-only`（diff 基点见 Review Context 的 Gate 说明）：

| File | In Review Scope | Classification |
|------|-----------------|----------------|
| `backend/core/exceptions.py` | YES | Reviewed |
| `backend/locales/en/LC_MESSAGES/messages.po` | YES | Reviewed |
| `backend/locales/zh_Hans/LC_MESSAGES/messages.po` | YES | Reviewed |
| `backend/tests/test_i18n_message_keys.py` | YES | Reviewed |
| `backend/application/services/chat_service.py` | YES | Reviewed |
| `backend/tests/test_chat_service_stream.py` | YES | Reviewed |
| `docs/work/delivery/2026-11/09-bugfix-i18n-raw-message-key/design.md` | — | 已在 Step 1 审 |
| `docs/work/delivery/2026-11/09-bugfix-i18n-raw-message-key/checklist.md` | NO | Substantive（含验收结论），review 结果见下 |
| `AutoTest/Release-Check/2026-11/bugfix/edy-i18n-raw-message-key.md` | NO | Substantive（合并门禁要求的验证指导），按 `AutoTest/Release-Check/STANDARD.md` 的 (AI review) 规则审，结果见下 |

### Additional Findings from Unscoped Files

**Release-Check 指导**

- [WARNING] **G1** `AutoTest/Release-Check/2026-11/bugfix/edy-i18n-raw-message-key.md:20,23,25,26,27,36`：违反规则 1.5（P0 照写就能跑）和 1.13（事实可追溯）。
  - 指南说"都不传时默认英文"，但它引用的 `locale.py:8` 写的是 `?lang > X-Lang > Accept-Language > 默认 en`，实现在 `:89-92`。
  - P0 第 1、3、4 项和 P1 第 5 项的英文期望值，都依赖"客户端不发 `Accept-Language`"。
  - 实测真实 app：只带 `Accept-Language: zh-CN,zh;q=0.9` 请求 `/api/v1/auth/me`，返回 `message='需要登录'`、`locale=zh_Hans`。
  - 故障场景：验证者用浏览器工具、中文系统上的 HTTP 客户端，或设了 zh locale 的 Playwright context 时，P0 会误判失败，并按 `_shared/safety.md` 记为"指南缺陷"。
  - 建议：英文期望项显式加上 `?lang=en`（或 `X-Lang: en`），并把第 20、36 行改成真实的优先级。
- [INFO] **G2** 同文件 `:27`：P1 第 5 项依赖 `agent-configs/999999999` 不存在。但 `/agent-configs` 没有归属隔离（AGENTS.md 已知缺口），如果某个环境里恰好有这个 id，会返回 200，该项误判。概率很低。可以改成"用测试账号建一个 `e2e-` 配置、删掉、再 GET 它"。
- 其余 (AI review) 规则通过：
  - 1.3：每项都有可由程序判断的信号（状态码、`code`、`message_key`、`message` 精确值），没有依赖模型生成文本；
  - 1.13：20 处 file:line 我逐行核对过，全部指向所述代码；
  - 1.14：`2026-11/` 下只有这一份指南，仓库里也没有 `regression: true` 的指南，不涉及同步其他指南；
  - lint：0 错误 0 警告。

**checklist.md**（不单独计数，归入对应 finding）

- #7「兜底不会把上游报错原文返回给调用方：PASS」不成立，见 C1。
- #3「以后再漏补翻译，覆盖测试会失败」言过其实，见 C3、C4。
- 开头根因段「没有任何检查」见 D-W1。
- 其余数字我都复核过，全部一致：43 个 key、11 个缺失、旧代码上的失败用例、全量 166 passed / 2 skipped、`lint-imports` 5 kept、Release-Check lint 0/0。
- 证据块里的 curl 结果来自真实前后端，我没有重启服务去复跑。但用进程内真实 app 复现了 `/auth/me` 的 en/zh 结果，与证据块一致。

---

## Overall Summary

| Dimension | CRITICAL | WARNING | INFO |
|-----------|----------|---------|------|
| Design document | 0 | 2 | 4 |
| Code quality（Step 2 + Step 3） | 0 | 5 | 5 |
| **TOTAL** | **0** | **7** | **9** |

### Verdict

**PASS**：所有维度都没有 CRITICAL。

PASS 不等于没事。以下 WARNING 应在合并前修复，或由你明确接受（`Gate: auto-confirmed — pending user review`）：

1. **C1**：上游原文经 `GET /conversations/{id}/runs` 返回给调用方；checklist #7 的结论需要更正。
2. **C2 / D-W1**：合并成一个 canonical 的 i18n 覆盖检查，修好 po 第 5 行头部，并更正设计里"没有任何检查"的根因。
3. **C3**：覆盖测试要检查空译文、fuzzy 条目和占位符一致性。
4. **C4**：扫描改用 `ast`，覆盖折行写法和 `or "默认 key"`。
5. **G1**：指南的英文期望项显式指定 `?lang=en`，并修正语言优先级的描述。
6. **D-W2**：§4 类比排查补上 run 记录、gRPC 拦截器和 `Accept-Language` 三处。
