# Test Case and Checklist Requirements

**Date**: 2026-04-11
**Status**: Active Standard
**Applies To**: All developers and AI assistants generating test cases for T1–T6 tasks

---

## Purpose

This document defines what test cases and verification checks are required for each
task level. The goal is proportionate verification: lightweight tasks should not be
over-tested, and complex tasks must not skip critical coverage.

---

## Test Requirement Overview

| Level | Test Depth | Who Executes | Gate Condition |
|-------|-----------|-------------|----------------|
| T1 (Presentation only) | Manual UI check | Human | Visual confirm passes |
| T2 (Logic extension) | Happy path + regression | AI (AUTO) + Human (HUMAN) | All pass |
| T3 (Conflicting change) | Happy path + bad cases + edge cases | AI + Human | All pass, conflict map resolved |
| T4 (Architectural change) | Full suite + migration + rollback | AI + Human + Tech Lead | Full pass, rollback verified |
| T5 (Cross-cutting change) | Full coverage per location + integration | AI + Human | All locations verified |
| T6 (External dependency) | Behavior parity + breaking change verification | AI + Human | Parity confirmed, changelog addressed |

---

## T1: Presentation Only

**Principle**: No logic changed, so no logic needs testing. Human eyes are the test.

**Required checks**:

```
[HUMAN] Visual render check
- Component renders correctly in target context (modal, table, page, etc.)
- No layout breakage at standard viewport sizes (1280px, 1920px)
- Text is readable — no truncation, overflow, or collision
- Interactive elements (if any) are correctly positioned and accessible

[HUMAN] Regression guard
- Confirm no business logic files were touched (grep for unexpected changes)
- Confirm no API calls were added or removed
```

**NOT required**: Unit tests, integration tests, backend tests.

**Common failure mode**: Developer assumes change is T1 but it also touched a state
variable or API call. Run Step 0 before confirming T1 classification.

---

## T2: Logic Extension

**Principle**: The change is backward-compatible, so existing behavior must still work.
Focus on verifying the new behavior and confirming nothing regressed.

**Required checks**:

```
Happy Path
[AUTO] Run existing test suite for modified files — all must pass
[AUTO] Test the new behavior with valid inputs — confirm expected output
[HUMAN] Manually test the primary user-facing flow affected by this change

Regression
[AUTO] Run full test suite for the affected module
[AUTO] Confirm callers of modified functions pass the same inputs as before and get the same outputs
[HUMAN] Review any test that was changed — confirm the change reflects new expected behavior,
        not a relaxed requirement

Backward Compatibility
[AUTO] If parameters were added: confirm they are optional with safe defaults
[AUTO] If API response was extended: confirm old fields are still present
[HUMAN] If there is a known integration partner (frontend, another service): manually verify
        the integration still works end-to-end
```

**Minimum test case set**:

| Test Case | Type | Executor |
|-----------|------|---------|
| New behavior with typical valid input | Happy path | AUTO |
| New behavior with boundary valid input | Edge | AUTO or HUMAN |
| Old callers still work without changes | Regression | AUTO |
| API consumers still receive expected fields | Compat | AUTO |

---

## T3: Conflicting Change

**Principle**: Something that was always true is no longer true. Every location that
depended on the old assumption must be explicitly tested with both old-style and new-style
inputs.

**Required checks**:

```
Happy Path
[AUTO] New behavior with standard inputs — confirm expected result
[HUMAN] End-to-end test of the primary flow under new behavior

Bad Cases (inputs that would have worked before but now follow a different path)
[HUMAN] Test with inputs that previously relied on the old assumption
[HUMAN] Test with inputs that are now explicitly invalid or handled differently

Edge Cases
[HUMAN] Null, empty, or boundary values for any field whose handling changed
[HUMAN] Concurrent or race condition scenarios if the change affects shared state
[AUTO] Test any new error paths introduced by the conflict resolution

Conflict Map Verification
[HUMAN] For each item in the Conflict Map (from Technical Design):
        - Test the specific code path at that location
        - Confirm it handles both old-style and new-style data correctly

Regression
[AUTO] Full test suite for all affected modules
[HUMAN] Manually review tests that were updated — confirm they reflect intent,
        not just "make the test pass"
```

**Minimum test case set**:

| Test Case | Type | Executor |
|-----------|------|---------|
| New behavior — standard input | Happy path | AUTO |
| Inputs that previously relied on old assumption | Bad case | HUMAN |
| Null/missing value for changed field | Edge case | AUTO or HUMAN |
| Each Conflict Map location — both data states | Regression | HUMAN |
| Any new error path | Error path | AUTO |

---

## T4: Architectural Change

**Principle**: Core abstractions are changing. Every layer of the system must be verified.
Testing must be phased to match the delivery phases in the Technical Design.

**Required checks**:

```
Per Phase
[HUMAN] Each deployment phase must be independently tested before the next phase begins
[AUTO] Automated smoke test after each phase deployment
[HUMAN] Phase-specific manual verification per phase test plan

Full Test Suite
[AUTO] Complete test suite run after all phases complete
[AUTO] Performance benchmarks — confirm no regression vs pre-change baseline
[HUMAN] Load or stress test for changes that affect throughput or concurrency

Migration Testing
[HUMAN] Migration script run on a copy of production data — confirm no data loss or corruption
[AUTO] Post-migration data integrity checks (row counts, field values, foreign key integrity)
[HUMAN] Confirm migrated data produces correct behavior with new code

Rollback Testing
[HUMAN] Execute rollback procedure in staging — confirm system recovers cleanly
[HUMAN] Test that data written under new code is handled gracefully if rollback is needed

Integration Testing
[HUMAN] End-to-end flow covering all modules affected by the architectural change
[HUMAN] Test interaction with external systems (SIP, LLM providers, etc.) post-change

Cross-Feature Interaction (see also Cross-Feature section below)
[HUMAN] Identify 2-3 features that are most likely to interact with the changed architecture
[HUMAN] Manually run those features' primary flows and confirm no unexpected behavior
```

**Minimum test case set**:

| Test Case | Type | Executor |
|-----------|------|---------|
| End-to-end primary flow — all phases complete | Integration | HUMAN |
| Performance benchmark | Performance | AUTO |
| Migration on production data copy | Migration | HUMAN |
| Rollback procedure in staging | Rollback | HUMAN |
| Adjacent feature flows (top 2-3) | Cross-feature | HUMAN |
| Error recovery — what happens if phase N-1 data is encountered by phase N code | Compatibility | HUMAN |

---

## T5: Cross-Cutting Change

**Principle**: The risk is incompleteness — one missed location causes a runtime failure.
Every location in the Usage Map must be tested individually, not just assumed correct.

**Required checks**:

```
Per-Location Verification
[AUTO] Grep confirms zero remaining occurrences of old reference
[AUTO] For each updated location: unit test or integration test that exercises that specific path
[HUMAN] Spot-check 3-5 locations manually — confirm the change is semantically correct,
        not just syntactically applied

Integration
[AUTO] Full test suite for each affected module
[HUMAN] End-to-end test that exercises multiple locations in the same flow

Consistency
[AUTO] Confirm all occurrences are updated consistently (no mixed old/new state)
[HUMAN] Review any location where the change was non-trivial (required judgment, not just find-replace)
```

**Minimum test case set**:

| Test Case | Type | Executor |
|-----------|------|---------|
| Zero old references remaining (grep) | Completeness | AUTO |
| Unit test per changed location (sample or full) | Correctness | AUTO |
| Multi-location flow — exercises N updated locations in sequence | Integration | HUMAN |
| Spot-check of 3-5 non-trivial locations | Manual review | HUMAN |

---

## T6: External Dependency Change

**Principle**: Behavior parity with the previous version is the primary goal. Every
breaking change in the changelog must have a corresponding test.

**Required checks**:

```
Behavior Parity
[AUTO] Run existing test suite — all must pass with new dependency
[HUMAN] Manually test the primary flows that use the changed dependency
[HUMAN] Confirm that responses/outputs from the new version match expected format

Breaking Change Coverage
[HUMAN] For each breaking change listed in the Technical Design's Breaking Change Analysis:
        test the specific affected code path explicitly

Fallback and Error Handling
[HUMAN] Test behavior when the external dependency is unavailable or returns an error
[AUTO] Confirm existing fallback logic still triggers correctly with the new version

Performance and Compatibility
[AUTO] Latency benchmark for calls to the external dependency — compare before/after
[HUMAN] Test in staging with production-equivalent load before promoting to production
```

**Minimum test case set**:

| Test Case | Type | Executor |
|-----------|------|---------|
| Existing test suite — full pass | Regression | AUTO |
| Primary flow using the dependency | Happy path | HUMAN |
| Each breaking change from changelog | Breaking change | HUMAN |
| Unavailability / error response | Fallback | HUMAN |
| Latency benchmark | Performance | AUTO |

---

## Data Change Testing (Applies to Any Level)

When a change involves data mutations — schema changes, migrations, or changes to how
data is written or read — the following additional checks are required regardless of
the T-level classification:

```
Pre-Migration
[HUMAN] Migration script reviewed by a second developer
[AUTO] Migration script run against a schema snapshot in CI — confirms it applies cleanly
[HUMAN] Migration run on a copy of production data — confirm no errors, no data loss

Post-Migration Data Integrity
[AUTO] Row count before and after migration matches expectations
[AUTO] Spot-check of migrated field values confirms correct transformation
[AUTO] Foreign key integrity check passes
[HUMAN] Application behavior with migrated data manually verified

Rollback
[AUTO] Downgrade migration (if applicable) runs without error
[HUMAN] Data state after rollback is consistent and usable

Zero-Downtime
[HUMAN] If deployment must be zero-downtime:
        - Old code can read new schema (during rolling deploy)
        - New code can read old schema (in case of rollback)
        Both directions verified explicitly
```

---

## Cross-Feature Interaction Testing

Cross-feature interaction testing is required in the following situations:

| Situation | Required Action |
|-----------|----------------|
| T4 (architectural change) | Always required |
| T3 (conflicting change) | If the conflict affects shared data structures or APIs |
| T5 (cross-cutting change) | If the changed element is used in more than one user-facing feature |
| Any level, if Analogical Investigation found related issues | Required for affected features |

**How to conduct cross-feature interaction testing**:

```
1. Identify features most likely to interact with the changed area
   - Features that share data structures changed in this PR
   - Features that call the same APIs or services
   - Features that run in the same session or concurrently

2. For each identified feature, run its primary happy path manually
   - Confirm it produces correct output
   - Confirm it does not exhibit unexpected behavior changes

3. For the highest-risk feature, also run its bad cases and edge cases

4. Document results:
   | Feature | Interaction Type | Tested | Result |
   |---------|-----------------|--------|--------|
   | [feature] | Shared data | YES | Pass |
   | [feature] | Same API | YES | Pass |
   | [feature] | Concurrent session | NO | Tracked as follow-up |
```

---

## Checklist Verification Standard

All test results must be recorded explicitly. The following format is required:

```
### Test Execution Results

| Test Case | Expected | Actual | Result | Notes |
|-----------|---------|--------|--------|-------|
| [test case name] | [expected] | [actual] | PASS / FAIL | [notes if any] |
```

**Rules**:
- No test may be recorded as PASS without actual execution
- FAIL results must be resolved before the gate — or documented with an explicit
  decision to defer (with tech lead acknowledgement for T3+)
- SKIP requires a written justification — "out of scope" is not sufficient

---

## Related Documents

- [Dev Process and Bug Fix Standards](./dev-process-and-bug-fix.md)
- [Technical Design Spec](./technical-design-spec.md)
- [Feature Type Classification](./feature-type-classification.md)
- [Checklist Generation Guide](./checklist-generation-guide.md)
- [Checklist Execution Guide](./checklist-execution-guide.md)
- [Gate Review Criteria](./checklist-gate-review.md)
