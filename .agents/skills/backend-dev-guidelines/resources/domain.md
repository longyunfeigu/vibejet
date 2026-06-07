# Domain Layer

Use this for `backend/domain/`.

## Responsibilities

- Entities, value objects, aggregate behavior, domain services, domain exceptions, repository interfaces.
- Business invariants that must hold independent of HTTP, database, queues, SDKs, or UI.
- Pure Python behavior that can be unit tested without application bootstrapping.

## Must Not

- Do not import FastAPI, SQLAlchemy, Redis, Kafka, Celery, storage SDKs, LLM SDKs, HTTP clients, `api`, `application`, or `infrastructure`.
- Do not return DTOs or API response envelopes.
- Do not depend on current request, headers, environment, or framework dependency injection.
- Do not perform I/O.

## Exceptions

- Use `DomainValidationException` for invalid entity/value-object state.
- Use module-specific `BusinessException` subclasses for expected business failures with stable business codes.
- Include `field`, `details`, `message_key`, and `format_params` when they help API clients and i18n.

## Entity Design

- Put state transitions on the entity when the entity owns the state.
- Validate allowed status/role/type values in `__post_init__` or value-object construction.
- Keep time handling explicit and UTC-aware when timestamps are part of entity behavior.
- Avoid anemic entities when the rule clearly belongs to the domain.

## Repository Interfaces

- Define repository interfaces in the domain when the domain/application depends on persistence behavior.
- Interfaces expose domain entities, not ORM models.
- Infrastructure implements these interfaces and handles mapping.

## Completion Check

- Import boundary is pure.
- New invariants have focused unit tests.
- Repository interfaces do not leak ORM/query details.
- Exceptions map to existing business code conventions.
