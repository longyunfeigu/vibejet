# Backend Testing

Use this for `backend/tests/`, task-doc bare `tests/...` paths in a backend Unit, and backend verification planning.

## Test Strategy

- Domain tests: pure unit tests, no DB or FastAPI.
- Application tests: fake UoW, fake repositories, fake ports when behavior can be isolated.
- Repository tests: real SQLAlchemy session when query/mapping matters.
- API tests: `httpx.AsyncClient` plus FastAPI dependency overrides for auth/services.

## Minimum Coverage Per Change

- Success path.
- Expected business error path.
- One boundary/risk path when relevant: unauthorized, forbidden, invalid input, duplicate request, external failure, state transition, or migration/query behavior.

## Current Repo Defaults

- Tests live under `backend/tests/` as `test_*.py`.
- If a task document in a backend Unit says `tests/...`, interpret it as `backend/tests/...` unless the plan explicitly says otherwise.
- Use `pytest` and `pytest-asyncio`.
- Prefer existing fixtures from `backend/tests/conftest.py`.
- Use dependency overrides rather than changing production dependency factories for tests.

## What To Avoid

- Do not test implementation details when a behavior assertion is possible.
- Do not rely on test order or shared mutable global state.
- Do not call real external systems.
- Do not skip auth/permission tests for new protected endpoints.

## Verification Commands

Run from `backend/` unless the task has a narrower command:

```bash
uv run pytest tests/ -q
```

If `uv` is unavailable in the environment, use the repo's active virtualenv or `pytest tests/ -q` and report the fallback.

## Completion Check

- Tests are focused on the changed behavior.
- Failure paths use the same response envelope/business codes as production.
- External ports are faked or mocked.
- Any skipped test or unrun verification is reported.
