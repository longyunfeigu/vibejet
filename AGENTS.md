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
├── docs/              # Project facts, reusable references, archives, and task assets
│   ├── project/       # Current architecture, API conventions, and reusable data contracts
│   ├── reference/     # ADRs, guides, manuals, research notes
│   ├── archive/       # Historical / superseded docs, not current baseline
│   └── tasks/         # Active epics/stories and implementation plans
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

Known current gaps:
- JWT auth (login gate) is implemented, but routes such as files, storage, conversations, chat,
  and documents only require login — they are not safe to expose as product endpoints until
  ownership and role/tenant checks are added.
- Schema changes go through Alembic (baseline `0001` + incremental revisions are tracked in
  `backend/alembic/versions/`); do not rely on `create_tables()` in production.

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
  an attribute on the global abstract UoW.
- Application services should define small service-local `Protocol`s for the repositories they need
  (see `FileAssetUnitOfWork`, `ConversationUnitOfWork`, `ChatUnitOfWork`).
- Domain repository interfaces remain in `backend/domain/<module>/repository.py`; domain must not
  know about UoW or transactions.

## Coding Style & Conventions

- Python >= 3.11, PEP 8, 4-space indent; type hints required for public functions
- Names: files/modules/functions/vars `snake_case`; classes `CapWords`
- DTOs use Pydantic v2 models; validate at boundaries
- Logging: never `print`; use `core.logging_config.get_logger(__name__)` (structlog)
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
- 前端 `.env`: `VITE_API_URL`（Vite 代理 `/api` 请求到此地址，默认 `http://localhost:8000`）
- 两个 `.env` 均不提交 git；不提交任何 secrets；默认 CORS/dev 配置不得用于生产

## AI Workflow Entry Points

See `docs/reference/guides/ai-workflow.md` for the repo-level end-to-end workflow and skill selection guide.

Use the repo-local skills (`.agents/skills/`) instead of ad-hoc prompting when they match the task:

- `vj-feature` — 给已有项目追加功能：澄清需求，生成/追加 Epic+Story，可选同步 PRD，路由到实现
- `vj-design-md-matcher` — 产品/品牌方向轨：当 `DESIGN.md` 缺失/过期、品牌感不清、front-of-house 无 golden screen，或用户要求整体视觉升级时，先用产品级 `ui-requirement-brief` 明确方向，再生成 `docs/project/DESIGN.md` + golden references；不用于日常单屏结构/状态补全
- `ui-requirement-brief` / `ui-page-goal-structure` / `ui-state-coverage` / `ui-visual-consistency-audit` — 前端设计生产与审查辅助：产品级 brief 喂 `vj-design-md-matcher`；单屏级 brief 喂 `ui-page-goal-structure` / `ui-state-coverage` 产出页面体验地图和状态覆盖；稳定合同写入 `docs/project/DESIGN.md` 与 `docs/project/ui/`，由 `vj-epic-plan` / `vj-work` 消费
- `run-story` — Preferred single-entry Story workflow: route implementation, verify, review, and risk-based QA
- `do-story` — Standard Story implementation from Story file or Story description
- `story-reference-impl` — Complex Story that needs research against open source or framework implementations
- `story-verify-fix` — Post-implementation verification, front/back bring-up, integration checks, visual alignment
- `review` — Pre-landing code review using `docs/reference/guides/review-checklist-python-fastapi.md`
- `diff-aware-qa` — Second-layer regression QA driven by the current diff

## Plan 文件规范

- 进入 plan mode 实现 Story 时，plan 文件同步写到 `docs/tasks/plans/{date}-{story-id}-{slug}.md`
- 必须沿用 `docs/tasks/plans/TEMPLATE.md`：先做 §0 Triage（8 问 + 约束清单），按路由结果填
  Flow A（第 1 层）/ Flow B（第 1+2 层）/ Flow C（全部 3 层），所有 Flow 必填 §11 执行步骤
- **强制升级条件**（plan 阶段或开发中碰到任一条 → 至少 Flow B，开发中则暂停并升级 plan）：
  改 DB migration、改公共 API 契约、改权限/认证/安全、引入外部系统或异步任务、
  复杂状态机/幂等/事务一致性、需求不清楚、影响多个 bounded context

## 架构文档策略

| 类型 | 文件 | 维护时机 |
|------|------|---------|
| 永久基线 | `docs/project/architecture.md`（1 份 repo 级） | 有架构影响时更新 |
| 永久基线 | `AGENTS.md`（`CLAUDE.md` 经 `@AGENTS.md` 导入） | 规则变更时更新 |
| 永久基线 | `docs/project/*.md` | 对应项目事实或设计契约变化时更新 |
| 历史归档 | `docs/archive/` | 过期/被取代的文档需要保留但不再作为当前基线时 |
| 执行基线 | `docs/tasks/plans/TEMPLATE.md` | Plan 结构变更时更新 |
| 审查基线 | `docs/reference/guides/review-checklist-python-fastapi.md` | review 规则变更时更新 |
| 执行计划 | `docs/tasks/plans/{date}-{story-id}-{slug}.md` | 每次 feature 实现时 |
| 设计参考 | `docs/reference/research/designs/{epic-id}/{story-id}-{page}.png` | 有 UI 设计稿时 |
| 按需生成/更新 | `docs/project/api/{module}.md` | 由 `api-design` skill 在公共接口契约变化时增量更新 |
| 按需生成/更新 | `docs/project/data/{module}.md` | 由 `data-model` skill 在 schema / migration 变化时增量更新 |
| 按需生成/更新 | `docs/project/requirements.md`（PRD） | 由 `vj-product-requirements` 生成；需求变化时更新 |

重要边界：
- 当对应 `docs/project/api/{module}.md` 或 `docs/project/data/{module}.md` 不存在时，AI 不能声称"实现违反了这些文档"；
  只能判断"本次变更是否引入新的 API contract / schema / migration delta，需要补设计说明"
- 始终可以校验的，只有 repo 硬约束、Story 验收标准和现有代码模式
- `docs/archive/` 下的文档不是当前 baseline，除非用户明确要求恢复或基于归档资料继续实现

## Common Development Patterns

### Adding a New Backend Entity/Aggregate

1. Define entity in `backend/domain/<aggregate>/entity.py`
2. Define repository interface in `backend/domain/<aggregate>/repository.py`
3. Create ORM model in `backend/infrastructure/models/<aggregate>.py`
4. Implement repository in `backend/infrastructure/repositories/<aggregate>_repository.py`
5. Register the concrete repository in `backend/infrastructure/unit_of_work.py`
6. In the application service, define a service-local UoW `Protocol` listing only the repositories that service needs
7. Generate migration: `cd backend && alembic revision --autogenerate -m "add <aggregate>"`
8. Apply: `cd backend && alembic upgrade head`
9. Create application service in `backend/application/services/<aggregate>_service.py`
10. Add API routes in `backend/api/routes/<aggregate>.py`
11. Register routes in `backend/main.py`

### Adding a Frontend Feature

Stack: Vite 8 + React 19 + TS 6 (strict) + Tailwind v4 + shadcn/ui (Radix) + TanStack Router/Query + RHF + Zod + Vitest. UI 用 Tailwind utility class + shadcn 组件，**不用 MUI**。设计 token 唯一来源 `docs/project/DESIGN.md` → 编译进 `src/index.css` 的 CSS 变量。Full guidelines in `.agents/skills/frontend-dev-guidelines/SKILL.md`.

1. Create `frontend/src/features/<name>/` with subdirs: `api/`, `components/`, `hooks/`, `types/` (and `helpers/` if needed)
2. Wrap backend endpoint in `api/<name>Api.ts` using `apiClient` from `@/lib/apiClient`
3. Create `useSuspenseQuery` wrapper in `hooks/use<Name>.ts`
4. UI component in `components/<Name>Card.tsx`：用 shadcn 组件（`@/components/ui/*`）+ Tailwind class + `cn()`，consumes the hook (no early-return loading; rely on outer `<SuspenseLoader>`)
5. 需要的 shadcn 组件用 `npx shadcn@latest add <component>` 拉进 `@/components/ui/`（网络抖动时见 SKILL.md 的 curl 兜底）
6. Register route at `frontend/src/routes/<name>/index.tsx` with `createFileRoute` + `lazy` + `<SuspenseLoader>`
7. Run `pnpm dev` once to regenerate `src/routeTree.gen.ts` (tracked file, do not hand-edit)

Reference impl: `frontend/src/features/health/` + `frontend/src/routes/health/`.
If the task is verification-only, use `story-verify-fix`. If design refs exist, store them under
`docs/reference/research/designs/{epic-id}/` and reference them from the Story or plan.

### Adding External Service Integration

1. Define port interface in `backend/application/ports/<service>.py`
2. Implement client in `backend/infrastructure/external/<service>/<provider>.py`
3. Initialize in `backend/main.py` lifespan
4. Inject via dependency in API routes

## Development Guidelines

### Task Sizing

| Size | Criteria | Approach |
|------|----------|----------|
| **Simple** | Single file, <20 lines, local impact | Execute directly with minimal explanation |
| **Standard Story** | 2-5 files, bounded impact, requirements reasonably clear | Use `do-story` or a concise execution plan, then implement |
| **Complex** | Architecture changes, multiple modules, high risk, or external references needed | Write a plan per `docs/tasks/plans/TEMPLATE.md` + the appropriate skill workflow |

Complex workflow: RESEARCH → PLAN（TEMPLATE.md 或 `story-reference-impl`）→ EXECUTE →
VERIFY（`story-verify-fix` 或最小定向验证）→ REVIEW（`review`）→ REGRESSION QA
（变更涉及 UI、路由、共享组件或高风险流程时跑 `diff-aware-qa`）。

动手前先回答：真问题还是过度设计？成功判据是什么（可观察的测试/接口响应/UI 行为）？
有什么可复用？影响半径多大？改共享代码前先用搜索/引用工具追完调用链。

### Testing Strategy

- **默认 TDD**: 测试用例从 Story 验收标准（Given-When-Then）推导，不从 AI 生成的代码推导
- **后端**: 在 `backend/` 内运行 pytest；测试放 `backend/tests/` 下的 `test_*.py`；
  异步测试用 `pytest-asyncio`，API 测试优先 `httpx.AsyncClient`；隔离副作用（事务 fixture 或清理 DB 状态）
- **联调 / UI**: 用 `story-verify-fix`；需要页面交互时优先用 `playwright-interactive`
- **跳过条件**: 配置文件、生成代码、纯类型定义可跳过 TDD，需注释说明

人工审查分级：🔴 数据库操作/认证/核心业务规则 → 人工逐行；🟡 API 路由/服务编排/错误处理 →
AI review + 人扫一遍；🟢 DTO/数据搬运/UI 样式 → AI review + 测试覆盖。

### Prefer Existing Solutions Over Reinventing

- 设计自定义方案前，先找经过验证的库/框架：先搜代码库，本地不够再 web search
- 评估维度：维护活跃度、社区、与现有 stack 的契合度；选择自研必须说明为何现有方案不适用
- 过度工程红线：4+ 底层库拼一个常见场景；>200 行实现一个已被解决的问题；
  没有具体需求的"以后可能需要灵活性"

### Red Lines

- No copy-paste duplication
- Do not break existing external behaviour (unless deliberate refactor with documentation —
  behaviour changes require a clear callout, affected-consumer analysis, and updated tests)
- Do not proceed with a known-wrong approach
- Critical paths must have explicit error handling
- Never implement "blindly" - confirm understanding via code reading + references
- Do not add speculative features, abstractions, configuration, or extension points for future needs
- Do not refactor, reformat, rename, or clean up unrelated code while implementing a requested change
- Every changed line must trace back to the user request, Story acceptance criteria, verification, or cleanup caused by this change

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
- 涉及设计取舍的 commit 追加结构化 trailers（trivial commit 全部跳过；PreToolUse hook 会在 `git commit` 时提醒）：

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

## Key References

### Backend
- REST entrypoint: `backend/main.py`
- gRPC entrypoint: `backend/grpc_main.py`
- Config: `backend/core/config.py`
- Dependency wiring: `backend/api/dependencies.py`
- UoW port: `backend/application/ports/unit_of_work.py`
- UoW implementation: `backend/infrastructure/unit_of_work.py`
- Database: `backend/infrastructure/database.py`

### Frontend
- Dev entrypoint: `frontend/src/main.tsx`
- Routes (file-based): `frontend/src/routes/` (e.g. `routes/index.tsx`, `routes/health/index.tsx`)
- Features: `frontend/src/features/` (each: `api/`, `components/`, `hooks/`, `types/`)
- shadcn 组件（vendored）: `frontend/src/components/ui/`（`npx shadcn add` 生成，可改）；布局: `frontend/src/components/layout/`
- 样式工具: `frontend/src/lib/utils.ts` 的 `cn()`（clsx + tailwind-merge）；设计 token: `frontend/src/index.css`（`@theme` + `:root`，源自 `docs/project/DESIGN.md`）
- Toast: 直接用 `sonner`（`import { toast } from 'sonner'`；`<Toaster/>` 已挂在 `main.tsx`）
- Reusable infra: `frontend/src/components/SuspenseLoader/`
- API client: `frontend/src/lib/apiClient.ts` (axios, `baseURL = VITE_API_URL`, `withCredentials`)
- Auth hook (placeholder): `frontend/src/hooks/useAuth.ts`
- Path alias: `@/` → `src/`（单一别名，configured in `tsconfig.app.json` + `vite.config.ts` + `vitest.config.ts`）
- Vite config: `frontend/vite.config.ts` (proxies `/api/*` to `VITE_API_URL`)
- Guidelines: `.agents/skills/frontend-dev-guidelines/SKILL.md`

### Workflow
- Plan template: `docs/tasks/plans/TEMPLATE.md`
- Review checklist: `docs/reference/guides/review-checklist-python-fastapi.md`
- Verify-fix design: `docs/reference/guides/story-verify-fix-design.md`
- Skills: `.agents/skills/`

## Tooling Note

Do not rely on stale generic tool names in this document. Prefer:

- repo-local skills under `.agents/skills/`
- shell + `rg` for codebase search
- targeted tests and verification commands from `backend/`
- `story-verify-fix` + `playwright-interactive` for browser-based validation
- `diff-aware-qa` for post-implementation regression checks scoped to the current diff
