---
name: bug-fix-checklist
status: experimental
description: Bug Fix Checklist - generate and execute the verification checklist for a bug fix, including root cause verification, side effect checks, and analogical investigation validation. Human gate before execution and after AUTO results. Ends by drafting the Release-Check verification guide QA uses to test the change.
allowed-tools: Read, Glob, Grep, Bash(git *), Bash(python3 *), Bash(pytest *), Bash(npm run lint\:release-check *), Bash(npx tsx *), Write, AskUserQuestion
user-invocable: true
argument-hint: "[bug description or design file path]"
---

# Skill: Bug Fix Checklist

**Purpose**: Generate the verification checklist for a bug fix, including bug-specific
mandatory items (root cause verification, side effect checks, analogical investigation
validation). Execute AUTO items and present HUMAN items for developer review with gates
at each step.

**Prerequisite**: `/bug-fix-design` must have been completed and confirmed.

**Reference docs**:
- `docs/reference/guides/delivery/test-case-requirements.md`
- `docs/reference/guides/delivery/dev-process-and-bug-fix.md`
- `docs/reference/guides/delivery/checklist-generation-guide.md`

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

This log is included in the saved checklist report at Step 4. Steps where only
minor wording corrections happened need not be logged.

---

## Step 0: Load Bug Fix Context

Ask the user to provide (or point to) the completed bug fix design:

> Please provide the bug fix design summary, or the path to the design document.
> I need:
> - Bug description and root cause (from Pre-Step A)
> - Fix approach and known side effects (from Pre-Step B)
> - Analogical investigation results (from Pre-Step C)
> - T-level classification and impact scope

If the user just completed `/bug-fix-design`, ask them to confirm these details.

---

## Step 1: Generate Checklist

Generate a bug-fix-specific checklist that combines:

1. **Bug-specific mandatory items** (always included regardless of T-level)
2. **T-level items** (from test-case-requirements.md for the classified T-level)
3. **Side effect verification items** (derived from Pre-Step B)
4. **Analogical investigation validation items** (derived from Pre-Step C)

**Rules**:
- Every item must be specific — file names, function names, exact commands
- Every item must be tagged `[AUTO]` or `[HUMAN]`
- Items must be grouped by category

---

### Bug-Specific Mandatory Items (Always Included)

These items appear in every bug fix checklist, regardless of T-level:

```
### Root Cause Verification
- [AUTO/HUMAN] Reproduce the original bug — confirm the symptom exists before the fix
  (mark [AUTO] if reproducible via test; [HUMAN] if requires manual steps)
- [AUTO] After applying fix — confirm the original symptom no longer occurs
  Evidence: [test output or manual result]
- [HUMAN] Verify the fix targets the root cause at [root location: file:line],
  not just suppresses the symptom

### Side Effect Verification
[For each side effect identified in Pre-Step B]:
- [AUTO/HUMAN] Verify [specific side effect] does not occur
  Check: [specific file/test/flow]

[For each caller identified as depending on buggy behavior]:
- [HUMAN] Verify caller [name] at [file:line] still works correctly with fixed behavior
  Test: [specific test or manual flow]

### Analogical Investigation Validation
[For each location marked "Same bug found — fixed in this PR" in Pre-Step C]:
- [AUTO] Verify fix applied correctly at [location]
- [HUMAN] Test the flow involving [location] end-to-end

[For each follow-up task created in Pre-Step C]:
- [HUMAN] Confirm follow-up task [task ref] was created and is visible in the tracker
```

---

### T-Level Items

Add the appropriate items from `test-case-requirements.md`:

**T1 additions**:
```
### Visual Check
- [HUMAN] Confirm the fix did not change any visual rendering unexpectedly
```

**T2 additions**:
```
### Regression
- [AUTO] Run test suite for [affected module] — all pass
- [AUTO] Run tests for callers of modified function — all pass
- [HUMAN] Manual test: primary flow that was broken now works correctly
```

**T3 additions**:
```
### Bad Cases
- [HUMAN] Test with input that previously relied on the buggy behavior — handled correctly
- [HUMAN] Test with null/empty/boundary values for changed field

### Conflict Map
[For each item in the Conflict Map from the design]:
- [HUMAN] [file:line] — verify [old assumption] correctly handled for [new behavior]
```

**T4 additions**:
```
### Migration
- [HUMAN] Migration script run on production data copy — no errors, no data loss
- [AUTO] Post-migration data integrity checks pass (row counts, field values, FK integrity)
- [HUMAN] Rollback procedure tested in staging — system recovers cleanly

### Cross-Feature Interaction
- [HUMAN] [top 2–3 adjacent features] — primary flows tested, no unexpected behavior
```

**T5 additions**:
```
### Completeness
- [AUTO] Grep for old [element] — expected 0 remaining occurrences
- [HUMAN] Spot-check [3–5 locations] — change is semantically correct, not just syntactic
```

**T6 additions**:
```
### Behavior Parity
- [AUTO] Existing test suite passes with new dependency version
- [HUMAN] Primary flow using the dependency — output matches expected format
- [HUMAN] Each breaking change from changelog explicitly tested
- [HUMAN] Unavailability/error response from dependency — fallback works correctly
```

---

**Output format**:

```
## Bug Fix Checklist

Bug: [description]
Type: T[N]
Generated: [date]

Root cause: [one line]
Fix: [one line]
Side effects identified: [N] | Analogical fixes bundled: [N] | Follow-up tasks: [N]

---

### Root Cause Verification
- [AUTO/HUMAN] ...

### Side Effect Verification
- [AUTO/HUMAN] ...

### Analogical Investigation Validation
- [AUTO/HUMAN] ...

### [T-level category]
- [AUTO/HUMAN] ...

### Architecture Compliance
- [AUTO] No print() statements added — grep: 0 results
- [AUTO] All new functions have type hints

---

Total items: [N]
AUTO: [N] | HUMAN: [N]
```

**[GATE]** Present the complete checklist. Ask the user to confirm or revise before
any execution begins.

---

## Step 2: Execute AUTO Items

After checklist is confirmed, execute every `[AUTO]` item.

**For each AUTO item**:
1. Run the verification
2. Record result: `PASS`, `FAIL`, or `WARNING`
3. Paste real evidence — actual output, not a summary
4. Never self-certify without evidence

**Priority order for execution**:
1. Root Cause Verification items first — if the bug is not fixed, stop immediately
2. Side Effect Verification items
3. Analogical Investigation Validation items
4. T-level items
5. Architecture Compliance items

**If Root Cause Verification FAILS** (bug not actually fixed):
- Stop all execution immediately
- Report: "Root cause verification failed — the original bug symptom still occurs.
  The fix does not address the root cause."
- Do not proceed until the fix is revised

**If any other AUTO item FAILS**:
- Report clearly
- Ask user: "An AUTO item has failed. Fix and re-run, or continue and fix all at once?"

**Output format for each item**:

```
#### [AUTO] [item text]
Result: PASS / FAIL / WARNING
Evidence:
[actual output]
```

After all AUTO items:

```
## AUTO Execution Summary

| Category | PASS | FAIL | WARNING |
|----------|------|------|---------|
| Root Cause Verification | [N] | [N] | [N] |
| Side Effect Verification | [N] | [N] | [N] |
| Analogical Validation | [N] | [N] | [N] |
| [T-level category] | [N] | [N] | [N] |
| Architecture Compliance | [N] | [N] | [N] |
| TOTAL | [N] | [N] | [N] |

Overall AUTO result: PASS / FAIL
```

**[GATE]** Present AUTO results. Ask the user:
- Confirm results are trustworthy (not false positives)
- Confirm the root cause verification is conclusive
- Confirm to proceed to HUMAN items

---

## Step 3: Present HUMAN Items

For each `[HUMAN]` item, provide context for the developer to verify it.

**For each HUMAN item**:
1. Read relevant code sections
2. Describe what needs to be verified and why
3. Provide specific verification steps
4. Provide decision record template

**Output format for each item**:

```
#### [HUMAN] [item text]

Context:
[file:line reference and relevant code]
[what the correct behavior should be]

How to verify:
[step-by-step — specific enough to follow without ambiguity]

Decision record:
Verified by: ______
Date: ______
Result: PASS / FAIL / N/A
Notes: ______
```

After all HUMAN items:

```
## HUMAN Items Summary

[N] items require human verification.

Critical items (must PASS, N/A not acceptable):
- Root cause verification items
- Side effect verification for callers that depended on buggy behavior
- Analogical investigation fixes bundled in this PR

Please complete each decision record above.
```

**[GATE]** Ask the user to confirm all HUMAN items have been personally verified
and decision records completed.

---

## Step 4: Gate Decision

```
## Gate Decision — Bug Fix

Bug: [description]
Type: T[N]
Reviewer: ______
Date: [today]

Pre-coding analysis completed:
- Root Cause Analysis: YES/NO
- Side Effect Analysis: YES/NO
- Analogical Investigation: YES/NO

Results:
- AUTO items: [N] PASS, [N] FAIL, [N] WARNING
- HUMAN items: [N] PASS, [N] FAIL, [N] N/A
- Total items: [N]

Critical checks:
- Root cause verified fixed: YES/NO
- All side effects verified: YES/NO
- Analogical fixes verified: YES/NO
- Follow-up tasks created for unchecked locations: YES/NO/N/A

Gate: [ ] PASS  [ ] FAIL

PASS conditions:
- Zero AUTO failures
- Zero HUMAN failures
- Root cause verified fixed
- All side effects checked
- All analogical follow-up tasks created

Notes for retrospective:
[Any checklist items to add based on this bug — so this class of bug is caught earlier next time]
```

**Rule**: Do NOT fill in the Gate decision or reviewer name.

**After Gate PASS**, write **one file**, in Chinese:

```
docs/work/delivery/[YYYY-MM]/[DD]-bugfix-[slug]/checklist.md
```

Use the same `[slug]` as the corresponding design document for this bug fix.

The report must include the full checklist with all execution results and decision
records filled in, followed by a **Decision Log** section at the end:

```
---

## Decision Log

[Include one entry per gate where a genuine trade-off was discussed. Omit steps
where the user only made minor wording corrections.]

### [Step Name] — Decision Discussion

**Decision point (option comparison)**: ...
**Additional context**: ...
**Rationale**: ...
**Decision**: ...

---
(If no substantive decisions were discussed, write a single line:
"All gates confirmed on first presentation — no decision discussions recorded.")
```

Then continue to **Step 5**. After Step 5 is confirmed (or exempted), output:

```
Next steps:
1. Checklist report saved to: docs/work/delivery/[YYYY-MM]/[DD]-bugfix-[slug]/checklist.md
2. Release-Check guide saved to: AutoTest/Release-Check/<YYYY-MM>/bugfix/<file name> (Step 5), or a `Release-Check: exempt <reason>` trailer in the commit message
3. Include links to the design doc, the checklist report, and the Release-Check guide in the PR description
4. After merge: consider whether this bug class should be added to the T-level checklist
   templates so future changes in this area catch it automatically
```

---

## Step 5: Release-Check Acceptance Guide

**Purpose**: QA's verification AI tests every change in any environment
from a written guide — developers are never asked to explain verbally. This step drafts that
guide from the design and this checklist, so it ships in the same branch as the code.

Standard (read first): `AutoTest/Release-Check/STANDARD.md`
Template: `AutoTest/Release-Check/TEMPLATE-bugfix.md` (Chinese headings; write the guide in Chinese)

**Exempt** only when the change has no runtime behavior to accept (pure refactor, CI, docs,
AutoTest-only). Then skip this step and tell the developer to write
a `Release-Check: exempt <reason>` trailer in the commit message.

### 5.1 Locate the file

Confirm with `AskUserQuestion`, pre-filled with your best guess (in unattended mode, use the
guess and log it):
- **Guide folder**: the current month, `YYYY-MM` (vibejet has no release branches; guides are
  grouped by month, like `docs/work/delivery/`)
- **Author handle** of the change (guess from `git config user.name` / `user.email`; lowercase,
  no spaces)

Source branch: `git branch --show-current`. File name:

```bash
cd AutoTest && npx tsx -e "console.log(require('./core/release-check/guide-name').suggestGuideFileName('<source branch>', '<gitlab username>'))"
```

Path: `AutoTest/Release-Check/<YYYY-MM>/bugfix/<file name>`

### 5.2 Draft from what this fix already produced

| Guide section | Take it from |
|---|---|
| Background and goal | design: Symptom, Root Cause |
| Reproduction conditions / Behavior on old version | design Root Cause Analysis; the checklist's "reproduce before fix" item and its recorded output |
| Expected after fix | the checklist's "symptom gone after fix" item and its recorded output |
| Root cause | design Root Cause (one sentence) |
| Must not break | design: callers that depend on old behavior, side effects; checklist side-effect and regression items |
| How to verify | HUMAN items and post-deploy items in this checklist (e.g. a load test, a real end-to-end run) |
| Depth hints | design Analogical Investigation: neighboring paths with the same root cause |

Write observable signals, not click-by-click steps. The acceptance AI finds its own path.

**Drafting rules** (each one comes from a real acceptance run where the guide misled the AI):
1. **Every check must be able to fail on the old version.** For each "How to verify" item, ask:
   would the version before this change pass it? If yes, the check is useless — rewrite it.
2. **Name the exact component that serves the request.** Check routing: e.g. in local dev the
   frontend's `/api` calls are proxied by Vite to the backend (`frontend/vite.config.ts`).
3. **Name the real source of a setting** (env var vs start-up args vs values file), not where it
   "usually" lives.
4. **Give the full page path** (navigation → page, URL pattern like `/login`).
   Page names that also appear elsewhere get the AI lost.
5. **List enumerations completely** (all roles, all status values, all endpoints) — or point to the
   exact code constant.
6. **Say what test data must already exist for the test account** (see
   `AutoTest/Release-Check/_shared/fixtures.md`). If it
   may not exist, either declare it a prerequisite or use `safety: writes-test-data` and create
   `e2e-`-prefixed data that is deleted afterwards.
7. **Define timing thresholds precisely**: from which moment to which moment, measured where.
8. **"Same as before" needs a baseline**: name the metric and the allowed tolerance.
9. **Deployment prerequisites beyond the image** (env vars, migrations, rollout order) go
   into "This change".
10. No hosts, IPs, accounts, secrets, or environment names (STANDARD 1.8).
11. **Never declare a verdict.** Do not write "not applicable" / 「不适用」 in "How to verify" or
    "Must not break" (lint `verdict-override` rejects it). If an item needs a precondition (a
    configured key, a mode), say how to create it with the test account; what the environment itself may lack
    (a service, an external dependency) goes into `requires` (STANDARD 1.15), and the verifier
    marks the dependent items not applicable where it is missing.
12. **Verify on the new version only.** No step may reproduce the old bug, switch to the old image, or
    build the old failure path first (lint `reproduce-old`). Rule 1 is a thought test for you while
    drafting, not a step for the verifier.
13. **Cite the code for every fact.** Each endpoint path, log keyword, page element, or console line in
    "Entry points" and "How to verify" gets one `file:line` from the source branch. Re-read the code
    instead of writing from memory: past guides named a wrong route and a console log that the page
    never prints.
14. **Count every call in `cost_estimate`**, including calls required by "Must not break"
    (lint `cost-mismatch`).
15. **Keep other guides in step.** If this change removes or alters behavior that another guide in the
    same month folder (or a `regression: true` guide) describes, update that guide in this branch or set
    `supersedes`.
16. **Every `[P0]` runs as written** (STANDARD 1.5, lint `p0-direct`). P0 items run on
    every environment the product is deployed to: test accounts and standing fixtures only, no
    person-supplied resource (real customer account, third-party quota), no stopping/restarting/scaling a service, no business
    traffic, no hours of observation, safe on production. Anything else is P1, or developer evidence in
    the PR. A P0 that cannot run during verification is returned to you as "guide defective".

### 5.3 Lint and gate

```bash
cd AutoTest && npm run lint:release-check -- Release-Check/<YYYY-MM>/bugfix/<file name>
```

Fix every error, then present the guide through the Gate Protocol (Confirm / Revise / Stop).
Write the file only after Confirm.

---

## Error Handling

| Situation | Action |
|-----------|--------|
| No bug fix design provided | Ask user to run /bug-fix-design first, or provide root cause and fix details manually |
| Root cause verification FAIL | Stop immediately — fix does not address root cause |
| Analogical fix locations not all verified | Block gate until verified or tracked |
| Follow-up tasks from Pre-Step C not created | Block gate — they must be created, not deferred silently |
| User wants to skip root cause verification | Acknowledge risk, record deviation explicitly, require written justification |
