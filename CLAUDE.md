# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
│   ├── archive/       # Historical/downstream product docs, not current baseline
│   └── tasks/         # Active epics/stories and implementation plans
├── .agents/skills/    # Repo-local AI workflow skills
└── docker-compose.yml
```

**Entry Points**:
- REST API: `backend/main.py`
- gRPC: `backend/grpc_main.py`
- Backend tests: `backend/tests/`
- Frontend dev: `frontend/src/main.tsx`
- Frontend routes: `frontend/src/routes/` (TanStack Router file-based)
- Frontend features: `frontend/src/features/`
- Frontend build: `frontend/dist/`

## Current Baseline

`vibejet` is currently maintained as a FastAPI foundation library and application scaffold, not
as a concrete product domain. Current project facts live under `docs/project/`; archived
downstream-product material lives under `docs/archive/`.

Archived internal exam-platform docs were moved to `docs/archive/exam-platform/`. Treat them as
historical context only. Do not use archived PRDs, epics, API contracts, data models, or design
prompts as current requirements unless the user explicitly promotes them back into the active
project.

Known current gaps:
- No production auth module is implemented. Scaffold routes such as files, storage, conversations,
  and chat are not safe to expose as product endpoints until a downstream project adds actor,
  ownership, and role/tenant checks.
- `backend/alembic/versions/` has no tracked baseline migrations yet. Production schema changes
  must be made through Alembic, not by relying on `create_tables()`.
- `docs/project/data/` currently has no product schema contracts beyond its README.

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

**Domain Service** (`domain/*/service.py`):
- Pure business rules, multiple entities/aggregates
- Business validation (e.g., username uniqueness)
- Business invariants (e.g., "superuser cannot be deactivated")
- **No external system dependencies**

**Application Service** (`application/services/*_service.py`):
- Orchestrates domain + external systems
- Technical concerns: HTTP calls, SDK, caching, distributed locks
- DTO mapping, transaction boundaries (UoW)

### Unit of Work Shape

- UoW is an application-layer transaction boundary: `backend/application/ports/unit_of_work.py`
- Concrete SQLAlchemy implementation: `backend/infrastructure/unit_of_work.py`
- The central UoW port must stay repository-agnostic. Do not add every new module's repository as
  an attribute on the global abstract UoW.
- Application services should define small service-local `Protocol`s for the repositories they need
  (see `FileAssetUnitOfWork`, `ConversationUnitOfWork`, `ChatUnitOfWork`).
- Domain repository interfaces remain in `backend/domain/<module>/repository.py`; domain must not
  know about UoW or transactions.

## Development Environment

| 项目 | 工具 | 启动命令 | 配置文件 |
|------|------|----------|----------|
| 后端 | uv + `backend/.venv/` | `cd backend && uv run python main.py` | `backend/.env` |
| 前端 | pnpm + Vite | `cd frontend && pnpm dev` | `frontend/.env` |
| 测试 | uv + pytest | `cd backend && uv run pytest tests/ -v` | - |

- 后端 `.env`: `SECRET_KEY`, `DATABASE__URL`, `DEBUG`
- 前端 `.env`: `VITE_API_URL`（Vite 代理 `/api` 请求到此地址，默认 `http://localhost:8000`）
- 两个 `.env` 均不提交 git

## AI Workflow Entry Points

See `docs/reference/guides/ai-workflow.md` for the repo-level end-to-end workflow and skill selection guide.

Use the repo-local skills instead of ad-hoc prompting when they match the task:

- `vj-feature`
  - 给已有项目追加功能：从功能想法出发，对话澄清需求，生成/追加 Epic+Story，可选同步 PRD，路由到实现
- `run-story`
  - Preferred single-entry Story workflow: route implementation, verify, review, and risk-based QA
- `do-story`
  - Standard Story implementation from Story file or Story description
- `story-reference-impl`
  - Complex Story that needs research against open source or framework implementations
- `story-verify-fix`
  - Post-implementation verification, front/back bring-up, integration checks, visual alignment
- `review`
  - Pre-landing code review using `docs/reference/guides/review-checklist-python-fastapi.md`
- `diff-aware-qa`
  - Second-layer regression QA driven by the current diff, focused on affected pages and adjacent surfaces

## Plan 文件规范

进入 plan mode 实现 Story 时，plan 文件同步写到 `docs/tasks/plans/{date}-{story-id}-{slug}.md`。

Plan 采用 **Triage + 3 层渐进式结构**。如果 `docs/tasks/plans/TEMPLATE.md` 存在，优先沿用该模板；否则按本节结构创建 plan。

### Triage 分级器（Plan §0）

AI 在 plan mode 探索代码后回答 8 问 + 填写约束清单：

1. 是否只服务一个明确的用户目标？
2. 是否只影响一个业务模块？
3. 是否不改数据库 schema / migration？
4. 是否不改公共 API 契约？
5. 是否不涉及 domain 规则变化？
6. 是否不涉及外部系统、Celery、缓存、消息队列？
7. 是否不涉及权限、安全、幂等、复杂状态流转？
8. 预估是否只改少量文件且不超过 2 层？

**约束清单**（8 问之后必填）：
- **硬约束**：AC 明确要求的数字、格式、行为
- **隐含约束**：从现有代码/架构推导出的（已有的库、接口模式、配置）
- **需确认**：AC 没说也推不出的，必须问用户（不要猜）

**路由规则**：

| 条件 | Flow | Plan 深度 |
|------|------|----------|
| 8 问全"是" | **Flow A**（局部实现） | 只填第 1 层 |
| 1-3 个"否" | **Flow B**（多层改动） | 填第 1+2 层 |
| 4+ 个"否" | **Flow C**（高风险变更） | 填全部 3 层 |

**强制升级条件**（碰到任一条 → 至少 Flow B）：改 DB migration、改公共 API 契约、改权限/认证/安全、引入外部系统或异步任务、复杂状态机/幂等/事务一致性、需求不清楚、影响多个 bounded context。

### Plan 层级

- **§0 Triage**（必填）: 8 问判定 → Flow A/B/C
- **第 1 层**（Flow A/B/C 必填）: 目标、范围、影响范围、风险、验收标准
- **第 2 层**（Flow B/C）: 术语、当前现状、方案概述、核心流程图
- **第 3 层**（Flow C）: 关键实现细节（DB 迁移/缓存/幂等/事务/并发）
- **§11 执行步骤**（所有 Flow）: 每步 = 一个 task，完成后 commit

### 按需加载

| 条件 | 触发节 |
|------|--------|
| 5+ 新概念 | §6 术语 |
| 流程/状态/异步/外部调用变化 | §9 流程图 |
| DB 迁移/缓存/幂等/事务/并发 | §10 实现细节 |
| 都不满足 | 只填第 1 层 + §11 |

### 动态升级规则

开发中发现超出 Triage 预期 → AI 必须暂停并升级：
- 发现要改 DB → 升级
- 发现要改 API 契约 → 升级
- 发现跨层超出预期 → 升级
- 发现需求有歧义 → 暂停确认

### Flow 与产出物对照

| | Flow A | Flow B | Flow C |
|---|---|---|---|
| Plan 深度 | 第 1 层 | 第 1+2 层 | 全部 3 层 |
| API docs | 不更新 | 改公共接口时按需更新 `docs/project/api/{module}.md` | 稳定公共接口契约必须更新 |
| Data docs | 不更新 | 改 schema/migration 时按需更新 `docs/project/data/{module}.md` | 稳定持久化模型必须更新 |
| ADR | 不需要 | 有架构影响时补 | 必须补 |

## 架构文档策略

| 类型 | 文件 | 维护时机 |
|------|------|---------|
| 永久基线 | `docs/project/architecture.md`（1 份 repo 级） | 有架构影响时更新 |
| 永久基线 | `CLAUDE.md` + `AGENTS.md` | 规则变更时更新 |
| 永久基线 | `docs/project/*.md` | 对应项目事实或设计契约变化时更新 |
| 历史归档 | `docs/archive/` | 下游产品/过期计划需要保留但不再作为当前基线时 |
| 执行基线 | `docs/tasks/plans/` | Plan 结构变更时更新 |
| 审查基线 | `docs/reference/guides/review-checklist-python-fastapi.md` | review 规则变更时更新 |
| 执行计划 | `docs/tasks/plans/{date}-{story-id}-{slug}.md` | 每次 feature 实现时 |
| 设计参考 | `docs/reference/research/designs/{epic-id}/{story-id}-{page}.png` | 有 UI 设计稿时 |
| 按需生成/更新 | `docs/project/api/{module}.md` | 由 `api-design` skill 在公共接口契约变化时增量更新 |
| 按需生成/更新 | `docs/project/data/{module}.md` | 由 `data-model` skill 在 schema / migration 变化时增量更新 |
| 按需生成 | 下游应用 PRD | 由 `vj-product-requirements` 在具体产品仓库中生成后维护；不作为 vibejet 基础库常驻文档 |

触发判断在 Plan §0 Triage 的影响判定中完成。

重要边界：
- 当对应 `docs/project/api/{module}.md` 或 `docs/project/data/{module}.md` 不存在时，AI 不能声称“实现违反了这些文档”
- 这时只能判断“本次变更是否引入新的 API contract / schema / migration delta，需要补设计说明”
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

Stack: Vite 8 + React 19 + TS 6 (strict) + MUI v9 + TanStack Router/Query + RHF + Zod + Vitest. Full guidelines in `.agents/skills/frontend-dev-guidelines/SKILL.md`.

1. Create `frontend/src/features/<name>/` with subdirs: `api/`, `components/`, `hooks/`, `types/` (and `helpers/` if needed)
2. Wrap backend endpoint in `api/<name>Api.ts` using `apiClient` from `@/lib/apiClient`
3. Create `useSuspenseQuery` wrapper in `hooks/use<Name>.ts`
4. UI component in `components/<Name>Card.tsx` consumes the hook (no early-return loading; rely on outer `<SuspenseLoader>`)
5. Register route at `frontend/src/routes/<name>/index.tsx` with `createFileRoute` + `lazy` + `<SuspenseLoader>`
6. Run `pnpm dev` once to regenerate `src/routeTree.gen.ts` (tracked file, do not hand-edit)

Reference impl: `frontend/src/features/health/` + `frontend/src/routes/health/`.

If the task is verification-only, use `story-verify-fix` for bring-up / integration / visual alignment.
If design refs exist, store them under `docs/reference/research/designs/{epic-id}/` and reference them from the Story or plan.

### Adding External Service Integration

1. Define port interface in `backend/application/ports/<service>.py`
2. Implement client in `backend/infrastructure/external/<service>/<provider>.py`
3. Initialize in `backend/main.py` lifespan
4. Inject via dependency in API routes

## Development Guidelines

### Before Touching Code

Ask before implementation:
1. **Real issue or over-design?** - Is this truly needed or just an assumption?
2. **Success criteria?** - What observable test, API response, UI behavior, or command output proves this is done?
3. **Reuse opportunities?** - What existing code, pattern, or library can be leveraged?
4. **Impact radius?** - What might break, and who depends on this?
5. **Call chain traced?** - Use the available code search / reference lookup tools before modifying shared code

### Testing Strategy

- **默认 TDD**: 测试用例从 Story 验收标准（Given-When-Then）推导，不从 AI 生成的代码推导
- **后端**: 在 `backend/` 内运行 pytest；当前测试主要位于 `backend/tests/`
- **联调 / UI**: 用 `story-verify-fix` 执行服务启动、联调验证、可选视觉检查
- **浏览器执行器**: 需要页面交互时，优先用 `playwright-interactive`
- **详细 Story 流程**: 标准实现走 `do-story`；复杂参考实现走 `story-reference-impl`
- **跳过条件**: 配置文件、生成代码、纯类型定义可跳过 TDD，需注释说明

#### 选择性人工审查

| 风险等级 | 代码类型 | 审查方式 |
|----------|----------|----------|
| 🔴 高 | 数据库操作、认证、核心业务规则 | 人工逐行审查 |
| 🟡 中 | API 路由、服务编排、错误处理 | AI review + 人扫一遍 |
| 🟢 低 | DTO、数据搬运、UI 样式 | AI review 即可，测试覆盖 |

### Prefer Existing Solutions Over Reinventing

**Default stance**: Search for battle-tested libraries/frameworks BEFORE designing custom solutions.

| Scenario | Bad (Reinventing) | Good (Reuse) |
|----------|-------------------|--------------|
| Web crawling for AI | httpx + bs4 + trafilatura from scratch | Firecrawl, Crawl4AI, Scrapy |
| PDF parsing | PyPDF2 + custom layout logic | Unstructured, LlamaParse, MinerU |
| Vector search | Manual embedding + similarity | LangChain, LlamaIndex integrations |
| Auth system | JWT + session from scratch | Authlib, FastAPI-Users |

**Decision Process**:
1. **Search first**: Search the codebase first; use web search only when local context is insufficient or the answer may have changed
2. **Evaluate**: Stars, maintenance, community, fit with existing stack
3. **Justify custom**: Only build from scratch if existing solutions genuinely don't fit
4. **Document why**: If choosing custom, explain why existing options were rejected

**Red flags for over-engineering**:
- Combining 4+ low-level libs for a common use case
- Writing >200 lines for something that's a solved problem
- "We might need flexibility later" without concrete requirements

### Task Sizing

| Size | Criteria | Approach |
|------|----------|----------|
| **Simple** | Single file, <20 lines, local impact | Execute directly with minimal explanation |
| **Standard Story** | 2-5 files, bounded impact, requirements reasonably clear | Use `do-story` or a concise execution plan, then implement |
| **Complex** | Architecture changes, multiple modules, high risk, or external references needed | Use the Plan 文件规范 and the appropriate skill workflow |

#### Mandatory Gates for Complex Work

Before writing code for architecture-heavy or high-risk work:

1. **Search for existing solutions FIRST**:
   - Search the codebase first
   - If the task needs external reference, use `story-reference-impl`
   - If reusable solution exists → prefer reuse over custom implementation

2. Write or update a plan in `docs/tasks/plans/{date}-{story-id}-{slug}.md` using the Plan 文件规范 above

3. Explicitly call out:
   - Reuse opportunities
   - Scope boundaries / not-in-scope
   - Failure modes
   - Validation strategy

4. Stop for confirmation only when there is genuine ambiguity, major tradeoff, or scope expansion

#### Complex Task Workflow

When task meets "Complex" criteria or user says "进入X模式":

| Phase | Action |
|-------|--------|
| **RESEARCH** | Investigate code and gather context |
| **PLAN** | Use the Plan 文件规范 or `story-reference-impl` |
| **EXECUTE** | Implement per plan |
| **VERIFY** | Run `story-verify-fix` or minimal targeted verification |
| **REVIEW** | Run `review` on the resulting diff |
| **REGRESSION QA** | Run `diff-aware-qa` when the change touches UI, routing, shared components, or high-risk flows |

### Refactor Policy

When existing code is a "big ball of mud", prefer **clean refactor** over patching.

**Behaviour changes require**:
- Clear callout that this is a behaviour/protocol change
- Explanation of why and which consumers are affected
- Updated or new tests covering the change

### Red Lines

- No copy-paste duplication
- Do not break existing external behaviour (unless deliberate refactor with documentation)
- Do not proceed with a known-wrong approach
- Critical paths must have explicit error handling
- Never implement "blindly" - confirm understanding via code reading + references
- Do not add speculative features, abstractions, configuration, or extension points for future needs
- Do not refactor, reformat, rename, or clean up unrelated code while implementing a requested change
- Every changed line must trace back to the user request, Story acceptance criteria, verification, or cleanup caused by this change

### Commit Trailers

When a commit involves design trade-offs, append structured trailers to the commit message. This records **why alternatives were rejected** — information that code alone cannot convey.

| Trailer | Purpose | Example |
|---------|---------|---------|
| `Constraint:` | External limitation that shaped the decision | `Auth service does not support token introspection` |
| `Rejected:` | Alternative considered but not chosen | `新建 ProfileService \| 只有2个方法，不值得拆聚合根` |
| `Confidence:` | Certainty level about this approach | `high \| medium \| low` |
| `Scope-risk:` | Blast radius of this change | `narrow \| moderate \| broad` |
| `Not-tested:` | Edge cases not covered by tests | `Concurrent updates to same profile` |

Rules:
- All trailers are **optional** — only include what's relevant
- **Skip entirely** for trivial commits (typos, formatting, deps bump)
- `Rejected:` is the most valuable — prioritize when DDD layer placement or architectural alternatives were considered
- A PreToolUse hook will remind you about trailers when running `git commit`

### Quality & Cleanup

After changes:
- Remove dead/commented-out code introduced by the current change
- Mention unrelated dead code or cleanup opportunities instead of changing them silently
- Remove unused imports
- Remove debug logging no longer needed
- If you change a function signature, update **all** call sites
- Run minimal verification (lint/test/build) for touched parts

### ⛔ Code Review Policy (AUTO-TRIGGER)

**⚠️ CRITICAL: Code review is part of the task workflow, NOT a separate step.**

#### Auto-Trigger Conditions

**You MUST automatically invoke code review agent when ANY of these are true:**

| Condition | Threshold | Auto-Review |
|-----------|-----------|-------------|
| Files modified | ≥ 2 files | ✅ MUST |
| Lines changed | ≥ 50 lines | ✅ MUST |
| New file created | Any `.py` or `.tsx` file | ✅ MUST |
| Security-related | Auth, validation, data access | ✅ MUST |
| Core domain | `domain/`, `infrastructure/repositories/` | ✅ MUST |

**Skip review ONLY when ALL of these are true:**
- Single file modified
- Less than 20 lines changed
- No new files created
- Not security-sensitive
- Not core domain logic

#### Enforcement Mechanism

**After completing implementation, BEFORE responding to user:**

```
1. Count files modified → if ≥ 2, trigger review
2. Count lines changed → if ≥ 50, trigger review
3. Check if new .py/.tsx created → if yes, trigger review
4. If any trigger met → MUST use the repo-local `review` skill or apply `docs/reference/guides/review-checklist-python-fastapi.md`
5. If NO triggers met → respond directly
```

**⛔ VIOLATION = Incomplete task. You have NOT finished the task until review is done (when required).**

#### How to Invoke

```
Use the `review` skill
```

**Prompt template:**
```
使用 review，审查当前变更，优先找 blocking 问题、回归风险和缺失测试。

如需指定范围：
- [list files]
- [key changes]
- [focus areas]
```

**User trigger phrases:** "Review the changes" / "Run code review" / "代码审查"

#### Review Checklist

- [ ] Logic: edge cases, null checks, race conditions
- [ ] Security: input validation, injection, XSS, secrets
- [ ] Performance: N+1, loops, memory leaks
- [ ] Maintainability: naming, SRP, no magic numbers

#### Severity Labels

| Label | Meaning | Action |
|-------|---------|--------|
| 🔴 [blocking] | Must fix | Required before merge |
| 🟡 [important] | Should fix | Discuss if disagree |
| 🟢 [nit] | Nice to have | Optional |
| 💡 [suggestion] | Alternative | Consider |

**Post-review:** Fix all 🔴 [blocking] issues before signoff unless the user explicitly accepts the risk.

### Interaction Guidelines

**When to Ask User**:
- Multiple reasonable approaches exist
- Requirements are unclear or ambiguous
- Scope of change exceeds expectations
- Potential risks discovered

**When to Execute Directly**:
- Requirements are clear and solution is unambiguous
- Small-scope changes (< 20 lines)
- User has confirmed similar operations before

**Dare to Say No**:
- Point out problems directly when discovered
- Never compromise on known-wrong approaches
- Challenge assumptions respectfully but firmly

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
- Shared UI components: `frontend/src/components/ui/`, `frontend/src/components/layout/`
- Reusable infra: `frontend/src/components/SuspenseLoader/`, `frontend/src/hooks/useMuiSnackbar.ts`
- API client: `frontend/src/lib/apiClient.ts` (axios, `baseURL = VITE_API_URL`)
- Auth hook (placeholder): `frontend/src/hooks/useAuth.ts`
- Path aliases: `@/` → `src/`, `~types/`, `~components/`, `~features/` (configured in `tsconfig.app.json` + `vite.config.ts` + `vitest.config.ts`)
- Vite config: `frontend/vite.config.ts` (proxies `/api/*` to `VITE_API_URL`)
- Environment: `frontend/.env` (`VITE_API_URL`)
- Guidelines: `.agents/skills/frontend-dev-guidelines/SKILL.md`

### Workflow
- Plan directory: `docs/tasks/plans/`
- Review checklist: `docs/reference/guides/review-checklist-python-fastapi.md`
- Verify-fix design: `docs/reference/guides/story-verify-fix-design.md`
- Archived exam-platform docs: `docs/archive/exam-platform/`
- Skills: `.agents/skills/`

## Tooling Note

Do not rely on stale generic tool names in this document.

Prefer:

- repo-local skills under `.agents/skills/`
- shell + `rg` for codebase search
- targeted tests and verification commands from `backend/`
- `story-verify-fix` + `playwright-interactive` for browser-based validation
- `diff-aware-qa` for post-implementation regression checks scoped to the current diff
