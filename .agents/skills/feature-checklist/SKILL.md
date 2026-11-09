---
name: feature-checklist
description: Feature Checklist - generate and execute the verification checklist for a feature, based on the completed feature design. Human gate before execution and after AUTO results. Ends by drafting the Release-Check verification guide QA uses to test the change.
allowed-tools: Read, Glob, Grep, Bash(git *), Bash(python3 *), Bash(pytest *), Bash(npm run lint\:release-check *), Bash(npx tsx *), Write, AskUserQuestion
user-invocable: true
argument-hint: "[feature name or design file path]"
---

# Skill: Feature Checklist

**Purpose**: Generate the verification checklist for a feature based on its design and
T-level, then execute AUTO items, and present HUMAN items for developer review.
Human confirmation is required before execution and again before the gate decision.

**Prerequisite**: `/feature-design` must have been completed and confirmed.

**Reference docs**:
- `RD/docs/standards/ai-era-workflow/test-case-requirements.md`
- `RD/docs/standards/ai-era-workflow/checklist-generation-guide.md`
- `RD/docs/standards/ai-era-workflow/checklist-templates/`

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

## Step 0: Load Feature Context

Ask the user to provide (or point to) the completed feature design:

> Please provide the feature design summary, or the path to the design document.
> I need: feature description, T-level classification, and impact scope.

If the user just completed `/feature-design`, ask them to confirm the T-level and any
key details needed for checklist generation.

---

## Step 1: Generate Checklist

Based on the T-level and feature specifics, generate a feature-specific checklist.

**Rules**:
- Every item must be specific (file names, function names, commands) — no generic items
- Every item must be tagged `[AUTO]` or `[HUMAN]`
- Items must be grouped by category
- The checklist must include test cases required by `test-case-requirements.md` for this T-level

**Required categories by T-level**:

| T-level | Required Categories |
|---------|-------------------|
| T1 | UI/UX, Regression Guard |
| T2 | Regression, Backward Compatibility, Cross-Module Impact, Architecture Compliance |
| T3 | Regression (deep), Conflict Map Resolution, Bad Cases, Edge Cases, Data Compatibility, Deployment Safety |
| T4 | All categories + Migration Plan, Rollback Verification, Phase Testing, Cross-Feature Interaction |
| T5 | Completeness (all locations), Regression, Consistency |
| T6 | Behavior Parity, Breaking Change Coverage, Fallback, Performance |

**T-level-specific mandatory items**:

For T1:
```
[HUMAN] Visual render check — component renders correctly at 1280px and 1920px
[HUMAN] No logic files changed — confirm grep finds no unexpected business logic changes
```

For T3 — add for each item in the Conflict Map:
```
[HUMAN] Conflict Map: [file:line] — verify [old assumption] is now handled for [new behavior]
```

For T4 — add mandatory:
```
[HUMAN] Tech lead approval confirmed before coding began
[HUMAN] Each deployment phase tested independently before next phase
[HUMAN] Migration script run on production data copy — no data loss
[HUMAN] Rollback procedure executed in staging — system recovered cleanly
```

For T5 — add mandatory:
```
[AUTO] Grep for all remaining occurrences of old [element] — expected: 0 results
```

For T6 — add mandatory:
```
[HUMAN] Full changelog reviewed between old and new version
[HUMAN] Each breaking change in changelog explicitly addressed
```

**Conditional mandatory items (when Alembic migration files are changed)**:

When `git diff` shows any file under `alembic/versions/` was added or modified, add this section regardless of T-level:

```
### Database Migration Rollback Safety
- [AUTO] Every changed migration file has a non-trivial downgrade() — search for `pass` or
  `raise NotImplementedError` as the sole statement inside each downgrade() body: expected 0 results
- [HUMAN] Review each migration's downgrade() — confirm it fully reverses the upgrade() operation
  (columns dropped in upgrade must be re-created in downgrade; tables dropped must be re-created, etc.)
- [HUMAN] Confirm upgrade() contains no irreversible operations without an explicit justification
  comment (e.g., DROP TABLE without data backup, DROP COLUMN with permanent data loss,
  raw execute() with destructive DML)
```

**Output format**:

```
## Feature Checklist

Feature: [name]
Type: T[N]
Generated: [date]

### [Category Name]
- [AUTO] [specific, actionable item with exact file/command/pattern]
- [HUMAN] [specific item requiring human judgment — describe exactly what to verify]

### [Next Category]
...

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
1. Run the verification (test, grep, file read, static analysis)
2. Record actual result: `PASS`, `FAIL`, or `WARNING`
3. Paste real evidence — actual command output, grep results, test logs
4. Never self-certify without evidence

**If an AUTO item FAILS**:
- Stop execution of remaining items
- Report the failure clearly
- Ask the user: "An AUTO item has failed. Do you want to fix the issue and re-run,
  or continue running remaining items and fix all at once?"

**Output format for each item**:

```
#### [AUTO] [item text]
Result: PASS / FAIL / WARNING
Evidence:
[actual output — truncated if very long, but never omitted]
```

After all AUTO items are executed, output summary:

```
## AUTO Execution Summary

| Category | PASS | FAIL | WARNING |
|----------|------|------|---------|
| [name]   | [N]  | [N]  | [N]     |
| TOTAL    | [N]  | [N]  | [N]     |

Overall AUTO result: PASS / FAIL (must be 0 FAIL to proceed)
```

**[GATE]** Present AUTO results. Ask the user:
- Confirm results are trustworthy (not false positives)
- Confirm to proceed to HUMAN items
- If any FAIL: ask user to fix and confirm before continuing

---

## Step 3: Present HUMAN Items

For each `[HUMAN]` item, provide context to help the developer verify it.

**For each HUMAN item**:
1. Read the relevant code sections
2. Describe the current state and what needs to be verified
3. Suggest how to verify (UI steps, manual test flow, command to run)
4. Provide a decision record template for the developer to fill in

**Output format for each item**:

```
#### [HUMAN] [item text]

Context:
[relevant code snippet or file:line reference]
[current behavior description]

How to verify:
[step-by-step instructions — specific enough to follow]

Decision record:
Verified by: ______
Date: ______
Result: PASS / FAIL / N/A
Notes: ______
```

After all HUMAN items are presented:

```
## HUMAN Items Summary

[N] items require human verification.
Please complete each decision record above.

When all items are verified, confirm to proceed to the Gate.
```

**[GATE]** Ask the user to confirm that all HUMAN items have been personally verified
and decision records completed.

---

## Step 4: Gate Decision

After both AUTO and HUMAN items are confirmed, produce the Gate Summary:

```
## Gate Decision

Feature: [name]
Type: T[N]
Reviewer: ______  (fill in)
Date: [today]

Results:
- AUTO items: [N] PASS, [N] FAIL, [N] WARNING
- HUMAN items: [N] PASS, [N] FAIL, [N] N/A
- Total items: [N]

Gate: PASS / FAIL

PASS conditions:
- Zero AUTO failures
- Zero HUMAN failures
- Every N/A has a documented reason

Decision: [ ] PASS  [ ] FAIL

Notes for retrospective:
[Any checklist items that should be added/removed based on this feature]
```

**Rule**: Do NOT fill in the Gate decision or reviewer name. Present the template for
the human to complete.

**After Gate PASS**, write **two files**:

```
RD/docs/delivery/[YYYY-MM]/[DD]-feature-[slug]/checklist.md       ← English (primary)
RD/docs/delivery/[YYYY-MM]/[DD]-feature-[slug]/checklist-cn.md    ← Chinese companion (required)
```

Use the same `[slug]` as the corresponding design document for this feature.
The Chinese file is the same report fully translated — not a summary.

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
1. Checklist report saved to: RD/docs/delivery/[YYYY-MM]/[DD]-feature-[slug]/checklist.md (EN) and RD/docs/delivery/[YYYY-MM]/[DD]-feature-[slug]/checklist-cn.md (CN)
2. Release-Check guide saved to: AutoTest/Release-Check/<release branch>/feature/<file name> (Step 5), or `release-check: exempt <reason>` added to the MR description
3. Include links to the design doc, the checklist report, and the Release-Check guide in the PR description
4. After merge: if any checklist items were missing or ineffective, update the
   checklist templates in RD/docs/standards/ai-era-workflow/checklist-templates/
```

---

## Step 5: Release-Check Acceptance Guide

**Purpose**: QA's verification AI tests every change in any environment
from a written guide — developers are never asked to explain verbally. This step drafts that
guide from the design and this checklist, so it ships in the same MR as the code.

Standard (read first): `AutoTest/Release-Check/STANDARD.md`
Template: `AutoTest/Release-Check/TEMPLATE-feature.md` (or `TEMPLATE-feature-cn.md`; a guide needs only one language)

**Exempt** only when the change has no runtime behavior to accept (pure refactor, CI, docs,
AutoTest-only). Then skip this step and tell the developer to write
`release-check: exempt <reason>` in the MR description.

### 5.1 Locate the file

Ask with `AskUserQuestion` (pre-fill your best guess):
- **Release branch** the MR targets (`DEV-YYYYMMDD` or `HOTFIX-...`)
- **GitLab username** of the MR author (guess from `git config user.email`)

Source branch: `git branch --show-current`. File name:

```bash
cd AutoTest && npx tsx -e "console.log(require('./core/release-check/guide-name').suggestGuideFileName('<source branch>', '<gitlab username>'))"
```

Path: `AutoTest/Release-Check/<release branch>/feature/<file name>`

### 5.2 Draft from what this feature already produced

| Guide section | Take it from |
|---|---|
| Background and goal | design §1 Background and Motivation, §2 Solution Overview |
| Entry points | design §4 Proposed Change (pages, APIs, config keys) |
| How to verify | design acceptance criteria; HUMAN items and post-deploy items in this checklist |
| Must not break | design §5 Impact Scope, §6 Side Effects and Risks; checklist regression items |
| Easy to misjudge | side effects that are intended; behaviors that look wrong but are not |
| This change | the diff summary; deployment notes |

Write observable signals, not click-by-click steps. The acceptance AI finds its own path.

**Drafting rules** (each one comes from a real acceptance run where the guide misled the AI):
1. **Every check must be able to fail on the old version.** For each "How to verify" item, ask:
   would the version before this change pass it? If yes, the check is useless — rewrite it.
2. **Name the exact component that serves the request.** Check routing/ingress: e.g. on UAT the
   public flow chat API is served by the simulation backend, not `flow-backend`.
3. **Name the real source of a setting** (env var vs start-up args vs values file), not where it
   "usually" lives.
4. **Give the full page path** (left navigation → page, URL pattern like `/agent/<id>/voice`).
   Page names that also appear elsewhere get the AI lost.
5. **List enumerations completely** (all voice names, all models, all endpoints) — or point to the
   exact code constant.
6. **Say what test data must already exist in the Autotest enterprise** (QA's test tenant). If it
   may not exist, either declare it a prerequisite or use `safety: writes-test-data` and create
   `e2e-`-prefixed data that is deleted afterwards.
7. **Define timing thresholds precisely**: from which moment to which moment, measured where.
8. **"Same as before" needs a baseline**: name the metric and the allowed tolerance.
9. **Deployment prerequisites beyond the image** (values changes, Deploy sync, rollout order) go
   into "This change".
10. No hosts, IPs, accounts, secrets, or environment names (STANDARD 1.8).
11. **Never declare a verdict.** Do not write "not applicable" / 「不适用」 in "How to verify" or
    "Must not break" (lint `verdict-override` rejects it). If an item needs a precondition (a
    configured key, a mode), say how to create it in Autotest; what the environment itself may lack
    (a gray-release key, a model, outbound) goes into `requires` (STANDARD 1.15), and the verifier
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
    same release branch (or a `regression: true` guide) describes, update that guide in this MR or set
    `supersedes`.
16. **Every `[P0]` runs as written** (STANDARD 1.5, lint `p0-direct`). P0 items run on UAT and on
    every production environment: Autotest and standing fixtures only, no person-supplied resource
    (test number, WhatsApp, real read-only account), no stopping/restarting/scaling a service, no business
    traffic, no hours of observation, safe on production. Anything else is P1, or developer evidence in
    the MR. A P0 that cannot run during verification is returned to you as "guide defective".

### 5.3 Lint and gate

```bash
cd AutoTest && npm run lint:release-check -- Release-Check/<release branch>/feature/<file name>
```

Fix every error, then present the guide through the Gate Protocol (Confirm / Revise / Stop).
Write the file only after Confirm.

---

## Error Handling

| Situation | Action |
|-----------|--------|
| No feature design provided | Ask user to run /feature-design first, or provide T-level and impact scope manually |
| AUTO item cannot be run (missing tool, env issue) | Mark as WARNING with explanation, flag for human verification |
| AUTO item fails | Stop, report clearly, ask user how to proceed |
| User skips HUMAN verification gate | Acknowledge, note the deviation, warn that gate cannot formally PASS |
| T4 migration test not yet run | Block gate — migration test is mandatory for T4 |
