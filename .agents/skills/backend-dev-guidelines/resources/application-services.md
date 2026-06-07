# Application Services

Use this for `backend/application/services/`, `backend/application/dto.py`, `backend/application/dtos/`, and `backend/application/ports/`.

## Responsibilities

- Orchestrate use cases across domain objects, repository interfaces, ports, and transaction boundaries.
- Own Unit of Work usage and read/write transaction choice.
- Map between DTOs and domain entities.
- Enforce use-case policies such as actor authorization, ownership checks, idempotency checks, and workflow order.
- Depend on interfaces/ports, not concrete infrastructure clients.

## Must Not

- Do not import FastAPI, `Request`, `Response`, `HTTPException`, route dependencies, or API response helpers.
- Do not import ORM models or SQLAlchemy sessions.
- Do not directly instantiate storage/LLM/Kafka/Redis/HTTP clients.
- Do not bury domain invariants in application code when they belong on an entity or domain service.

## Domain vs Application

- Domain owns invariants that must hold everywhere: state transitions, value validation, entity behavior, cross-entity business rules that do not need infrastructure.
- Application owns use-case sequencing: load entity, check actor, call domain behavior, persist, emit side effect, map DTO.

If a rule must also hold for gRPC, Celery, CLI, or future transports, it probably does not belong in `api/`.

## Ports

- External systems used by application services require a port under `backend/application/ports/`.
- Concrete implementations live under `backend/infrastructure/`.
- Tests should use fakes/in-memory implementations for ports when possible.

## Transactions

- Use `uow_factory(readonly=True)` for read-only queries.
- Use write UoW for create/update/delete and state transitions.
- Do not perform irreversible external side effects inside an uncommitted DB transaction unless the failure mode and compensation are explicit.

## DTOs

- Existing DTOs may live in `backend/application/dto.py`; task-driven module DTOs may also use `backend/application/dtos/` when the plan explicitly names that package or the repo has adopted it for the module.
- DTOs validate boundary shape and serialization. They should not become business-rule containers.

## Completion Check

- No FastAPI or ORM imports in application code.
- UoW boundary is explicit and minimal.
- Domain invariants are on domain objects/services.
- External dependencies are ports.
- Tests cover success and at least one failure/business-rule path.
