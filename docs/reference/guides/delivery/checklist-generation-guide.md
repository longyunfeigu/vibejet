# Checklist Generation Guide

**Date**: 2026-03-11
**Status**: Active Standard
**Used In**: `/feature-checklist` and `/bug-fix-checklist` skills

---

## Purpose

This guide defines how to generate a feature-specific checklist based on the feature type
determined in Step 1. The checklist must be generated **before coding starts**.

---

## Generation Principles

### 1. Start from the Type Template

Each feature type has a base template in `checklist-templates/`.
Start with the template for the classified type, then customize for the specific feature.

### 2. Make Items Specific, Not Generic

Bad: `[ ] Check for regressions`
Good: `[ ] Run existing tests for agent-flow/engine.py and confirm all pass`

Bad: `[ ] Verify API compatibility`
Good: `[ ] Confirm GET /api/sessions response still includes legacy field session_ref (deprecated but not removed)`

### 3. Tag Every Item

Every item must be tagged:
- `[AUTO]` — AI can verify this by running code, reading files, or static analysis
- `[HUMAN]` — requires human judgment, business knowledge, or browser/UI interaction

### 4. Group Items by Category

Standard categories (use all that are relevant):
- **Regression Risk** — will existing behavior break?
- **Data Compatibility** — schema, migration, backward compatibility
- **Cross-Module Impact** — other modules affected
- **Architecture Compliance** — follows project standards
- **Performance** — latency, memory, query count
- **Security** — input validation, auth, data exposure
- **UI/UX** — visual correctness (for frontend changes)
- **Deployment Safety** — can this be deployed without downtime?

---

## Generation by Feature Type

### T1: Presentation Layer

Focus areas: visual correctness, no unintended logic changes

Required categories: UI/UX, Regression Risk (minimal)

Typical checklist size: 3-6 items

Key generation questions:
- Does any changed component receive data from a parent? If so, check prop types unchanged.
- Are there snapshot tests? They need updating.
- Is the change responsive / does it affect multiple screen sizes?

---

### T2: Logic Extension

Focus areas: caller compatibility, test coverage, data handling

Required categories: Regression Risk, Data Compatibility, Cross-Module Impact, Architecture Compliance

Typical checklist size: 8-12 items

Key generation questions:
- List all callers of modified functions — do they need updates?
- If new parameters added, are they optional with safe defaults?
- Are new code paths covered by tests?
- Does this touch any shared schema? (If yes, add Data Compatibility items)

---

### T3: Conflicting Change

Focus areas: conflict resolution completeness, all assumption locations handled

Required categories: Regression Risk (deep), Data Compatibility, Cross-Module Impact, Deployment Safety

Typical checklist size: 12-18 items

Key generation questions (use the Conflict Map from Step 1):
- For each item in the Conflict Map: is it explicitly handled?
- Are there any tests that assert the OLD behavior that must now be updated?
- Is there a migration path for existing data that relied on old behavior?
- Do any external callers (API consumers) need to be notified?

**Mandatory item for T3**:
```
[HUMAN] Review Conflict Map — confirm every listed location has been addressed.
        Conflict Map: [paste or link the map from Step 1]
```

---

### T4: Architectural Change

Focus areas: ADR compliance, migration safety, rollback plan

Required categories: All categories apply. Add: **Migration Plan**, **Rollback Plan**

Typical checklist size: 20+ items

Key generation questions:
- Is the ADR approved before this checklist is used?
- What is the phased rollout plan? Is each phase independently deployable?
- What is the rollback procedure and has it been tested?
- Are all modules updated consistently, or is there a compatibility layer?
- Is there a data migration script, and has it been tested on a copy of production data?

**Mandatory items for T4**:
```
[HUMAN] Confirm ADR has been reviewed and approved by technical lead.
[HUMAN] Verify rollback procedure is documented and tested.
[HUMAN] Confirm phased deployment plan — this change is NOT a single-PR merge.
```

---

### T5: Cross-Cutting Change

Focus areas: completeness of coverage across all affected locations

Required categories: Regression Risk, Data Compatibility, Cross-Module Impact

Typical checklist size: 15-20 items (scales with number of locations)

Key generation questions (use the Complete Usage Map from Step 1):
- For each location in the Usage Map: is it updated?
- Are there any dynamically constructed references (e.g., string-based field access) that static analysis might miss?
- Are all tests that reference the changed element updated?

**Mandatory item for T5**:
```
[AUTO] Grep codebase for all references to [changed element] — confirm none remain unreplaced.
       Expected: 0 occurrences of old reference after change.
```

---

### T6: External Dependency Change

Focus areas: breaking changes from upstream, behavior parity, fallback

Required categories: Regression Risk, Performance, Deployment Safety, Security (for auth libs)

Typical checklist size: 10-15 items

Key generation questions:
- What does the changelog say? List all breaking changes explicitly.
- For each breaking change: is it handled in our code?
- Is there a way to test the new version in isolation before full rollout?
- If the external service is unavailable, does our fallback still work?

**Mandatory item for T6**:
```
[HUMAN] Read full changelog between old version and new version.
        Confirm each listed breaking change is explicitly addressed.
        Changelog URL: [insert URL]
```

---

## Checklist Output Format

The generated checklist must use this format, to be stored in the PR description or task notes:

```markdown
## Dev Checklist

**Feature**: [feature name]
**Type**: T3 (Conflicting Change)
**Generated**: 2026-03-11

### Regression Risk
- [AUTO] Run pytest tests/ and confirm all existing tests pass
- [AUTO] Run tests specifically for agent-flow/engine.py: pytest tests/test_engine.py
- [HUMAN] Review test_session_handling.py — 3 tests assert group_id is not None, update to handle nullable

### Data Compatibility
- [AUTO] Confirm Alembic migration exists for making group_id nullable
- [AUTO] Confirm migration includes default=None for existing rows
- [HUMAN] Verify migration is safe to run on live database without downtime

### Cross-Module Impact
- [AUTO] Grep for `.group_id` across codebase — confirm all usages handle None case
- [HUMAN] Manually test sip-integration transfer flow (cannot be auto-tested without SIP hardware)

### Conflict Map Resolution
- [HUMAN] Confirm agent-flow/engine.py:145 updated — was: `assert session.group_id`, now handles None
- [HUMAN] Confirm sip-integration/handlers.py:89 updated — routing logic handles missing group

### Architecture Compliance
- [AUTO] Confirm no print() statements added (grep for print()
- [AUTO] Confirm all new functions have type hints

### Deployment Safety
- [AUTO] Confirm migration has rollback (downgrade) defined
- [HUMAN] Confirm feature can be deployed without restarting all services simultaneously
```

---

## Related Documents

- [Feature Type Classification](./feature-type-classification.md)
- [Checklist Templates](./checklist-templates/)
- [Test Case Requirements](./test-case-requirements.md)
