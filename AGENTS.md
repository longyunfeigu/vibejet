# AGENTS.md

Repo-level working baseline for all coding agents — the single source of truth.
`CLAUDE.md` imports this file via `@AGENTS.md`; other agents (Codex, etc.) read it directly.

## Project Structure

Monorepo-style repository with Python backend code under `backend/` and a frontend runtime directory under `frontend/`.

```
vibejet/
├── backend/           # Python FastAPI + gRPC + DDD backend
│   ├── .venv/         # Python 虚拟环境 (uv 管理)
│   └── .env           # 后端环境变量 (SECRET_KEY, DATABASE__URL 等)
├── frontend/          # React + TypeScript 前端 (Vite)
│   ├── src/           # 前端源码
│   └── .env           # 前端环境变量 (VITE_API_URL 等)
├── docs/              # Project facts, product intent, references, archives, in-flight work
│   ├── product/       # Product intent (PRD 等)——与平台事实隔离，不进 project/
│   ├── project/       # Current architecture, API/data/UI contracts, design tokens
│   ├── reference/     # ADRs, guides, research notes
│   ├── solutions/     # Solved problems & decisions knowledge base (vj-compound 写入)
│   ├── archive/       # Historical / superseded docs, not current baseline
│   └── work/          # In-flight delivery: plans/（每块工作一份计划文档）
├── .agents/skills/    # Repo-local AI workflow skills
└── docker-compose.yml
```

**Entry Points**:
- REST API: `backend/main.py` (routes exposed under `/api/v1`)
- gRPC: `backend/grpc_main.py`
- Backend tests: `backend/tests/`
- Frontend dev: `frontend/src/main.tsx`
- Frontend routes: `frontend/src/routes/` (TanStack Router file-based)
- Frontend features: `frontend/src/features/`

## Current Baseline

`vibejet` is a full-stack application with a Python backend (`backend/`) and a React frontend
(`frontend/`). Current project facts live under `docs/project/`.

**仓库定位**：本仓库同时是一个**基础库/模板**——沉淀经过验证的架构、参考实现与工作流，
供 AI 在其上开发而不漂移。因此内容有策展纪律（完整论证见
`docs/reference/guides/base-library-principles.md`）：

- 每种能力只保留一个 canonical 参考；新增前先找既有实现扩展，不造第二个
- 弃用即删除或移入 `docs/archive/`，不留"改成不可用但保留"的墓碑
- 断言当前状态的文档必须与现实一致；删除/移动任何资产时，同步更新所有指向它的文档
- 不沉淀可从代码推导的事实；文档只承载意图、约束与被拒绝的方案
- 给规则加强制前先确认规则本身成立；写"必须"的规则要有会失败的检查兜底

Known current gaps:
- JWT auth (login gate) + resource ownership are implemented: files / storage / conversations /
  chat / documents endpoints are owner-scoped (non-owner access → 404). Role/tenant checks and
  `/agent-configs` ownership are still missing — multi-role products need an RBAC pass first
  (see `docs/project/api/conventions.md` 鉴权与归属).
- Schema changes go through Alembic (single init revision `0001` in
  `backend/alembic/versions/`; new changes autogenerate incremental revisions on top);
  do not rely on `create_tables()` in production.

## Backend Architecture

DDD + Hexagonal Architecture with strict layered boundaries. All paths relative to `backend/`.

### Dependency Direction (Critical)

```
API → Application → Domain ← Infrastructure
```

- **Domain NEVER imports** from infrastructure, application, or API
- Infrastructure implements domain repository interfaces and application ports
- Application orchestrates through interfaces (ports/adapters), including Unit of Work
- API layer only handles HTTP I/O and dependency injection

### Layer Responsibilities

| Layer | Purpose | Contains | Constraints |
|-------|---------|----------|-------------|
| `domain/` | Pure business logic | Entities, repository interfaces, domain services, events | No framework/DB/HTTP imports |
| `application/` | Use case orchestration | Services, DTOs, ports | No direct DB/ORM imports |
| `infrastructure/` | Technical implementation | ORM models, repository impls, external clients, adapters | Implements domain interfaces |
| `api/` | Presentation | Routes, middleware, dependencies | Only I/O binding, no business logic |
| `core/` | Shared infrastructure | Config, logging, exceptions, response models | - |
| `shared/` | Cross-cutting | Business codes, constants, prompts | - |

Composition-root exception: `backend/main.py` and `backend/api/dependencies.py` may wire concrete
infrastructure implementations into FastAPI. Route handlers must still stay thin and must not
directly operate repositories, ORM models, or SQLAlchemy sessions.

依赖方向由 import-linter **机器强制**（`backend/pyproject.toml` 的 `[tool.importlinter]`，
pre-commit `lint-imports` hook + CI 全量执行，`cd backend && uv run lint-imports` 可本地跑）。
例外只有两类，均在契约的 `ignore_imports` 中显式声明并注明原因：组合根
（`api/dependencies.py`）与基础设施探针（`api/routes/metrics.py`、
`core/observability/` 的 health/tracing）。完整清单以契约为准；新增例外必须改契约，
不允许口头豁免。

### Domain Service vs Application Service

**Domain Service** (`domain/*/service.py`): pure business rules across entities/aggregates —
business validation (e.g., username uniqueness), business invariants (e.g., "superuser cannot
be deactivated"). **No external system dependencies.**

**Application Service** (`application/services/*_service.py`): orchestrates domain + external
systems — HTTP calls, SDK, caching, distributed locks, DTO mapping, transaction boundaries (UoW).

### Unit of Work Shape

- UoW is an application-layer transaction boundary: `backend/application/ports/unit_of_work.py`
- Concrete SQLAlchemy implementation: `backend/infrastructure/unit_of_work.py`
- The central UoW port must stay repository-agnostic. Do not add every new module's repository as
  an attribute on the global abstract UoW（由 `backend/tests/test_architecture.py` 白名单兜底）.
- Application services should define small service-local `Protocol`s for the repositories they need
  (see `FileAssetUnitOfWork`, `ConversationUnitOfWork`, `ChatUnitOfWork`).
- Domain repository interfaces remain in `backend/domain/<module>/repository.py`; domain must not
  know about UoW or transactions.

## Coding Style & Conventions

- Python >= 3.11, PEP 8, 4-space indent; type hints required for public functions
- Names: files/modules/functions/vars `snake_case`; classes `CapWords`
- DTOs use Pydantic v2 models; validate at boundaries
- Logging: never `print`; use `core.logging_config.get_logger(__name__)` (structlog)
  （flake8-print T20 强制；`backend/scripts/` 与 `.agents/**/scripts/` 属 CLI 工具豁免）
- Exceptions: domain raises `BusinessException` (`backend/domain/common/exceptions.py`);
  API translates to HTTP responses via handlers in `backend/core/exceptions.py`

## Development Environment

| 项目 | 工具 | 启动命令 | 配置文件 |
|------|------|----------|----------|
| 后端 | uv + `backend/.venv/` | `cd backend && uv run python main.py` | `backend/.env` |
| 前端 | pnpm + Vite | `cd frontend && pnpm dev` | `frontend/.env` |
| 测试 | uv + pytest | `cd backend && uv run pytest tests/ -v` | - |

- DB 等基础设施可用 `docker-compose up -d` 启动
- 后端 `.env`: `SECRET_KEY`（必填，缺失则启动失败）、`DATABASE__URL`、`DEBUG`；env 用嵌套键（如 `DATABASE__URL`、`REDIS__URL`）
- 前端 `.env`: `VITE_API_URL`（Vite 代理 `/api` 请求到此地址，默认 `http://localhost:8010`，与后端默认端口一致）
- 两个 `.env` 均不提交 git；不提交任何 secrets；默认 CORS/dev 配置不得用于生产

## AI Workflow Entry Points

默认从 `vj` router 进入，按风险选择 Patch / Story / Plan；详细阶段、UI 双轨、验证与收口规则见
`docs/reference/guides/ai-workflow.md`。

- Patch：不建文档，窄改动 + focused verification。
- Story：回复里写几行意图和执行方式，直接实现，不建文档。
- Plan / strict：`vj-plan`（一份计划文档）`-> vj-work`。
- 工作流自身变更：跑 `.agents/evals/vj-workflow/` 和 `.agents/tests/`；计划交付必过 `plan_lint.py`，
  `vj-work` 开工必过 `plan_lint.py --for-execution` + `workflow_doctor.py plan`。

## Plan 规范

- 一块工作一份计划：`vj-plan` 生成 `docs/work/plans/{date}-{slug}.md`，写给人审：做什么、关键设计、
  要拍板的决定、验收清单、执行顺序（只有后三节格式固定，其余按这块工作的性质写）；不写改哪些文件——
  `vj-work` 开工时读真实代码、把验收变成测试、拆子任务，进度和验收说明写回同一文件。
  整份 PRD 输入时先出拆分总览（`{date}-epic-0-overview.md`），再按 Epic 拆成多份、一次全部写完，`after:` 只表示先后；
  每份计划写完调 `prd-to-bdd` 生成给人把关的用例表（`cases:` 指向它），`vj-work` 收尾时激活这些用例并用 AutoTest 真跑
- 执行策略用计划 frontmatter 的 `policy: fast | strict` 表达
- **strict 触发条件**（plan 阶段或开发中碰到任一条 → strict，开发中则暂停并升级）：
  改 DB migration/schema/数据回填/破坏性数据更新、改公共 API 契约/DTO envelope/错误码/
  向后兼容、改权限/认证/安全/ownership/tenant 边界、引入外部系统或异步任务、复杂状态机/
  幂等/并发/事务（UoW）一致性、需求不清楚、影响多个 bounded context、
  UI shell/navigation/design token 级变更、预计大 diff（跨子系统 ≥400 行或总计 ≥1000 行）
- Simple 档小改动（单文件 <20 行）可不出计划直接实现；但命中 strict 触发条件的改动必须先出计划
- 质量、延迟、兼容性等经验事实不靠文档审批，先产生可审计证据（计划执行顺序里的证据步骤）。计划状态和写法
  见 `.agents/skills/vj-plan/SKILL.md`。

## 架构文档策略

当前 repo 事实放 `docs/project/`；产品意图（PRD 等）放 `docs/product/`；历史资料放
`docs/archive/`；执行产物放 `docs/work/`。API/Data/UI 稳定合同分别放
`docs/project/api|data|ui/`，只在对应 delta 出现时增量更新——合同跟随代码分层归 project/，
不按 product/platform 拆分。
完整维护规则见 `docs/reference/guides/ai-workflow.md`，archive 不是当前 baseline。

## Common Development Patterns

- Backend 变更先读 `.agents/skills/backend-dev-guidelines/SKILL.md`；DDD/UoW 约束以上文为准。
- Frontend 变更先读 `.agents/skills/frontend-dev-guidelines/SKILL.md`；canonical 数据流参考
  `frontend/src/features/home/`，复杂 feature 参考 `frontend/src/features/auth/`。
- 外部服务：application port -> infrastructure adapter -> composition root injection。
- 需要 UI/联调验证走 `vj-work` 内置的端到端验证或 `diff-aware-qa` / `web-access`，不在仓库引入另一套浏览器依赖。

## Development Guidelines

### Task Sizing

| Size | Criteria | Approach |
|------|----------|----------|
| **Simple** | Single file, <20 lines, local impact | Execute directly with minimal explanation |
| **Standard Story** | 2-5 files, bounded impact, requirements reasonably clear | Use `vj` Story track: Intent Contract + concise execution plan, then implement and verify |
| **Complex** | Architecture changes, multiple modules, high risk, or external references needed | `vj-plan` 计划文档（policy 通常为 strict）→ `vj-work` |

Complex workflow: RESEARCH → PLAN（`vj-plan`，需要外部参考时先 `story-reference-impl`）→ EXECUTE →
VERIFY（`vj-work` 内置的端到端验证，或最小定向验证）→ REVIEW（`review`）→ REGRESSION QA
（变更涉及 UI、路由、共享组件或高风险流程时跑 `diff-aware-qa`）。

动手前先回答：真问题还是过度设计？成功判据是什么（可观察的测试/接口响应/UI 行为）？
有什么可复用？影响半径多大？改共享代码前先用搜索/引用工具追完调用链。

### Testing Strategy

- **默认 TDD**: 测试用例从计划的验收清单推导，不从 AI 生成的代码推导
- **后端**: 在 `backend/` 内运行 pytest；测试放 `backend/tests/` 下的 `test_*.py`；
  异步测试用 `pytest-asyncio`，API 测试优先 `httpx.AsyncClient`；隔离副作用（事务 fixture 或清理 DB 状态）
- **联调 / UI**: 计划内由 `vj-work` 激活并跑端到端用例；计划外改动用 `diff-aware-qa`；页面交互/截图验证走全局 `web-access` skill
- **跳过条件**: 配置文件、生成代码、纯类型定义可跳过 TDD，需注释说明

人工审查分级：🔴 数据库操作/认证/核心业务规则 → 人工逐行；🟡 API 路由/服务编排/错误处理 →
AI review + 人扫一遍；🟢 DTO/数据搬运/UI 样式 → AI review + 测试覆盖。

### Prefer Existing Solutions Over Reinventing

- 设计自定义方案前，先找经过验证的库/框架：先搜代码库，本地不够再 web search
- 评估维度：维护活跃度、社区、与现有 stack 的契合度、license 可商用；选择自研必须说明为何现有方案不适用
- 过度工程红线：4+ 底层库拼一个常见场景；>200 行实现一个已被解决的问题；
  没有具体需求的"以后可能需要灵活性"
- 机器位：`vj-plan` 写关键设计前先查现成的库和方案，结论写成计划第 3 节的一条决定
  （直接用 / 改造 / 自研 + 理由）；"改造/深度借鉴"路径的实现期研究走 `story-reference-impl`

### Red Lines

- No copy-paste duplication
- Do not break existing external behaviour (unless deliberate refactor with documentation —
  behaviour changes require a clear callout, affected-consumer analysis, and updated tests)
- Do not proceed with a known-wrong approach
- Critical paths must have explicit error handling
- Never implement "blindly" - confirm understanding via code reading + references
- Do not add speculative features, abstractions, configuration, or extension points for future needs
- Do not refactor, reformat, rename, or clean up unrelated code while implementing a requested change
- Every changed line must trace back to the user request, the plan's acceptance checklist, verification, or cleanup caused by this change

### Quality & Cleanup

After changes: remove dead/commented-out code and debug logging introduced by this change;
remove unused imports; if a function signature changes, update **all** call sites; mention (not
silently change) unrelated dead code; run minimal verification (lint/test/build) for touched parts.

### Code Review Policy (AUTO-TRIGGER)

实现完成后、回复用户前，满足任一条件 → **必须**先用 `review` skill（或应用
`docs/reference/guides/review-checklist-python-fastapi.md`）审查当前变更：

- 修改 ≥ 2 个文件，或变更 ≥ 50 行
- 新建任何 `.py` / `.tsx` 文件
- 涉及 auth、输入校验、数据访问等安全面
- 触及 `domain/` 或 `infrastructure/repositories/`

仅当**全部**满足才可跳过：单文件、<20 行、无新文件、非安全敏感、非核心 domain。
**Review 未完成 = 任务未完成。** Blocking 问题必须修复后才能 signoff，除非用户明确接受风险。
（severity 分级、检查清单、输出格式见 `review` skill 本体，不在此重复。）

### Commit & PR Guidelines

- Commits: imperative, present tense, concise (e.g., "add user routes")
- PRs: clear description, linked issues, steps to test, migration notes, and screenshots or curl examples for new endpoints
- 涉及设计取舍的 commit 追加结构化 trailers（trivial commit 全部跳过；`.claude/settings.json`
  的 PreToolUse hook 会在 `git commit` 时提醒）：

| Trailer | Purpose | Example |
|---------|---------|---------|
| `Constraint:` | External limitation that shaped the decision | `Auth service does not support token introspection` |
| `Rejected:` | Alternative considered but not chosen（最有价值，DDD 分层/架构二选一时优先写） | `新建 ProfileService \| 只有2个方法，不值得拆聚合根` |
| `Confidence:` | Certainty level about this approach | `high \| medium \| low` |
| `Scope-risk:` | Blast radius of this change | `narrow \| moderate \| broad` |
| `Not-tested:` | Edge cases not covered by tests | `Concurrent updates to same profile` |

### Interaction Guidelines

- 问用户：多个合理方案并存、需求模糊、改动超出预期 scope、发现潜在风险
- 直接执行：需求明确且方案无歧义、小范围改动（<20 行）、用户已确认过同类操作
- Dare to say no：发现问题直说；不迁就已知错误的方案；有理有据地挑战假设
- 推荐纪律（给方案/建议时强制）：
  - 结论写成"证据表明 X；倾向 Y（置信度）；出现 Z 改判"，不给裸的"推荐 A"
  - 判据属于用户的决策（审美、产品取舍、用户工作流成本）→ 只摆 trade-off，用户裁决
  - 方案数量由决策空间结构导出（二元 / 刻度 / 多维拆开 / 全量枚举），禁止默认凑三个；
    列出的每个选项必须写得出最强版本，写不出的是稻草人，删掉
  - 可逆且便宜的分歧先原型给用户看，不打多轮嘴仗；用户否决后重申立场必须携带新证据

## Key References

入口地图见本文件开头的 Project Structure；workflow 见
`docs/reference/guides/ai-workflow.md`；backend/frontend 细节见对应 repo-local guideline skill。

## Tooling Note

优先 repo-local skills、shell + `rg`、触碰面的定向测试、`web-access` 浏览器验证和
`diff-aware-qa` 回归检查。不要依赖文档里过时的通用工具名。
