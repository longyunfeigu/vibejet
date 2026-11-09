# T2: Logic Extension — Checklist Template

**Feature**:
**Type**: T2 (Logic Extension, Non-Conflicting)
**Date**:

---

## Regression Risk

- [ ] [AUTO] All existing tests pass: `pytest tests/`
- [ ] [AUTO] Tests specific to modified files pass
- [ ] [AUTO] New code paths have test coverage
- [ ] [HUMAN] Existing tests verify the right behavior (not just passing trivially)

## Cross-Module Impact

- [ ] [AUTO] List all callers of modified functions — confirm none break with new signature
- [ ] [AUTO] If new optional parameters added, default values are safe for existing callers
- [ ] [HUMAN] Confirm no other module depends on a side effect of the old implementation

## Data Compatibility

- [ ] [AUTO] If schema changed, Alembic migration exists and is correct
- [ ] [AUTO] New fields have appropriate defaults (not null without default)
- [ ] [AUTO] API response schema changes are backward compatible (no removed fields)

## Architecture Compliance

- [ ] [AUTO] No print() used — logger used throughout
- [ ] [AUTO] All new functions have type hints
- [ ] [AUTO] Pydantic schemas used for new request/response structures
- [ ] [AUTO] Dependency direction follows layered architecture (AGENTS.md; `cd backend && uv run lint-imports`)

## Performance

- [ ] [AUTO] No N+1 query patterns introduced (check ORM usage)
- [ ] [HUMAN] No new synchronous blocking calls in async paths
