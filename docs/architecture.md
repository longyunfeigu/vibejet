# vibejet Architecture

`vibejet` is a FastAPI foundation library and application scaffold. It should provide reusable
technical building blocks, not a finished product domain. Downstream projects own their specific
business modules, policies, roles, workflows, and product requirements.

## Goals

- Provide a production-oriented backend base for REST, gRPC, persistence, storage, messaging,
  background tasks, i18n, observability, and testing.
- Keep domain code independent from FastAPI, SQLAlchemy, SDKs, queues, and other infrastructure.
- Make downstream business code easy to add without changing the core framework shape.
- Keep documentation generic unless it describes a reusable platform capability.

## Non-Goals

- Do not define product PRDs, personas, growth loops, market-specific flows, or other
  application-specific requirements in this base repository.
- Do not put concrete business decisions into shared exceptions, response codes, middleware, or
  framework utilities.
- Do not make generated story or epic artifacts permanent baseline docs for the base library.

## Layering

The backend follows DDD-style layering with hexagonal boundaries.

```text
api -> application -> domain
infrastructure -> application/domain interfaces
```

`domain/`
: Pure entities, value objects, domain services, repository interfaces, and domain exceptions.
  It must not import `api`, `application`, `infrastructure`, FastAPI, SQLAlchemy, Redis, Kafka,
  storage SDKs, or LLM SDKs.

`application/`
: Use-case orchestration, DTOs, transaction boundaries, and ports. Application services coordinate
  domain objects and depend on interfaces rather than concrete infrastructure implementations.

`infrastructure/`
: SQLAlchemy models, repository implementations, external clients, storage providers, messaging
  drivers, Celery tasks, and concrete adapters for application ports.

`api/`
: FastAPI routes, dependencies, middleware, request parsing, response formatting, and HTTP error
  translation. Routes should stay thin and delegate use cases to `application/`.

`core/`
: Configuration, logging, exception handlers, observability helpers, and response primitives that
  are shared by the runtime.

`shared/`
: Cross-cutting constants and small utilities that do not belong to a specific domain.

## Current Foundation Capabilities

The base library currently provides these reusable capabilities:

| Capability | Main Paths | Notes |
|------------|------------|-------|
| REST runtime | `backend/main.py`, `backend/api/` | FastAPI app, versioned routes under `/api/v1`, middleware, OpenAPI |
| gRPC runtime | `backend/grpc_app/`, `backend/grpc_main.py` | Parallel transport for services that need gRPC |
| Persistence | `backend/infrastructure/database.py`, `backend/alembic/` | Async SQLAlchemy and Alembic migrations |
| Repository/UoW | `backend/domain/common/`, `backend/infrastructure/repositories/`, `backend/infrastructure/unit_of_work.py` | Generic persistence boundary patterns |
| File storage | `backend/application/ports/storage.py`, `backend/infrastructure/external/storage/` | Local, S3, and OSS providers behind a storage port |
| Messaging | `backend/infrastructure/external/messaging/` | Kafka driver abstraction with retry/DLQ-oriented configuration |
| Background tasks | `backend/infrastructure/tasks/` | Celery app, task base, and dispatcher pattern |
| Observability | `backend/core/observability/`, `backend/api/routes/health.py`, `backend/api/routes/metrics.py` | Health checks, metrics, tracing hooks |
| i18n | `backend/core/i18n.py`, `backend/locales/` | Babel-based message catalogs |
| Testing | `backend/tests/`, `backend/pyproject.toml` | pytest, async test support, repository and config tests |

If a capability starts to encode one application's business language, move that code into the
downstream project or mark it as an example that can be removed.

## Extension Rules

When adding a new downstream business module:

1. Add domain objects under `backend/domain/<module>/`.
2. Add repository interfaces in the domain layer.
3. Add application services and DTOs under `backend/application/`.
4. Add infrastructure models, repositories, external clients, and migrations under
   `backend/infrastructure/`.
5. Add HTTP routes under `backend/api/routes/` and register them in `backend/main.py`.
6. Add tests under `backend/tests/`.

Keep the dependency direction unchanged. If an application service needs an external system, define
a port in `application/ports/` and implement it in `infrastructure/`.

## Documentation Rules

- Keep repo-level docs focused on reusable architecture, development workflow, review standards,
  and planning templates.
- Product PRDs, epics, routing datasets, launch articles, and app-specific examples should live
  in downstream application repositories.
- Temporary implementation plans can be created under `docs/plans/`, but they should be removed or
  archived once they are no longer useful as reusable guidance.
- If a generated doc describes a concrete app, do not treat it as part of the base library baseline.
