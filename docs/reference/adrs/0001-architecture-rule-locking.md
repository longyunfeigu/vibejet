# 设计：架构边界 + 编码红线上锁（第一批）

> 目标：把 `AGENTS.md` 中最核心的散文规则翻译成"会失败的机器检查"，
> 落实 `docs/reference/guides/base-library-principles.md` 第 1 节的杠杆排序
> （机器检查 > 一键验证 > 散文规则）。本批只覆盖**规则确定性高、零假阳性、
> 有现成工具**的不变量。

## 背景与动机

- 本仓库定位为基础库/模板，核心命题是"让 AI 在其上开发不跑偏"。
- `base-library-principles.md` 已论证：治漂移的最强杠杆是会失败的机器检查，
  但排第一的这条杠杆尚未落地——`.pre-commit-config.yaml` 与 CI 只有通用
  lint（black/isort/flake8/mypy/bandit），没有任何检查强制 DDD 依赖方向。
- 当前代码库是干净的（`domain/` 零反向 import、零框架 import；
  `application/` 零 `infrastructure` import），上锁成本处于最低点。

## 范围

### 1. import-linter 声明式契约

配置进 `backend/pyproject.toml`（`[tool.importlinter]`），新增 dev 依赖
`import-linter`。

| 契约 | 规则 | 例外 |
|------|------|------|
| domain 纯净性 | `domain` 禁止 import `application` / `infrastructure` / `api` | 无 |
| domain 禁框架 | `domain` 禁止 import `fastapi` / `sqlalchemy` / `redis` / `httpx` | 无 |
| application 边界 | `application` 禁止 import `api` / `infrastructure` | 无 |
| api 边界 | `api` 禁止 import `infrastructure` / `sqlalchemy` | `api/dependencies.py`（AGENTS.md 认可的组合根）；`api/routes/metrics.py`（基础设施健康探针，见"被拒绝的方案"） |

约束方向依据 AGENTS.md：`API → Application → Domain ← Infrastructure`。
`infrastructure` 允许 import `domain` 与 `application`（实现仓储接口与端口），
不需要契约限制。

### 2. flake8-print（禁 print）

- `backend/pyproject.toml` dev 依赖加 `flake8-print`；
- `.pre-commit-config.yaml` 的 flake8 hook `additional_dependencies` 加同名条目；
- CI 的 flake8 步骤依赖随 `uv sync --extra dev` 自动获得；
- 排除目录沿用现有配置（`alembic/versions`、`grpc_app/generated`），
  并对 T20 追加排除 `backend/scripts/`（CLI 工具，`validate_po.py` 等的
  `print` 是合法输出）。

### 3. pytest 架构兜底测试

新增 `backend/tests/test_architecture.py`（约 20 行），仅一条检查：

- **UoW port 保持 repository-agnostic**：断言
  `backend/application/ports/unit_of_work.py` 中抽象 UoW 类的公开属性
  在白名单内（当前形状固化为白名单）。新模块试图往全局 UoW 挂 repository
  时测试变红，强制走 service-local `Protocol` 路线（AGENTS.md UoW Shape 节）。

### 4. 接线

- `.pre-commit-config.yaml` 新增 `lint-imports` hook（local hook，
  在 `backend/` 内执行）；
- `.github/workflows/ci.yml` 新增一步全量 `uv run lint-imports`
  （import 图检查必须全量跑，不适用 changed-files 策略；执行很快）；
- pytest 兜底测试随现有 `Test` 步骤自动生效，CI 结构不变。

### 5. 文档同步

- `AGENTS.md`：Dependency Direction 节与 Red Lines 相关条目各加一行
  "由 import-linter / `tests/test_architecture.py` 强制"；
- `docs/reference/guides/base-library-principles.md` 第 2 节
  "把散文规则翻译成会失败的代码"处标注已落地的部分。

## 被拒绝的方案

1. **全部自写 pytest 架构测试（AST 扫描）**：import-linter 已覆盖 80%，
   自写数百行 AST 检查违反本仓库"重新发明已被解决的问题"红线。
2. **只上 lint 层、不写 pytest 兜底**：UoW 膨胀这类非 import 类不变量抓不到，
   而它恰是 AI 最省事的违规路径。
3. **domain 异常必须为 BusinessException 的 AST 检查**：规则本身经不起
   第一性原理检验——domain 内 `raise ValueError(...)` 式的**编程错误断言**
   是正当 Python，与"业务规则违反用 BusinessException"不冲突，AST 无法
   区分两者。一刀切会制造假阳性，诱导 AI 把编程错误伪装成业务异常。
   真正需要防的"domain 抛 HTTPException"已被 import 禁令覆盖。
4. **将 `metrics.py` 重构为 port 以消灭豁免**：健康探针的本职是戳基础设施，
   无业务逻辑可隔离、无第二实现可替换，凿 port 属于仪式化分层。
   显式白名单 + 注释原因本身具有教育价值（教 AI 规则的边界）。

## 成功判据

- `uv run lint-imports` 在当前代码库绿灯；人为在 `domain/` 加一条
  `from infrastructure...` 后红灯。
- `uv run flake8` 对新增 `print(...)` 报 T201。
- 往抽象 UoW 加一个 repository 属性后 `pytest tests/test_architecture.py` 红灯。
- pre-commit 与 CI 全链路通过。

## 影响面

`backend/pyproject.toml`、`.pre-commit-config.yaml`、`.github/workflows/ci.yml`、
新增 `backend/tests/test_architecture.py`、`AGENTS.md`、
`docs/reference/guides/base-library-principles.md` 少量行。
Execution policy: fast（无 strict 触发条件：不改 schema/API 契约/auth，
纯增量 dev 工具链）。
