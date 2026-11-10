# T4: Architectural Change — Checklist Template

**Feature**:
**Type**: T4 (Architectural Change)
**ADR Reference**: [link to ADR document — MUST exist before coding starts]
**Date**:

---

## Pre-Coding Gate (Must Be Complete Before Coding Begins)

- [ ] [HUMAN] Architecture Decision Record (ADR) is written and approved by technical lead
- [ ] [HUMAN] Phased rollout plan is defined — no single-PR delivery of full architecture change
- [ ] [HUMAN] Rollback procedure is documented
- [ ] [HUMAN] All affected team members have been informed

## Phase Delivery

- [ ] [HUMAN] This PR delivers exactly one defined phase (specify which phase: ___)
- [ ] [HUMAN] System is fully functional and deployable after this phase alone
- [ ] [AUTO] No partially implemented abstractions left in the codebase

## Migration

- [ ] [AUTO] Data migration script exists (if data model changes)
- [ ] [HUMAN] Migration tested on a realistic data copy
- [ ] [AUTO] Migration is reversible
- [ ] [HUMAN] Zero-downtime deployment confirmed or maintenance window scheduled

## Regression Risk

- [ ] [AUTO] All existing tests pass
- [ ] [HUMAN] End-to-end critical path tested manually (AI cannot cover this for architectural changes)
- [ ] [HUMAN] Performance benchmarks run — no degradation introduced

## Cross-Module Impact

- [ ] [HUMAN] Each affected module has been updated per the ADR spec
- [ ] [HUMAN] Compatibility layer (if any) works correctly for unconverted modules
- [ ] [AUTO] No module bypasses the new architectural boundary

## Rollback Verification

- [ ] [HUMAN] Rollback procedure has been executed in a staging environment
- [ ] [HUMAN] System is fully operational after rollback

## Architecture Compliance

- [ ] [AUTO] New structure follows layered architecture (AGENTS.md; `cd backend && uv run lint-imports`)
- [ ] [AUTO] No circular dependencies introduced
- [ ] [HUMAN] New abstractions are documented in relevant module docs
