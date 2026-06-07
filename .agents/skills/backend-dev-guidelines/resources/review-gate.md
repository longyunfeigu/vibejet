# Review Gate

Use this before reporting backend work as done.

## Required Manual Gate

Read `docs/reference/guides/review-checklist-python-fastapi.md` and apply it to the diff.

Prioritize:

- DDD import boundary violations
- permission and ownership leaks
- transaction/side-effect consistency
- idempotency/concurrency races
- untrusted input/LLM/SDK validation
- unsafe persistence/query behavior
- API response contract drift
- missing tests for changed behavior

## Suggested Automated Checks

When feasible, run focused tests first, then broader tests:

```bash
cd backend
uv run pytest tests/ -q
```

For schema changes:

```bash
cd backend
alembic upgrade head
```

For future hardening, prefer adding automated checks for:

- `domain/` importing `api`, `application`, `infrastructure`, FastAPI, SQLAlchemy, Redis, Kafka, SDKs
- `application/` importing FastAPI, ORM models, SQLAlchemy sessions, concrete infrastructure clients
- `api/routes/` importing SQLAlchemy sessions, ORM models, repository implementations
- new business routes missing `response_model`
- new business routes not explicitly protected or public
- model changes without Alembic migration
- migration/model changes without `docs/project/data/` update when stable schema changes

## Completion Report

Report:

- what changed
- what verification ran
- what was not run and why
- any remaining risk or follow-up that affects correctness
