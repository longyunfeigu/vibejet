# Plan: vibejet 定位为 AI Coding Template Kit —— 清理 + 重构 + Auth

日期：2026-06-10
分支：`refactor/code-cleanup`（worktree）

## §0 Triage

8 问：
1. 只服务一个明确用户目标？**是**（把 backend 整备成干净的 template kit）
2. 只影响一个业务模块？**否**（跨 domain/application/infrastructure/api/core/shared + pyproject）
3. 不改 DB schema/migration？**否**（新增 users 表 + baseline migration）
4. 不改公共 API 契约？**否**（新增 /auth/*，存量路由挂 auth 依赖）
5. 不涉及 domain 规则变化？**否**（新增 user 聚合）
6. 不涉及外部系统？**是**（不新增外部系统，反而把 kafka/celery/grpc 改为可选）
7. 不涉及权限/安全？**否**（auth 模块）
8. 只改少量文件？**否**

→ 4+ 个"否" → **Flow C**

约束清单：
- 硬约束（用户明确指定）：
  - 定位为 **template**（不是 pip library）
  - 重依赖拆 extras/可裁剪；pyproject description 改掉
  - 遗骸代码清掉（gRPC ProfileService/forge proto、过期 description）
  - entity 统一用 BaseEntity；UoW 删字典双轨
  - 补 auth 模块（SECRET_KEY 终于被消费）
  - Alembic 打 baseline migration
  - **不补测试**（核心服务测试明确跳过；已有测试不能弄坏）
  - 🟡 问题 6/7/9/10/11 能修则修：chat 流取消收尾、chat 去重、Swagger hack 移出 main.py、lifespan fail-fast 可配、迁移单轨
- 隐含约束（来自现有代码）：
  - DDD 依赖方向不可破坏；UoW port 保持 repository-agnostic
  - 统一响应/异常→业务码链路、i18n message_key 模式沿用
  - `domain/common/exceptions.py` 已有完整 user/auth 异常族，auth 直接复用
  - `BusinessCode.USER_NOT_FOUND/USER_ALREADY_EXISTS/PASSWORD_ERROR` 保留给 auth 用
- 需确认（已用合理默认，事后可调）：
  - auth 形态：JWT access+refresh、用 `pyjwt` + `pwdlib`（拒绝 FastAPI-Users：自带 ORM/manager 体系，会破坏 kit 的 DDD 分层示范价值）
  - 存量业务路由（chat/conversations/files/storage）router 级挂 `get_current_user`，ownership 细粒度校验留给下游

## 第 1 层

**目标**：把 backend 从"挖掉业务的产品遗骸"整备成干净自洽的 AI coding template kit。

**范围内**：
1. pyproject：description/作者占位修正；kafka/celery/grpc/boto3/oss2 拆为 optional extras；核心依赖放松为 `>=lower,<next-major`
2. 遗骸：删 gRPC ProfileService + forge proto（保留 gRPC server 骨架 + health + 拦截器）
3. UoW：删 `register_repository/get_repository` 字典双轨；仓储改"工厂表 + `__getattr__` 懒实例化"，新聚合只加一行
4. entity：`BaseEntity` 拆 `BaseEntity` + `SoftDeletableEntity`；Conversation/Message/Run/AgentConfig/FileAsset 全部继承，删手写 `_ensure_utc/_touch`
5. chat_service：phase1/phase3 抽公共方法；流式断连用 `CancelledError/GeneratorExit` 收尾 Run
6. main.py：Swagger i18n hack 移到 `api/docs.py`；lifespan 按依赖可配 fail-fast（`required` 标志）；启动迁移单轨化（砍 create_tables 分支）
7. auth 模块：domain/user + application(auth_service+security ports) + infrastructure(model/repo/jwt/password) + api/routes/auth + `get_current_user`，挂到业务路由
8. Alembic baseline migration（含 users 表）

**范围外**：核心服务测试补齐、前端、ownership 细粒度鉴权、grpc proto 重命名再生成、library 化（包名改造）。

**风险**：
- 放松版本 pin → 解析到新版本有行为差异。缓解：下界=当前 pin，上界=下个 major；跑现有测试。
- 业务路由挂 auth = 外部行为变化（deliberate，TODO 本来就要求）。
- 流式收尾在取消路径上做 IO，用 `asyncio.shield` 兜底，失败只 log。

**验收标准**：
- `uv run pytest tests/ -v` 现有测试全绿
- `uv run python -c "import main"` 可导入；不装 extras 时 kafka/celery/grpc/boto3/oss2 的 import 不在主启动路径上
- 登录拿 token → 带 token 访问 /conversations 通；不带 token 401
- `alembic upgrade head --sql` 能离线生成全量建表 SQL
- grep 无 forge/ProfileService 残留；UoW 无字典 API；entity 无重复 `_ensure_utc`

## 第 2 层

**方案概述**：
- **UoW**：`SQLAlchemyUnitOfWork._REPOSITORY_FACTORIES: dict[str, type]`（模块级数据表），`__getattr__` 懒创建并缓存到实例。port 删掉 register/get_repository。拒绝 entry-point 式注册（import 顺序魔法，对 template 过度设计）。
- **entity**：`BaseEntity(Generic[IdT])`: id/created_at/updated_at + `_touch`；`SoftDeletableEntity(BaseEntity)`: + deleted_at/mark_deleted/restore/is_deleted。`ensure_utc` 公开为模块函数供子类 `__post_init__` 复用。
- **auth**：
  - domain/user：`User` 实体（username/email/hashed_password/is_active/is_superuser），行为 activate/deactivate（superuser 不可停用，复用现有异常）
  - application/ports/security.py：`PasswordHasher`、`TokenProvider` Protocol
  - application/services/auth_service.py：register/login/refresh/get_current_user/change_password；`AuthUnitOfWork` Protocol 只声明 user_repository
  - infrastructure/security/：`PwdlibPasswordHasher`（argon2）、`JwtTokenProvider`（pyjwt，HS256，SECRET_KEY 签名，access 30min/refresh 7d，type claim 区分）
  - api/routes/auth.py：POST /auth/register、POST /auth/login、POST /auth/refresh、GET /auth/me
  - api/dependencies.py：`get_current_user`（HTTPBearer）；chat/conversations/files/storage router 加 `dependencies=[Depends(get_current_user)]`
- **lifespan**：Redis/Storage/LLM settings 各加 `required: bool = False`；init 失败时 required→raise，否则保持降级 log
- **迁移单轨**：lifespan 只认 `AUTO_RUN_MIGRATIONS`；`create_tables/drop_tables` 保留为测试工具并注明

**核心流程（auth）**：
login → AuthService.authenticate（查 user → verify password → 校验 is_active）→ TokenProvider.issue(access+refresh) → 路由返回 token 对；受保护请求 → HTTPBearer 提取 → TokenProvider.verify → uow 查 user → request 注入 CurrentUser。

## 第 3 层（关键实现细节）

- **DB**：users 表：id PK、username unique、email unique、hashed_password、full_name nullable、is_active、is_superuser、created/updated/deleted_at + 索引。baseline migration 手写（autogenerate 需活 DB），表序：conversations → runs → messages（FK 依赖）→ agent_configs → file_assets → users。
- **JWT**：HS256 + SECRET_KEY；claims: sub(user_id)/type(access|refresh)/exp/iat；refresh 只能换 token，不能直接访问业务接口。
- **流式收尾**：`except (asyncio.CancelledError, GeneratorExit)` → `asyncio.shield(_fail_run(run_id, "stream cancelled"))` best-effort + re-raise。
- **extras 与裁剪**：messaging/celery/grpc/boto3/oss2 的 import 必须保持惰性（验证主 app 启动路径不触碰）；extras：`kafka`、`aiokafka`、`celery`、`grpc`、`s3`、`oss`、`observability`（已有）、`dev`（已有）。

## §11 执行步骤（每步一 commit）

1. 本 plan 文件
2. 遗骸清理 + pyproject（description、extras 拆分、放松 pin、新增 pyjwt/pwdlib）
3. UoW 去字典双轨 + 懒加载仓储
4. entity 统一 BaseEntity/SoftDeletableEntity
5. chat_service 去重 + 流取消收尾
6. main.py 瘦身（api/docs.py）+ lifespan fail-fast + 迁移单轨
7. auth 模块全链路
8. Alembic baseline migration
9. review skill 全量审查 + 修 blocking
