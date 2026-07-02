# 后端代码审计报告与修复计划

- 日期：2026-07-02
- 范围：`backend/`（约 1.94 万行 Python），五维度并行审计：架构分层 / 安全权限 / 健壮性 / 代码质量 / 测试工程化
- 审计分支：`master`
- 方式：全量 grep + 关键文件逐一阅读 + 关键证据交叉核实（本文件所有 file:line 均已实测）
- 性质：本文件是证据摘要与修复计划，不是当前基线。落地修复后，永久事实更新到 `AGENTS.md` / `docs/project/`，本文件归档到 `docs/archive/`。

---

## 一句话结论

这是一个分层纪律执行得相当到位的 DDD + 六边形「脚手架 kit」——依赖方向、端口/适配器、UoW 抽象、bounded context 边界几乎零违规，领域实体充血，仓储/响应/事务骨架干净。它离「完美的模板」很近，但离「可上线的产品」还差两道硬门槛：**授权层整体缺失**，以及一个**会让令牌被伪造的配置默认值**。

问题总数：2 critical + 5 major + 一批 minor/质量债。无架构级返工，问题都是可定点修复的。

---

## 分级问题清单

### 🔴 P0 — 上线前置（critical）

#### P0-1 compose 默认 SECRET_KEY 可伪造任意用户令牌
- 证据：`docker-compose.yml:25,42` = `SECRET_KEY: ${SECRET_KEY:-your-secret-key-here}`；`backend/core/config.py:340` 的 `_validate_secret_key` 只校验「非空」，公开的模板默认值满足非空 → 应用照常启动，fail-fast 形同虚设。
- 影响：JWT 用 HS256 + 该 secret 签名（`backend/infrastructure/security/jwt_tokens.py:50`）。攻击者知道模板默认值即可离线伪造任意 `sub` 的 access token，冒充任意用户；配合 P0-2 的 IDOR = 完全接管。
- 修复：
  1. `docker-compose.yml` 两处改为 `SECRET_KEY: ${SECRET_KEY:?SECRET_KEY must be set}`（缺失则 compose 直接报错，不给弱默认）。
  2. `config.py` 的 `_validate_secret_key` 增加：拒绝已知弱值（`your-secret-key-here` 等）+ 最小长度/熵校验。
- 成本：低，零业务风险，立即可做。

#### P0-2 全线 IDOR 越权（AGENTS.md 已登记 gap 的具体化）
- 证据：`files` / `documents` / `conversations` / `chat` 的所有读/改/删路径只有登录闸门（router 级 `Depends(get_current_user)`），无归属校验。
  - `api/routes/files.py:50`（`owner_id=None`）、`:98,:127,:148,:168`（`# No permission check`）
  - `api/routes/storage.py:132`（`# No permission check`，可确认他人 pending 上传）
  - `api/routes/documents.py:71`（`owner_id=None`）及 `:85,:98,:111,:121` 读改删无 owner 过滤
  - `api/routes/conversations.py:59-208` 全 CRUD + messages/runs/agent-configs 无 owner 过滤
  - `api/routes/chat.py:26` 可向任意会话发消息、消耗付费 LLM
- 放大因素：主键为自增整数（非 UUID），可直接枚举遍历。
- 关键反差：`domain/file_asset/entity.py` 已定义 `belongs_to(user_id) -> bool` 鉴权原语，但**全仓库从未被调用**（grep 确认仅定义处）——地基建好了，墙没砌。写路径（presign/upload/documents.create）会记录 `owner_id`，但读改删完全不消费它，归属信息「只写不校验」。
- 影响：任一登录用户可读/删他人文件、看他人聊天记录与文档正文、为他人对象签发下载 URL、向他人会话发消息烧 LLM 成本、对他人文档触发 reparse 烧解析成本。
- 修复：在 application/domain 层统一落地授权——`get_current_user` 注入 owner，service 查询强制 `owner_id` 谓词，或加载后比对 `asset.belongs_to(current_user.id)` 否则抛 403；列表接口传入真实 owner_id 而非 None。**不能只在路由打补丁**，必须落到 application/domain 统一鉴权。
- 成本：高（工作量最大），产品化硬门槛。建议单独开 Story + plan mode。

### 🔴 P0.5 — 仓库卫生（零风险，随手做）

#### P0.5-1 dev.db 备份未被 gitignore，含口令哈希/PII
- 证据：`backend/dev.db.bak-20260624`（约 111KB SQLite，`git status` 显示 `??` 未跟踪）。`git check-ignore` 确认**未命中**——`.gitignore` 的 `*.db` 不匹配 `.db.bak-<date>` 后缀（`dev.db`/`app.db` 反而被忽略）。含 users 表 argon2 哈希与用户数据，一次 `git add .` 即入库、历史难清除。
- 修复：删除该文件；`.gitignore` 增加 `*.db.bak*` / `*.bak`。

---

### 🟡 P1 — 应该修（major）

#### P1-1 SSE 预校验异常在 200 OK 之后抛出
- 证据：`api/routes/chat.py:32` 返回 `StreamingResponse(service.send_message_stream(...))` 时 200 与响应头已发出；而 `application/services/chat_service.py:82-86,182` 的 `ConversationNotFoundException` / `ConversationArchivedException` 是在生成器内部才抛。
- 影响：客户端已收 200 却拿到中断流——无 4xx、无 SSE `error` 事件，前端无法区分「会话不存在」与「网络断开」。
- 修复：把会话存在性/归档校验前移到 `StreamingResponse` 构造之前（普通 async handler 能正常映射 4xx）；或在生成器内 catch 这两个域异常，转成 `event: error` + `event: done` 帧再关闭。

#### P1-2 存储上传成功、DB 写入失败 → 孤儿对象，无补偿
- 证据：`application/services/file_asset_service.py:444-463`（`relay_upload`）、`507-525`（`relay_upload_stream`）。先 `await self._storage.upload(...)` 落对象存储，再 `upsert_active_asset(...)` 写 DB。DB 失败时 UoW 只回滚 DB，已上传对象成孤儿。
- 影响：长期累积不可见垃圾对象、占用配额。
- 修复：DB 失败路径做 best-effort `storage.delete(key)`（失败仅告警，不掩盖原异常）；或加对账/GC 任务扫「存储有、DB active 记录无」的 key。至少要有一条兜底。

#### P1-3 测试非 hermetic + 生产启动崩溃隐患（配置漂移）
- 证据：`core/config.py:371` 在导入期即 `settings = Settings()`；`:332` 用 `SettingsConfigDict(env_file=".env", extra="forbid")`。本地 `backend/.env` 含 `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`，而 master 的 `Settings` 无这两个字段 → 从 `backend/` 跑 pytest 时 4 个文件采集失败（`ValidationError ... extra_forbidden`）；切纯净 cwd 才 43 passed / 1 skipped。
- 双重影响：(a) 任何开发者在 `backend/` 目录跑测试都是红的；(b) 更严重——生产若真设了 `GOOGLE_CLIENT_ID`，`extra="forbid"` 会让应用**启动直接崩溃**。
- 背景：Google 登录代码在 `feat/google` 分支，不在 master；`.env` 是为那个分支准备的残留。
- 修复：
  1. 短期：master 上把 `.env` 里 google 两行注释/删除，或测试用 `Settings(_env_file=None)` / conftest monkeypatch 关 env_file。
  2. 结构性：导入期不要实例化全局 `settings`（改惰性/依赖注入）；确认 google oauth 字段是否该并入 master 的 Settings。

#### P1-4 DEBUG 默认 True + debug 下响应体泄露 traceback
- 证据：`core/config.py:208` `DEBUG: bool = Field(default=True, ...)`；`core/exceptions.py:176` 在 `app.debug` 时把 `exception`/`traceback` 写入响应体；`main.py:143` `debug=settings.DEBUG`。env.example/compose 显式设 false 可缓解，但缺省不安全（无 `.env` DEBUG 项时为 True）。
- 修复：默认改 `False`；可加「ENVIRONMENT=production 时强制 DEBUG=False」交叉校验。

#### P1-5 AgentConfig 并发同名创建/改名 → 裸 500
- 证据：`infrastructure/repositories/agent_config_repository.py:50-53,71` 只 `flush()` 无 IntegrityError 捕获；唯一索引 `ix_agent_configs_name`（`infrastructure/models/conversation.py:217`）；`application/services/conversation_service.py:158,201` 是 check-then-act 预检，并发下挡不住。唯一索引冲突冒泡成裸 500（走 `core/exceptions.py:167` 全局 handler）。
- 修复：照抄 `infrastructure/repositories/user_repository.py:62-68` 的 `except IntegrityError` → 域异常 → 409 模式。**改动最小、收益最清晰，建议顺手做。**

---

### 🟢 P2 — 质量债（面广但不阻塞，可排期）

- **魔法状态字符串跨三层硬编码，缺 StrEnum**：domain 有私有校验 set（`_DOCUMENT_STATUSES` 等）但值是裸字符串，application（`file_asset_service.py:136,574`、`chat_service.py:94,115,141`）与 infrastructure（`document_repository.py:121,125,141` domain 词汇泄漏进 infra 裸比较）各自重抄同一套词汇。→ 各模块定义 `StrEnum`（`DocumentStatus`/`RunStatus`/`MessageRole`/`ConversationStatus`/`FileAssetStatus`），校验 set 改 `set(DocumentStatus)`，三层统一引用。StrEnum 与 SQLAlchemy/Pydantic 兼容，不改存储格式。**面最广的一条债。**
- **config 假能力 + 幽灵配置**：`core/config.py:297-316` 的 `SMTP_*`/`EMAIL_FROM`/`STRIPE_API_KEY`/`SENTRY_DSN`/`REALTIME_WS_*`/`MAX_UPLOAD_SIZE`/`UPLOAD_DIR` 零消费路径；`pyproject.toml:53-61` 的 mypy override 还挂着 `stripe.*`/`wechatpayv3.*` 两个不存在的模块。与 `extra="forbid"` 初衷自相矛盾。→ 删除或移到路线图文档；真要 Sentry 就补 `sentry_sdk.init`。（注：`RATE_LIMIT_PER_MINUTE` 是真能力，已接入 auth，不算死配置。）
- **api_clients 整个模块死代码**：`infrastructure/external/api_clients/{base.py,example.py,__init__.py}` 外部零引用，`example.py` 是带 `print()`（:26,28,30,34）的中文 demo 住在生产包里。→ 删除，顺带清 3 处 print。
- **文件头注释覆盖率约 50%**（68/136）：缺头的恰是 `core/config.py`、`core/response.py`、`core/exceptions.py`、`infrastructure/repositories/base_repository.py`、`infrastructure/database.py`、`application/dto.py` 等核心文件，违反 `.claude/rules/doc-maintenance.md`。→ 批量补 input/output/pos 三行，优先 core/ 与 base_repository/dto。
- **测试覆盖偏科**：document 模块质量高（状态机 + 负路径 + 并发语义 + 强断言），但 `auth_service`/`chat_service`/`conversation_service`、`domain/user/service`、6 条路由、整个 gRPC 层**零测试**，全仓无一条越权/未授权测试——恰是 CLAUDE.md 标🔴的最高风险面。CI（`.github/workflows/ci.yml`、`.gitlab-ci.yml`）用 `uv sync --extra dev` 不装 documents/s3 extra，导致 parser/provider 代码在 CI 从不执行（`test_document_parsers.py` 全 SKIPPED），绿 ≠ 可用。→ 优先补 auth_service + auth 路由（401/403）集成测试；CI 增加 `--all-extras` job + `--cov` 阈值。
- **其余 minor**：
  - `api/routes/storage.py:105,123,130` 混用 `HTTPException` 与 `BusinessException`，错误信封不统一。
  - fetch-or-raise 模板重复约 13 次（`conversation_service` 就 7 次）→ 可加 `get_or_raise(repo, id, exc_factory)` helper。
  - `infrastructure/external/storage/providers/oss.py` 只设 `connect_timeout` 无 read timeout → 对齐 `s3.py` 的 connect+read timeout + retries。
  - `infrastructure/external/storage/providers/local.py:145,486` 裸 `except:` → 收窄 + 记日志。
  - `core/i18n.py:57-58` `except Exception: pass` 静默 → 加 debug/warning 日志。
  - `api/routes/documents.py:53,117` BackgroundTasks 无并发上限、`document_service.py:118` 整文件读内存、重启丢在途任务（依赖 `parsing_stale_seconds` 被动恢复）→ 迁 Celery 前至少设并发/大小上限（属已知过渡设计）。
  - `application/dto.py:284` `MessageDTO_Agent` 命名混 CapWords+snake → 改 `AgentMessageDTO`。
  - 工具链无 ruff（仍 black+isort+flake8），`.flake8` 与 `[tool.flake8]` 双份配置且后者大概率 inert。
  - refresh token 无轮换/撤销、无登出/黑名单（`auth_service.py:99`）；`/docs` `/redoc` `/` 未认证暴露 API 契约；CORS `allow_credentials=True` + methods/headers 全通配；postgres compose 默认弱口令；限流仅 register/login 且进程内实现，chat/reparse/upload 无限流。（安全 medium/low，按环境收敛。）

---

## 已确认为「做对了」的点（避免后续误伤）

- 依赖方向零违规；六边形方向正确（infrastructure 只 import `application.ports.*`，无反向依赖）。
- UoW 用 `_REPOSITORY_FACTORIES` 注册表 + `__getattr__` 懒实例化，各服务定义 service-local Protocol（ChatUoW/ConversationUoW/DocumentUoW/FileAssetUoW），无全局属性膨胀。
- bounded context 隔离干净；gRPC 无重复业务逻辑（当前是纯骨架）；domain 实体充血非贫血（User/Run/Document/FileAsset 均有真实状态机与不变量）。
- SQL 全参数化无注入面；路径穿越有 `providers/local.py:426 _safe_path` 防御；响应头有 `_sanitize_filename_for_header` CRLF 剥离；密码用 pwdlib argon2 且 fail-closed；登录防用户枚举；JWT 强制校验 type claim + 单一 algorithms 无算法混淆。
- 三段式 chat 事务从不跨 LLM 调用；文档解析幂等 claim 原子安全（条件 UPDATE + `claimed_at` token）；chat 断连用 `asyncio.shield` 兜底；purge 存储删除失败记结构化 warning（正确降级非静默吞）。
- 超时/重试普遍到位（OpenAI/Anthropic timeout+retries、S3 connect+read timeout）；无 N+1；分页有 `le=MAX_PAGE_SIZE` 上界。
- lifespan fail-fast（`_init_optional(required=...)`）；schema 单轨走 Alembic（`create_tables()` 未接入 lifespan）；Alembic 迁移链单头 0002、downgrade 完整、与 ORM tablename 无漂移。
- 泛型仓储基类 + SoftDeleteFilterMixin，仓储层无 CRUD 复制；响应格式统一走 success_response/paginated_response；DTO 用 `model_validate` 无手抄字段搬运。
- Dockerfile 质量好（多阶段、非 root、HEALTHCHECK、manifest 先拷贝分层缓存、`uv export --frozen`）；CI 双轨含 `uv lock --check` + pip-audit + changed-file 增量 lint；pre-commit 完整。

---

## 修复计划（分批）

### 批次 A — 立即（零风险，可单个小 PR 一起做）
1. P0-1：`docker-compose.yml` SECRET_KEY 去弱默认 + `config.py` 加弱值/长度校验。
2. P0.5-1：删 `backend/dev.db.bak-20260624`，`.gitignore` 加 `*.db.bak*` / `*.bak`。
3. P1-3 短期项：master 上注释/删除 `.env` 的 google 两行（或测试关 env_file）。
4. P1-4：DEBUG 默认改 False。
5. P1-5：AgentConfig IntegrityError → 409（照抄 user_repository）。

> 批次 A 全部是小范围、可逆、不触碰业务逻辑的改动。

### 批次 B — 上线前硬门槛（单独 Story + plan mode）
1. P0-2：统一授权层，落到 domain 已有的 `belongs_to`——注入 current_user、service 强制 owner 谓词、列表按 owner 过滤、补 401/403 测试。这是最大工程，触及 auth/权限安全面，按 AGENTS.md 强制升级条件走 Flow B 起步。

### 批次 C — 健壮性收尾
1. P1-1：SSE 预校验前移。
2. P1-2：存储孤儿补偿（best-effort delete 或 GC 对账）。
3. `_limit_stream` 中断路径 abort multipart；OSS read timeout；local.py/i18n 异常收窄+日志。

### 批次 D — 质量债（一个 sprint 收拾模板残留）
1. StrEnum 收敛魔法状态字符串（面最广）。
2. 删假能力配置 + api_clients 死代码 + stripe/wechatpayv3 幽灵 override。
3. 补文件头注释（优先 core/ 与 base_repository/dto）。
4. 补 auth/chat/conversation 服务与越权测试；CI 加 `--all-extras` + `--cov` 阈值。
5. 工具链评估迁 ruff；清理 flake8 双份配置。

---

## 关键文件索引（全绝对路径）

- `backend/api/routes/files.py` / `documents.py` / `conversations.py` / `storage.py` / `chat.py`
- `backend/application/services/file_asset_service.py` / `chat_service.py` / `conversation_service.py`
- `backend/api/dependencies.py`
- `backend/infrastructure/security/jwt_tokens.py`
- `backend/infrastructure/repositories/agent_config_repository.py` / `user_repository.py`
- `backend/domain/file_asset/entity.py`（`belongs_to` 未被调用）
- `backend/core/config.py`（SECRET_KEY 校验、DEBUG 默认、假能力字段、导入期实例化）
- `backend/core/exceptions.py`（debug traceback 泄露、AgentConfig 500）
- `backend/infrastructure/external/api_clients/`（死代码）
- `docker-compose.yml`（SECRET_KEY 弱默认、postgres 弱口令）
- `backend/dev.db.bak-20260624`（应删除）
