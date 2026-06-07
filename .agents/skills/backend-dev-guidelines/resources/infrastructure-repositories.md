# Infrastructure Repositories

Use this for ORM models, repository implementations, database setup, and Unit of Work implementation.

## Responsibilities

- Own SQLAlchemy models, queries, sessions, flush/refresh behavior, ORM/entity mapping, external adapters, and concrete client code.
- Implement domain repository interfaces and application ports.
- Keep database details hidden from `application` and `domain`.

## Must Not

- Do not import `api`.
- Do not return ORM models from repositories when the domain/application expects domain entities.
- Do not put business invariants only in repository code.
- Do not swallow database or external failures without structured logging and an intentional fallback.

## Repository Pattern

- Repository methods should speak in domain/application terms.
- Convert ORM models to domain entities at the boundary.
- Keep filters explicit and safe. Do not pass uncontrolled user field names into order/filter clauses.
- Use `select`, `func`, `selectinload`, `joinedload`, `with_for_update`, and indexes based on actual query needs.

## Unit of Work

- UoW opens/closes sessions and coordinates repositories.
- `readonly=True` must avoid unnecessary write transactions.
- Commit/rollback behavior belongs in UoW, not scattered across application services.

## Database Errors

- Map known `IntegrityError` cases to business/domain exceptions where appropriate.
- Unexpected DB failures should surface and be logged by global handlers or task wrappers.
- Be careful calling `rollback()` inside repository methods if the UoW owns transaction state. Prefer letting UoW roll back unless a local flush needs explicit handling.

## Completion Check

- Repository returns domain entities or DTO-ready domain objects, not ORM models, unless existing interface says otherwise.
- Query filters include ownership/tenant/status constraints when required by the use case.
- Model/migration/docs are updated together when schema changes.
- Tests cover mapping and important query filters.
