# T3: Conflicting Change — Checklist Template

**Feature**:
**Type**: T3 (Conflicting Change)
**Conflict Map**: [paste or link from design document]
**Date**:

---

## Conflict Resolution (CRITICAL)

- [ ] [HUMAN] Every location in the Conflict Map has been explicitly reviewed and handled
- [ ] [HUMAN] Each handled location: confirm the fix is correct, not just syntactically valid
- [ ] [AUTO] No remaining code that asserts or assumes the old behavior (grep for old patterns)

## Regression Risk

- [ ] [AUTO] All existing tests pass: `pytest tests/`
- [ ] [HUMAN] Tests that previously tested old behavior: confirm they are updated correctly
         (updating a test to pass is not the same as updating it to test the right thing)
- [ ] [AUTO] New behavior has its own test coverage
- [ ] [HUMAN] Edge cases where old and new behavior diverge are explicitly tested

## Cross-Module Impact

- [ ] [HUMAN] Every module in the Impact Scope Report has been reviewed
- [ ] [AUTO] No cross-module integration tests fail
- [ ] [HUMAN] If external API consumers exist, confirm they are notified or handled

## Data Compatibility

- [ ] [AUTO] Alembic migration handles existing data correctly (not just schema)
- [ ] [HUMAN] Migration tested on a copy of realistic data, not just an empty database
- [ ] [AUTO] Rollback (downgrade) migration is defined and tested
- [ ] [HUMAN] Data that relied on old behavior — confirm it is migrated or explicitly deprecated

## Deployment Safety

- [ ] [HUMAN] Can this change be deployed without a full system restart?
- [ ] [HUMAN] If a partial deployment state exists (some services updated, others not),
         is the system safe in that intermediate state?
- [ ] [HUMAN] Is there a documented rollback plan if production issues occur post-deploy?

## Architecture Compliance

- [ ] [AUTO] No print() used
- [ ] [AUTO] All new functions have type hints
- [ ] [AUTO] Pydantic schemas updated where applicable
