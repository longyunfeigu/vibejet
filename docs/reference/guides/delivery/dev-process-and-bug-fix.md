# Development Process and Bug Fix Standards

**Date**: 2026-04-11
**Status**: Active Standard
**Applies To**: All developers and AI assistants working on features or bug fixes

---

## Purpose

This document defines the mandatory steps for all development work — both feature delivery
and bug fixing. It ensures that every change is understood before it is made, its side
effects are explicitly considered, and similar problems elsewhere are proactively identified.

---

## Part 1: Feature Development Process

Feature development follows the 6-step AI-Era workflow. This section clarifies the
non-negotiable gates within that workflow.

### Step 0: Explore

Before writing a single line of code, AI must scan the codebase and produce an
**Impact Scope Report**:

```
- Files likely to change
- Modules affected (reference CLAUDE.md module map)
- Shared interfaces, schemas, or contracts touched
- Critical paths involved (llm-proxy, agent-flow core, session handling)
- Features that depend on the behavior being changed
- External dependencies involved
```

**Rule**: No coding without a completed Impact Scope Report. The human must review and
confirm the scope before proceeding.

### Step 1: Classify

Assign the feature type T1–T6. See [feature-type-classification.md](./feature-type-classification.md).

**Rule**: If classification changes scope (e.g., what appeared to be T1 is actually T3),
restart Step 0 with the updated understanding.

### Step 2: Technical Design

For T2 and above, a Technical Design must be produced before coding.
See [technical-design-spec.md](./technical-design-spec.md) for templates and requirements.

**Rule**: T4 designs require tech lead approval before Step 3 begins. T2/T3/T5/T6 designs
may proceed after self-review but must be recorded in the PR or task notes.

### Step 3: Code

AI implements the feature guided by the checklist from Step 2. The checklist is a
constraint on implementation decisions, not just a post-hoc verification tool.

### Step 4: Execute Checklist

AI runs all `[AUTO]` checklist items and flags all `[HUMAN]` items with context.

### Step 5: Human Review

Developer verifies AI results and executes all `[HUMAN]` items personally.

**Rule**: No item may remain unresolved at the gate. Every item must be PASS or
explicitly documented N/A with a justification.

### Step 6: Retrospective

After merge, review checklist effectiveness. Add items for any bugs that the checklist
failed to catch. This is how the quality standard improves over time.

---

## Part 2: Bug Fix Process

Bug fixes follow the same 6-step workflow, but with additional mandatory analysis before
any code is written.

### Bug Fix Mandatory Pre-Steps

Before Step 0 of the standard workflow, a bug fix requires:

#### Pre-Step A: Root Cause Analysis

Answer these questions in writing before touching the code:

```
1. What is the exact symptom? (observable behavior)
2. What is the root cause? (why it happened — trace to the origin, not the surface)
3. Why was this not caught earlier?
   - Missing test coverage?
   - Wrong assumption in the original design?
   - Environmental/data condition not anticipated?
4. Is this a symptom of a deeper pattern, or an isolated mistake?
```

**Rule**: The fix targets the root cause, not the symptom. If the root cause cannot be
clearly stated, continue investigation before writing code.

#### Pre-Step B: Fix Approach and Side Effect Analysis

```
1. What is the proposed fix?
2. What code paths does the fix change?
3. What currently PASSES because of the buggy behavior?
   (Some callers may depend on the wrong behavior)
4. What side effects could this fix introduce?
5. Does this fix require a data migration or cleanup?
6. Is the fix reversible if it causes issues in production?
```

**Rule**: If the fix has known side effects, they must be documented in the PR description
and corresponding checklist items must be added to verify them.

#### Pre-Step C: Analogical Investigation

After identifying the root cause, ask:

```
1. Same parameter / same pattern in the same component
   - Are there other parameters or fields handled by the same code path?
   - Could they have the same bug?

2. Same pattern in sibling components
   - Does the bug exist in structurally similar components?
   - Example: if ASR parameter mapping is broken, check TTS parameter mapping.
   - Example: if a frontend dropdown is missing a value, check other dropdowns
     using the same data source.

3. Same pattern across layers
   - If the bug is in the API layer, could it also exist in the data processing layer?
   - If the bug is in one provider's adapter, check other provider adapters.
```

Output an **Analogical Investigation Report**:

```
## Analogical Investigation

Root cause pattern: [describe the pattern that caused the bug]

Similar locations checked:
- [location 1]: [result — same bug found / clean / different pattern]
- [location 2]: [result]
- [location 3]: [result]

Additional fixes needed: YES / NO
If YES, list them: [...]
```

**Rule**: The Analogical Investigation Report must be completed before the PR is submitted.
If additional bugs are found, they must either be fixed in the same PR (if small and
low-risk) or tracked as separate tasks immediately.

### Bug Fix Workflow Summary

```
Bug reported
     │
     ▼
Pre-Step A: Root Cause Analysis
     │
     ▼
Pre-Step B: Fix Approach + Side Effect Analysis
     │
     ▼
Pre-Step C: Analogical Investigation
     │
     ▼
Step 0: Explore (impact scope of the fix)
     │
     ▼
Step 1: Classify (T1-T6 for the fix itself)
     │
     ▼
Step 2: Technical Design (T2 and above)
     │
     ▼
Step 3: Code the fix
     │
     ▼
Step 4: Execute Checklist
     │
     ▼
Step 5: Human Review + Gate
     │
     ▼
Step 6: Retrospective — update checklist templates if needed
```

---

## Part 3: Analogical Investigation Standard

The Analogical Investigation discipline applies to all changes, not just bug fixes.
Whenever a change reveals a pattern — whether a bug, a missing feature, or a design
inconsistency — the developer must widen their view before closing the task.

### When to Apply

- After identifying a bug's root cause
- After discovering a missing case during feature development
- After finding that a standard or pattern was applied inconsistently in one place

### Investigation Dimensions

| Dimension | Question |
|-----------|----------|
| Same file, different elements | Do other fields/params in this file follow the same broken pattern? |
| Sibling files | Do files with the same structural role have the same problem? |
| Sibling components | Do analogous components (e.g., TTS vs ASR, frontend vs API) have the same issue? |
| Cross-layer | Does the problem exist at other layers of the same data flow? |
| Cross-module | Are there other modules with a functionally equivalent pattern? |

### Documentation Format

```
## Analogical Investigation

Pattern identified: [concise description]

| Location | Checked | Result | Action |
|----------|---------|--------|--------|
| [file/module] | YES | Clean | None |
| [file/module] | YES | Same issue | Fixed in this PR |
| [file/module] | YES | Similar issue | Tracked as TASK-XXX |
| [file/module] | NO | Not checked | Reason: out of scope — tracked as TASK-XXX |
```

**Rule**: "Not checked" locations must always generate a follow-up task. They may not be
silently ignored.

---

## Part 4: PR and Commit Standards

Every PR for a feature or bug fix must include in its description:

**For features:**
- Feature type (T1-T6)
- Technical Design reference (or inline design for T2/T3)
- Checklist execution summary
- Analogical Investigation Report (if any patterns identified)

**For bug fixes:**
- Root Cause Analysis (Pre-Step A output)
- Fix approach and side effects (Pre-Step B output)
- Analogical Investigation Report (Pre-Step C output)
- Checklist execution summary

See [Git Standards](../common/git-standards.md) for commit message format.

---

## Related Documents

- [Feature Type Classification](./feature-type-classification.md)
- [Technical Design Spec](./technical-design-spec.md)
- [Test Case Requirements](./test-case-requirements.md)
- [Checklist Generation Guide](./checklist-generation-guide.md)
- [Checklist Execution Guide](./checklist-execution-guide.md)
- [Gate Review Criteria](./checklist-gate-review.md)
