# Feature Type Classification Guide

**Date**: 2026-03-11
**Status**: Active Standard
**Used In**: `/feature-design` and `/bug-fix-design` skills

---

## Purpose

Correctly classifying a feature type before development determines the depth of exploration,
the checklist used, and the level of human involvement required.

**Misclassification is a common failure mode.** A feature that looks like T1 may be T3.
Always complete Step 0 (codebase exploration) before classifying.

---

## Exploration (Required Before Classification)

Before classifying, scan the codebase and answer these questions:

```
Exploration Questions:
1. Which files will likely change?
2. Which modules are affected (reference CLAUDE.md module map)?
3. Are any shared interfaces, schemas, or contracts involved?
4. Does this touch any critical path (llm-proxy, agent-flow core, session handling)?
5. Are there other features that depend on the behavior being changed?
6. Are any external dependencies (third-party libs, APIs) involved?
```

Output a brief **Impact Scope Report** before proceeding to classification.

---

## Type Definitions

### T1: Presentation Layer Change

**Definition**: Changes only affect how data is displayed. No logic, interaction flow,
data structure, or API contract is modified.

**Indicators**:
- Only `.css`, `.scss`, template strings, or display-only component props change
- No state structure changes
- No API changes
- No business logic files touched

**Examples**:
- Changing table column widths or order
- Updating color themes or font sizes
- Reformatting date display strings
- Changing button labels (not behavior)

**Common Misclassification**: A "display" change that actually modifies how data is fetched
or filtered is T2, not T1. Check whether the change reaches any service or API layer.

---

### T2: Logic Extension (Non-Conflicting)

**Definition**: Modifies or extends existing business logic. The new behavior is additive
or a direct replacement that does not contradict existing assumptions elsewhere.

**Indicators**:
- Business logic files change
- Existing callers of changed functions can still work without modification
- New behavior is a superset of old behavior, or a clear replacement with no side effects

**Examples**:
- Adding an optional parameter to an existing API endpoint
- Extending a validation rule
- Optimizing a database query (same inputs/outputs)
- Adding a new field to a response schema (backward compatible)

**Common Misclassification**: If callers of the changed function assume old behavior,
this becomes T3. Run Step 0 to check all callers.

---

### T3: Conflicting Change

**Definition**: The new feature contains requirements that directly contradict or break
assumptions made by existing features.

**Indicators**:
- Removing or making optional something that was previously required
- Changing a data structure that other modules treat as having a specific shape
- A business rule that was always true is now conditionally false
- Other features' tests would fail if they tested the old behavior

**Examples**:
- "Group creation" was mandatory; now it is optional or removed
- A session field that was always populated may now be null
- A status enum gains a new value that existing switch statements don't handle

**Detection Method**:
After Step 0, ask: "Does any existing code path **assume** the old behavior will always be true?"
If yes, this is T3.

**Required Extra Step**: Before generating the checklist, produce a **Conflict Map**:
list every location in the codebase that assumes the old behavior, and confirm
each location is handled.

---

### T4: Architectural Change

**Definition**: Changes the fundamental structure, data flow, or design assumptions of
a subsystem. Cannot be delivered incrementally in a single PR without planning.

**Indicators**:
- A core abstraction is being replaced or significantly extended
- The change affects multiple layers of the architecture simultaneously
- Requires a migration plan for existing data or state
- The PR would be unsafe to roll back without a dedicated rollback procedure

**Examples**:
- Moving from single-agent to multi-agent orchestration
- Replacing synchronous call handling with async/event-driven
- Introducing a new central service that all modules must call
- Changing authentication model across the system

**Required Extra Step**: Produce an **Architecture Decision Record (ADR)** before any coding.
The ADR must be reviewed and approved by the technical lead. Coding starts only after ADR approval.

---

### T5: Cross-Cutting Change

**Definition**: A change that is individually small at each location but must be applied
consistently across many modules or features. The risk is incompleteness, not depth.

**Indicators**:
- A shared data structure, constant, or utility is modified
- Every module that uses this shared element must be updated
- Missing even one location causes a runtime error or inconsistency

**Examples**:
- Renaming a field in a core Pydantic schema used by 8 endpoints
- Changing the format of a shared session/context object
- Updating a shared enum that is referenced across multiple services
- Modifying a common logging format that all modules use

**Required Extra Step**: Step 0 must produce a **Complete Usage Map** — every file that
imports or references the changed element. The checklist must cover each location.

---

### T6: External Dependency Change

**Definition**: Changes involve upgrading, replacing, or modifying integration with a
third-party library or external service.

**Indicators**:
- `requirements.txt`, `package.json`, or lock files change
- A third-party API contract is updated
- A provider is being swapped (e.g., different STT vendor)

**Examples**:
- Upgrading LiteLLM to a new major version
- Switching from one TTS provider to another
- Updating the LiveKit SDK

**Required Extra Step**: Before coding, review the **changelog/release notes** for breaking changes.
The checklist must include explicit verification against the breaking changes list.

---

## Classification Decision Tree

```
START: Read the feature requirement + Step 0 Impact Report
          │
          ▼
Does it only change display/styling with no logic/data impact?
  YES → T1
  NO  ↓
          │
Is any external library/provider being changed or upgraded?
  YES → T6 (may also be T4 if architectural)
  NO  ↓
          │
Does it change a fundamental architectural abstraction or data flow?
  YES → T4
  NO  ↓
          │
Does it change a shared element used across many modules?
  YES → T5 (may also be T3 if conflicting)
  NO  ↓
          │
Does the new behavior contradict or break any existing assumptions?
  YES → T3
  NO  ↓
          │
T2 (logic extension, non-conflicting)
```

---

## Mixed Types

A feature may span multiple types. In that case:

1. List all applicable types (e.g., "T3 + T5")
2. Apply the checklist of the **highest-risk type** as the base
3. Add specific items from other applicable types
4. Use the **highest** human involvement level

**Example**: "Rename the `session_id` field across all modules and remove the old alias"
→ T5 (cross-cutting rename) + T3 (removing old alias breaks callers)
→ Use T3 checklist as base + T5 complete usage map requirement

---

## Classification Output Format

Output after completing classification:

```
## Feature Classification

**Type**: T3 (Conflicting Change)
**Secondary**: T5 (Cross-cutting Change)

**Reason**: The requirement removes the mandatory `group_id` field from session objects.
Multiple modules (agent-flow, sip-integration) assume this field is always present.

**Impact Scope** (from Step 0):
- Files affected: 12
- Modules affected: agent-flow, sip-integration, voice-agent
- Critical paths touched: YES (session handling in agent-flow/engine.py)
- External dependencies: NO

**Conflict Map**:
- agent-flow/engine.py:145 - assumes session.group_id is not None
- sip-integration/handlers.py:89 - uses session.group_id for routing
- [... complete list ...]

**Recommended Checklist Template**: T3 + T5 combined
```
