# Technical Design Specification Standard

**Date**: 2026-04-11
**Status**: Active Standard
**Applies To**: All developers producing technical designs for T2 and above tasks

---

## Purpose

A Technical Design is a written record of what we are changing, why, how, and what
risks we are taking. It forces explicit thinking before implementation and provides a
reference for code review, incident investigation, and future development.

---

## When Is a Technical Design Required?

| Level | Design Required? | Approval Required? |
|-------|-----------------|-------------------|
| T1 (Presentation only) | No | No |
| T2 (Logic extension) | Yes — lightweight | Self-reviewed |
| T3 (Conflicting change) | Yes — standard | Self-reviewed + peer acknowledgement |
| T4 (Architectural change) | Yes — full | Tech lead approval before coding |
| T5 (Cross-cutting change) | Yes — standard | Self-reviewed |
| T6 (External dependency) | Yes — lightweight | Self-reviewed |

**For T4**: No code may be written until the design document is approved by the tech lead.

---

## Universal Design Sections (All Levels T2 and Above)

Every Technical Design must include the following sections, scaled to the appropriate depth:

### 1. Background and Motivation

```
- What is the current behavior or state?
- What is the problem or gap being addressed?
- Why is this change needed now?
- Link to the bug report, task, or PRD that triggered this work.
```

### 2. Proposed Change

```
- What will be changed? (precise description, not vague)
- What will NOT be changed? (scope boundary)
- What is the new behavior after this change?
```

### 3. Root Cause (for bug fixes only)

```
- What is the exact root cause?
- Why did the original implementation have this flaw?
- Why was it not caught earlier?
```

### 4. Impact Scope

```
- Files that will change
- Modules affected
- APIs or contracts that change
- Data structures or schemas that change
- Critical paths touched
```

### 5. Side Effects and Risks

```
- What existing behavior could this break?
- Are there callers that depend on the current (possibly incorrect) behavior?
- Does this require a data migration?
- Is this change reversible? What is the rollback procedure?
- What is the blast radius if this goes wrong in production?
```

### 6. Analogical Investigation

```
- What pattern does this change address?
- Were similar locations checked?
- Results and any follow-up tasks created.
(Required even if no similar issues were found — document that you checked.)
```

---

## Supplementary Analysis: Field Addition Compatibility

**When required**: Any time the change adds a new field to a shared schema, configuration
model, stored document (e.g., Redis hash, JSON blob, database row), or API contract.
Applies to T2 and above; T1 is exempt.

**Trigger**: Step 1 (Impact Scope) or Step 3 (Proposed Change) identifies that one or
more new fields are being added to a shared data structure.

**AI responsibility**: For each question below, state a concrete recommendation first,
then present it to the user for confirmation. "TBD" is not an acceptable answer.

Repeat this block once per new field:

```
### Field: [field name]

Type: [type]  |  Location: [schema / model / config path]

#### Q0 — Default Value (No User Configuration)

Recommendation: default = [concrete value]
Reason: [why this preserves existing behavior / is safe for new records]

#### Q1 — Data Migration for Existing Records

Existing records affected: YES / NO

If YES:
  Backfill value: [concrete value]
  Why: [this value should restore the behavior that existed before this field was added]
  Migration approach: [Alembic column default / Alembic data migration script /
                       lazy upgrade on first read / other]

If NO:
  Why migration is safe to skip: [reason — e.g., None/absent is handled gracefully
  at runtime; field is purely additive with no behavioral impact]

#### Q2 — Missing Field Handling at Runtime (applies when Q1 = NO)

Runtime behavior when field is absent from an existing record: [describe — must be safe]

Frontend write-back required:
  Does the frontend display and allow editing of this field? YES / NO

  If YES (recommended): write the default value into form state on load for records
  that are missing this field, so the next user save automatically persists the new
  data structure. Confirm the write-back value: [value]

  If NO: field is backend-only; no frontend action required.
```

---

## Level-Specific Requirements

### T2: Logic Extension — Lightweight Design

**Goal**: Confirm the change is backward-compatible and callers are safe.

**Required sections**: Background, Proposed Change, Impact Scope, Side Effects and Risks

**Key questions to answer**:
- List all callers of modified functions. Are they still compatible?
- If adding parameters, are they optional with safe defaults?
- Are new code paths covered by existing or new tests?
- Does this touch any shared schema? If yes, is backward compatibility maintained?

**Format**: May be written inline in the PR description. Does not require a separate file
unless the change is complex.

**Design must answer**:
```
[ ] All callers of modified functions listed — none require changes OR all are updated
[ ] New parameters are optional with safe defaults
[ ] Backward compatibility explicitly confirmed
[ ] New code paths identified and test plan noted
```

---

### T3: Conflicting Change — Standard Design

**Goal**: Map every location that assumes the old behavior and confirm each is handled.

**Required sections**: All universal sections + Conflict Map

**Additional section: Conflict Map**

```
## Conflict Map

Old assumption: [what was always true before this change]
New behavior: [what is now true or conditionally true]

Locations that assume old behavior:
| File | Line | Assumption | Resolution |
|------|------|-----------|------------|
| agent-flow/engine.py | 145 | group_id is always set | Updated to handle None |
| sip-integration/handlers.py | 89 | group_id used for routing | Routing now falls back to default |
| [file] | [line] | [assumption] | [resolution] |

Callers that need notification (external API consumers): YES / NO
If YES: [list them and the notification plan]
```

**Key questions to answer**:
- For each item in the Conflict Map: is it explicitly handled?
- Are there tests that assert the old behavior that must be updated?
- Is there a migration path for existing data that relied on old behavior?
- Do any external API consumers need to be notified?

**Design must answer**:
```
[ ] Conflict Map is complete — no location left unaddressed
[ ] All tests asserting old behavior have been updated or removed
[ ] Data migration plan stated (or confirmed not needed)
[ ] External consumer notification plan (or confirmed not needed)
```

---

### T4: Architectural Change — Full Design

**Goal**: Provide a complete plan that can be reviewed, approved, and phased.

**Required sections**: All universal sections + Architecture Decision Record + Migration Plan + Rollback Plan

**This design MUST be approved by the tech lead before any code is written.**

**Additional section: Architecture Decision Record (ADR)**

```
## Architecture Decision Record

### Context
[Why is this architectural change necessary? What constraints are we working within?]

### Decision
[What architectural approach are we taking?]

### Alternatives Considered
| Option | Pros | Cons | Rejected Because |
|--------|------|------|-----------------|
| [option A] | ... | ... | ... |
| [option B] | ... | ... | ... |

### Consequences
- Positive: [what improves]
- Negative: [what gets worse or more complex]
- Neutral: [what changes but neither improves nor worsens]
```

**Additional section: Migration Plan**

```
## Migration Plan

### Phase Breakdown
| Phase | What Happens | Safe to Deploy? | Rollback Possible? |
|-------|-------------|-----------------|-------------------|
| Phase 1 | [description] | YES | YES |
| Phase 2 | [description] | YES | YES (with script) |
| Phase 3 | [description] | YES | NO — point of no return |

### Data Migration
- Script location: [path or "N/A"]
- Tested on: [staging / production copy / not yet]
- Estimated duration: [time estimate]
- Zero-downtime: YES / NO

### Rollback Procedure
[Exact steps to roll back. Must be tested, not theoretical.]
```

**Design must answer**:
```
[ ] ADR documents all alternatives considered
[ ] Tech lead approval recorded (name + date)
[ ] Each phase is independently deployable
[ ] Data migration script exists and has been tested
[ ] Rollback procedure is documented and tested
[ ] All modules updated consistently OR compatibility layer is in place
```

---

### T5: Cross-Cutting Change — Standard Design

**Goal**: Produce a complete usage map so that no location is missed.

**Required sections**: All universal sections + Complete Usage Map

**Additional section: Complete Usage Map**

```
## Complete Usage Map

Changed element: [name of field / constant / function / schema]

All locations that reference this element:
| File | Line | Usage Type | Updated? |
|------|------|-----------|---------|
| [file] | [line] | import | YES |
| [file] | [line] | type annotation | YES |
| [file] | [line] | dynamic string reference | YES |
| [file] | [line] | test assertion | YES |

Dynamic references (string-based, template-based — may not be caught by grep):
- [list any known dynamic references]

Total locations: [N]
Updated in this PR: [N]
```

**Key questions to answer**:
- Are there any dynamically constructed references (string interpolation, getattr, etc.)
  that a grep would miss?
- Are all tests that reference the changed element updated?
- Is there any external documentation that references the old name?

**Design must answer**:
```
[ ] Complete Usage Map covers all grep results
[ ] Dynamic references explicitly checked
[ ] All tests referencing changed element updated
[ ] Zero occurrences of old reference remain after change (auto-verified)
```

---

### T6: External Dependency Change — Lightweight Design

**Goal**: Document all breaking changes from the upstream and confirm each is handled.

**Required sections**: All universal sections + Breaking Change Analysis

**Additional section: Breaking Change Analysis**

```
## Breaking Change Analysis

Dependency: [name]
Old version: [X.X.X]
New version: [Y.Y.Y]
Changelog URL: [URL]

Breaking changes from changelog:
| Breaking Change | Affects Us? | Our Handling |
|----------------|------------|-------------|
| [breaking change 1] | YES | [how we handle it] |
| [breaking change 2] | NO | Not used in our codebase |
| [breaking change 3] | YES | [how we handle it] |

Behavioral changes (non-breaking but behavior differs):
| Change | Affected Behavior | Verified? |
|--------|------------------|---------|
| [behavior change] | [what we need to check] | YES/NO |
```

**Key questions to answer**:
- What does the full changelog say between old and new versions?
- For each breaking change: is it handled?
- Is there a way to test the new version in isolation before full rollout?
- If the external service is unavailable, does our fallback still work?

**Design must answer**:
```
[ ] Full changelog reviewed (not just the summary)
[ ] Every breaking change either handled or confirmed not applicable
[ ] Behavioral changes verified in staging
[ ] Fallback behavior confirmed
[ ] Rollback procedure (how to revert to old version if needed)
```

---

## Design Storage Location

All design documents are stored in `RD/docs/delivery/`:

| Work type | File path |
|-----------|----------|
| Feature design | `RD/docs/delivery/[YYYY-MM-DD]-feature-[slug]-design.md` |
| Bug fix design | `RD/docs/delivery/[YYYY-MM-DD]-bugfix-[slug]-design.md` |

T4 Architecture Decision Records are additionally cross-filed in:
`RD/docs/architecture/adr/adr-[NNN]-[topic].md`

Both the design doc and checklist report must be linked in the PR description.

---

## Design Review Checklist

Before submitting a design for review (or before proceeding with self-review):

```
[ ] Background clearly explains the "why"
[ ] Proposed change is precise — not vague
[ ] All affected files and modules listed
[ ] Side effects explicitly enumerated (not just "no side effects")
[ ] Analogical Investigation completed
[ ] Level-specific sections completed (Conflict Map / Usage Map / ADR / Breaking Change Analysis)
[ ] Rollback or recovery approach stated
```

---

## Related Documents

- [Dev Process and Bug Fix Standards](./dev-process-and-bug-fix.md)
- [Feature Type Classification](./feature-type-classification.md)
- [Test Case Requirements](./test-case-requirements.md)
- [Checklist Generation Guide](./checklist-generation-guide.md)
