# Backend Constitution

Read this before every backend code change. These rules are non-negotiable unless the user explicitly asks for an architecture change and the architecture docs are updated in the same work.

## Architecture

The backend follows DDD-style hexagonal layering:

```text
api -> application -> domain
infrastructure -> application/domain interfaces
```

Truth source: `docs/project/architecture.md`.

## Hard Boundaries

- `domain/` contains pure entities, value objects, domain services, repository interfaces, and domain exceptions.
- `domain/` must not import `api`, `application`, `infrastructure`, FastAPI, SQLAlchemy, Redis, Kafka, storage SDKs, LLM SDKs, or other concrete external clients.
- `application/` contains use-case orchestration, DTOs, transaction boundaries, and ports.
- `application/` must not import ORM models, FastAPI request/response classes, concrete infrastructure clients, SQLAlchemy sessions, or transport-specific concerns.
- `api/` contains FastAPI routes, dependencies, middleware, request parsing, response formatting, and HTTP error translation.
- `api/` must not directly operate repositories, ORM models, SQLAlchemy sessions, or business invariants.
- `infrastructure/` implements domain/application interfaces and owns ORM models, repository implementations, external clients, storage providers, messaging drivers, Celery tasks, and adapters.
- `core/` owns configuration, response primitives, exception handlers, logging, and observability helpers.

## API Contract

- Business REST endpoints live under `/api/v1`.
- Business endpoints return `core.response.Response[T]`.
- Operational endpoints such as `/health*`, `/metrics`, and `/` return raw JSON and do not use the business envelope.
- Use `core.response.success_response`, `paginated_response`, and global exception handlers. Do not hand-roll response envelopes.
- New business endpoints are default-deny: protect them with `get_current_user`, `require_role`, or an explicit reviewed public-endpoint decision.

Truth source: `docs/project/api/conventions.md`.

## Error Model

- Expected business failures should use `domain.common.exceptions.BusinessException` or module-specific domain exceptions.
- Domain validation failures use `DomainValidationException`.
- HTTP exceptions are reserved for transport/auth adapter cases where existing code already uses them.
- Expected 4xx business paths are not Sentry noise by default. Log/report unexpected failures, data consistency risks, and external system failures.

## Documentation Triggers

- If a public API contract changes, update the relevant file under `docs/project/api/`.
- If persistent schema, migration, indexes, or constraints change, update the relevant file under `docs/project/data/`.
- If a decision changes architecture, cross-layer dependency direction, or integration strategy, add or update an ADR under `docs/reference/adrs/`.

## Controller Policy

Controller is not a default layer in vibejet. The default shape is:

```text
FastAPI route -> application service -> domain -> repository interface
infrastructure repository -> ORM/database
```

Add a controller only when an existing module already uses that layer or a reviewed design requires a separate HTTP orchestration adapter.

## Golden Existing Examples

Prefer nearby code and these representative files over generic snippets:

- API route: `backend/api/routes/conversations.py`
- Application service: `backend/application/services/conversation_service.py`
- Domain entity: `backend/domain/conversation/entity.py`
- Repository implementation: `backend/infrastructure/repositories/conversation_repository.py`
- Response and exceptions: `backend/core/response.py`, `backend/core/exceptions.py`
