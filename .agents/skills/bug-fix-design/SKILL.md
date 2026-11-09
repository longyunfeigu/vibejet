---
name: bug-fix-design
status: experimental
description: Bug Fix Design - guided pre-coding analysis for bug fixes (Root Cause → Side Effects → Analogical Investigation → Classify → Design), with human gate at each step
allowed-tools: Read, Glob, Grep, Bash(git *), Write, AskUserQuestion
user-invocable: true
argument-hint: "[bug description]  (e.g. 'ASR streaming parameter not passed to provider')"
---

# Skill: Bug Fix Technical Design

**Purpose**: Walk through the mandatory pre-coding analysis for a bug fix. Forces root
cause identification, side effect analysis, and analogical investigation before any code
is written. Each step requires human confirmation.

**Reference docs**:
- `docs/reference/guides/delivery/dev-process-and-bug-fix.md`
- `docs/reference/guides/delivery/feature-type-classification.md`
- `docs/reference/guides/delivery/technical-design-spec.md`

---

## Gate Protocol

At every gate, call `AskUserQuestion` with exactly the following structure.
**Never treat a user statement as confirmation** — only an explicit "Confirm"
selection from `AskUserQuestion` may advance the flow.

Gate question: `"Do you confirm the above output?"`

Options (pass exactly these three):
- **Confirm** — output accepted; proceed to next step
- **Revise** — user provides feedback via the Other field; AI revises and
  re-presents this gate; if the revision involved a real trade-off, log a
  Decision Discussion entry (see below)
- **Stop** — AI summarizes completed steps and halts; do not proceed further

**Unattended mode** (vibejet adaptation): when the user has handed the work over and asked not
to be interrupted (for example "全权交给你", "中途不要问我", or a scheduled / background run),
do not call `AskUserQuestion`. At each gate:
- pick the option the evidence supports yourself: **Confirm**, or **Revise** and fix the output
  before moving on;
- log the gate in the Decision Log as `Gate: auto-confirmed — pending user review`, with the
  evidence you relied on;
- pick **Stop** only for the reasons a human would: the root cause or the scope cannot be stated
  with evidence, a T4 design needs approval, or the next step is destructive or irreversible.

List every auto-confirmed gate at the top of the saved document, so the user can review them in
one pass. The "never treat a user statement as confirmation" rule above applies to interactive
runs.

**Decision Discussion tracking**: when a "Revise" round involves a genuine
trade-off or option comparison (not a simple wording fix), append one entry
to the running Decision Log kept in memory during the session:

```
### [Step Name] — Decision Discussion

**Decision point (option comparison)**: [the choice faced; list alternatives]
**Additional context**: [any extra questions or thoughts raised by the user]
**Rationale**: [why the chosen direction was selected; why alternatives were ruled out]
**Decision**: [the confirmed outcome]
```

This log is included in the saved document at Step 4. Steps where only minor
wording corrections happened need not be logged.

---

## Step 0: Get Bug Description

If the user provided an argument when invoking the skill, use it as the bug description.

If no argument was given, ask:

> Please describe the bug:
> 1. What is the symptom? (observable behavior)
> 2. Where does it occur? (component, endpoint, flow)
> 3. Any known reproduction steps?
> 4. Link to bug report or task (if any)

---

## Pre-Step A: Root Cause Analysis

Before touching any code, investigate the bug and produce a **Root Cause Analysis**.

**How to investigate**:
- Read the relevant source files
- Trace the data/call flow from symptom back to origin
- Check git log for recent changes in the area (`git log --oneline -20 -- [file]`)
- Look for the deepest point where the behavior diverges from intent

**Output format**:

```
## Pre-Step A: Root Cause Analysis

Bug: [description]
Date: [today]

### Symptom
[Exact observable behavior — what the user or system sees]

### Root Cause
[The deepest origin of the problem — not the surface symptom]

Trace:
1. [entry point] → [what happens]
2. [next layer] → [what happens]
3. [root location: file:line] → [the actual flaw]

### Why Was This Not Caught Earlier?
[ ] Missing test coverage for this case
[ ] Wrong assumption in original design: [describe]
[ ] Unexpected data/environment condition: [describe]
[ ] Other: [describe]

### Isolated Mistake or Deeper Pattern?
[Is this a one-off error, or does it indicate a recurring pattern in this area?]
```

**[GATE]** Present the Root Cause Analysis. Ask the user to confirm or revise.

**Rule**: If the root cause cannot be clearly stated after investigation, do not proceed.
Tell the user: "Root cause is unclear. Additional investigation is needed before we
can design a fix." List what would help clarify it.

---

## Pre-Step B: Fix Approach and Side Effect Analysis

Based on the confirmed root cause, propose a fix and enumerate its side effects.

**Output format**:

```
## Pre-Step B: Fix Approach and Side Effect Analysis

### Proposed Fix
[Precise description of what will change in the code]

### Code Paths Affected by the Fix
- [file:line] — [what changes]
- [file:line] — [what changes]

### Callers That May Depend on the Current (Buggy) Behavior
| Caller | Location | Depends on Buggy Behavior? | Impact of Fix |
|--------|----------|--------------------------|--------------|
| [name] | [file:line] | YES/NO | [describe] |

### Possible Side Effects
[Enumerate explicitly — "no side effects" requires justification]

### Data Migration Required?
YES/NO — [if yes, describe what data is affected and what must happen]

### Is the Fix Reversible?
YES/NO — Rollback approach: [describe]

### Blast Radius if Fix Causes Issues in Production
[Describe what would break and for how many users/flows]
```

**[GATE]** Present the Fix Approach and Side Effect Analysis. Ask the user to confirm or revise.

---

## Pre-Step C: Analogical Investigation

After confirming the fix approach, widen the investigation to catch similar problems.

**Investigation dimensions** (check all that apply):

1. **Same component, other parameters/fields**: Do other parameters in the same
   component go through the same code path? Could they have the same bug?

2. **Sibling components**: Do structurally similar components have the same issue?
   - Example: if ASR parameter mapping is broken → check TTS parameter mapping
   - Example: if one provider adapter has the bug → check other provider adapters

3. **Cross-layer**: If the bug is in the API layer → check the data processing layer.
   If it's in one service → check the parallel service.

4. **Cross-module**: Are there other modules with functionally equivalent code that
   could have the same flaw?

**How to investigate**:
- Grep for the same pattern that caused the bug
- Read sibling files that share the same structure
- Check analogous flows in other modules

**Output format**:

```
## Pre-Step C: Analogical Investigation

Root cause pattern: [concise description of the pattern]

### Locations Checked

| Location | Checked | Result | Action |
|----------|---------|--------|--------|
| [file/module] | YES | Clean — no issue | None |
| [file/module] | YES | Same bug found | Fix in this PR |
| [file/module] | YES | Similar issue | Create follow-up task |
| [file/module] | NO | Not checked | Reason: [out of scope / too risky to bundle] → Track as TASK |

### Additional Fixes Needed
YES/NO
If YES:
- [description] — included in this PR / tracked separately as [task ref]
```

**Rule**: Every "NOT checked" location must result in a follow-up task being created.
It may not be silently skipped.

**[GATE]** Present the Analogical Investigation. Ask the user to confirm or revise.

---

## Step 1: Explore — Impact Scope of the Fix

Now explore what the actual code fix will touch.

**Output format**:

```
## Step 1: Impact Scope of Fix

### Files That Will Change
- [file path] — [what changes]

### Modules Affected
- [module] — [why]

### APIs or Contracts That Change
- [name] — YES/NO

### Critical Paths Touched
- YES/NO — [which paths]
```

**[GATE]** Present the Impact Scope. Ask the user to confirm or revise.

---

## Step 2: Classify the Fix

Classify the fix itself as T1–T6 (same criteria as features).

```
## Step 2: Fix Classification

Type: T[N] — [type name]
Reason: [1–2 sentences]
```

**[GATE]** Present the classification. Ask the user to confirm or revise.

**If T1 confirmed**: Output the following and stop:

```
## Result: T1 Fix — No Technical Design Required

Pre-coding analysis is complete. No design document is needed for a T1 fix.

Summary of pre-coding analysis:
- Root cause: [one line]
- Fix: [one line]
- Side effects: none / [brief]
- Analogical investigation: [brief result]

Next step: Use /bug-fix-checklist to generate the verification checklist before coding.
```

---

## Step 3: Technical Design for the Fix

Produce the fix design document, incorporating the pre-coding analysis.

**All sections from the universal design spec, plus**:

```
## Technical Design — Bug Fix

Bug: [description]
Type: T[N]
Date: [today]
Status: Draft

---

### 1. Background
[Brief description of the bug and its impact]
Task/bug report: [link]

### 2. Root Cause (from Pre-Step A)
[Paste confirmed root cause — trace included]

Why not caught earlier: [confirmed reason]

### 3. Fix Approach (from Pre-Step B)
[Proposed fix — precise code-level description]

### 4. Impact Scope
Files: [list]
Modules: [list]
APIs / contracts: [list or "none"]
Critical paths: [list or "none"]

### 5. Side Effects and Risks (from Pre-Step B)
Callers depending on buggy behavior: [table or "none"]
Other side effects: [list or "none — confirmed in Pre-Step B"]
Reversible: YES/NO
Rollback approach: [description]

### 6. Analogical Investigation (from Pre-Step C)
Pattern: [description]
Additional fixes bundled: [list or "none"]
Follow-up tasks created: [list or "none"]
```

**Level-specific additions** (same as feature-design):
- **T3**: Full Conflict Map
- **T4**: ADR + Migration Plan + Rollback Procedure (requires tech lead approval)
- **T5**: Complete Usage Map
- **T6**: Breaking Change Analysis

**[GATE]** Present the complete design. Ask the user to confirm or revise.

**If T4**: After content confirmed, additionally ask:

> **[T4 GATE]** This is a T4 Architectural Fix. Tech lead approval is required
> before coding begins.
>
> Has the tech lead reviewed and approved this design?
> - Yes — proceed
> - No — stop here until approval is obtained

---

## Step 4: Output and Next Steps

After design is confirmed, write **one file**, in Chinese:

```
docs/work/delivery/[YYYY-MM]/[DD]-bugfix-[slug]/design.md
```

Naming rules:
- `[YYYY-MM]`: year and month from today's date
- `[dayofmonth-description]`: `DD-bugfix-[slug]` (day of month + description)
- `[slug]`: lowercase, hyphen-separated summary of the bug (max 5 words), e.g. `asr-param-mapping-wrong`

**Always write the design file**, regardless of T-level (T2–T6). T1 is exempt from design.

The document must contain the final confirmed content of every step, followed by
a **Decision Log** section at the end:

```
---

## Decision Log

[Include one entry per step where a genuine trade-off was discussed (i.e., the
user selected "Revise" and the revision involved option comparison, not just
wording). Steps with no substantive discussion are omitted.]

### [Step Name] — Decision Discussion

**Decision point (option comparison)**: ...
**Additional context**: ...
**Rationale**: ...
**Decision**: ...

---
(If no substantive decisions were discussed across all steps, write a single
line: "All steps confirmed on first presentation — no decision discussions recorded.")
```

Then output:

```
## Bug Fix Design Complete

Bug: [description]
Type: T[N]
Design document: docs/work/delivery/[YYYY-MM]/[DD]-bugfix-[slug]/design.md
Pre-coding analysis: Complete (Root Cause → Side Effects → Analogical Investigation)
Design status: Confirmed

Summary:
- Root cause: [one line]
- Fix approach: [one line]
- Side effects: [one line]
- Additional fixes bundled: [N] / Follow-up tasks: [N]

---

Next step: Use /bug-fix-checklist to generate the verification checklist.
The checklist must be generated BEFORE writing the fix code.
```

---

## Error Handling

| Situation | Action |
|-----------|--------|
| Root cause unclear after investigation | Stop at Pre-Step A — list what additional info is needed |
| Fix would affect too many callers to safely bundle | Flag in Pre-Step B, recommend scoping the fix down |
| Analogical investigation finds many similar bugs | List all findings, ask user whether to bundle or track separately |
| T4 without tech lead approval | Stop after Step 3 gate — do not proceed to checklist |
