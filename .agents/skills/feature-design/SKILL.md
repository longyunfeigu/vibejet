---
name: feature-design
status: experimental
description: Feature Technical Design - guided design process for new features (Explore → Classify → Design), with human confirmation gate at each step
allowed-tools: Read, Glob, Grep, Bash(git *), Write, AskUserQuestion
user-invocable: true
argument-hint: "[feature description]  (e.g. 'add retry logic to LLM proxy timeout')"
---

# Skill: Feature Technical Design

**Purpose**: Walk through the pre-coding design process for a new feature. Each step
produces a concrete output and requires human confirmation before proceeding.
T1 features are exempt from design; T2 and above produce a design document.

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

## Step 0: Get Feature Description

If the user provided an argument when invoking the skill, use it as the feature description.

If no argument was given, ask:

> What is the feature you want to design?
> Please describe what it should do and any known constraints.

---

## Step 1: Explore — Impact Scope Report

Scan the codebase and produce an **Impact Scope Report**.

**How to explore**:
- Use Glob and Grep to locate relevant files
- Read CLAUDE.md files in affected modules
- Trace call chains to find downstream impact
- Check for shared Pydantic schemas, API contracts, enums

**Output format**:

```
## Step 1: Impact Scope Report

Feature: [feature description]
Date: [today]

### Files Likely to Change
- [file path] — [reason]

### Modules Affected
- [module name] — [why affected]

### Shared Interfaces / Contracts Touched
- [schema / API / enum] — [yes/no, describe if yes]

### New Fields Added to Shared Schema
- YES / NO
- If YES: [list each field name, its type, and which model/schema it belongs to]
  (These fields require Field Addition Compatibility Analysis in Step 3.)

### Critical Paths Touched
- [auth / ownership / DB migration / UoW transaction / etc.] — YES/NO

### External Dependencies Involved
- [library / third-party service] — YES/NO

### Features That Depend on Changed Behavior
- [feature name] — [how it depends]
```

**[GATE]** Present the Impact Scope Report. Ask the user to confirm or revise.

---

## Step 2: Classify — Feature Type

Based on the confirmed Impact Scope Report, classify the feature as T1–T6.

Use this decision tree:

```
Display/styling only, no logic/data impact? → T1
External library or provider changing?      → T6 (may also be T4)
Fundamental architecture changing?          → T4
Shared element changing across many files?  → T5 (may also be T3)
New behavior contradicts existing logic?    → T3
Otherwise                                  → T2
```

**Output format**:

```
## Step 2: Feature Classification

Type: T[N] — [type name]
Secondary type (if applicable): T[N] — [type name]

Reason: [1–2 sentences]

Impact summary:
- Files affected: [N]
- Modules affected: [list]
- Critical paths: YES/NO
- External dependencies: YES/NO

[If T3] Conflict Map:
| File | Line | Old Assumption | Must Handle |
|------|------|---------------|------------|
| ...  | ...  | ...           | YES/NO     |

[If T5] Complete Usage Map:
| File | Line | Usage Type |
|------|------|-----------|
| ...  | ...  | ...       |

[If T6] Breaking changes from changelog:
| Change | Affects Us? |
|--------|------------|
| ...    | ...        |
```

**[GATE]** Present the classification. Ask the user to confirm or revise.

**If T1 confirmed**: Output the following and stop:

```
## Result: T1 — No Technical Design Required

This feature is presentation-only. No technical design document is needed.

Next step: Use /feature-checklist to generate the verification checklist before coding.
```

---

## Step 3: Technical Design

Produce the technical design document based on the confirmed classification.

Read the level-specific requirements from:
`docs/reference/guides/delivery/technical-design-spec.md`

### Design Presentation Principles (MANDATORY)

**Pyramid Principle**: Always present top-down — conclusion first, details second.
- State the solution approach in one sentence before any elaboration.
- Follow with implementation details only after the approach is established.
- Never lead with implementation details before stating what is being built.

**Implementation Detail Coverage**: The "Proposed Change" section must explicitly
address every dimension listed below. Omitting a dimension is not acceptable;
if a dimension is not applicable, state "N/A — [reason]" explicitly.

Implementation dimensions to cover:
- **DB changes**: new tables, new columns, migrations, index changes, schema evolution
- **Environment variables**: new vars required, changed defaults, vars removed
- **Business logic flow**: how data flows through the system end-to-end (API → service → DB → response)
- **API changes**: new endpoints, changed request/response shapes, versioning impact
- **Async / background tasks**: Celery tasks, queues, scheduled jobs affected
- **Configuration**: feature flags, service config, Helm values changes
- **External service calls**: third-party APIs, LLM calls, storage operations

**Universal sections (all T2–T6)**:

```
## Technical Design

Feature: [feature name]
Type: T[N]
Date: [today]
Status: Draft

---

### 1. Background and Motivation
[Current state, problem, why now, task/PRD link]

### 2. Solution Overview

> **Required for T3–T6; strongly recommended for T2 when the change crosses component boundaries.**

One paragraph stating what approach is taken and why — the pyramid top. Readers should
understand the overall strategy before seeing any implementation detail. Do not list files
or specifics here; save those for later sections.

### 3. Architecture: Before and After

> **Required for T3–T6; include whenever the change affects how components interact.**

Show how the system works **before** and **after** the change at the component level.
This section bridges Background (why we're changing) and Proposed Change (what specifically changes).

**Elements to include:**
- **Before** diagram: current component topology and data flow (ASCII diagram)
- **After** diagram: target component topology and data flow (ASCII diagram)
- **Component roles table**: what each component is responsible for after the change
- **Data flow or sequence diagram** (Mermaid preferred): critical paths affected by this change,
  covering both the happy path and key edge cases (e.g. unauthenticated, non-owner access)

Place this section **before** "Proposed Change / What Changes" so that readers understand
the system-level picture before seeing the list of implementation decisions.

### 4. Proposed Change

> **Solution (one sentence)**: [State the approach before any detail — Pyramid Principle]

What changes: [precise description]
What does NOT change: [scope boundary]
New behavior: [description]

#### Implementation Details

| Dimension | Changes | Notes |
|-----------|---------|-------|
| DB changes | [new tables / columns / migrations, or "N/A"] | [migration strategy if applicable] |
| Environment variables | [new / changed / removed vars, or "N/A"] | [default values, required vs optional] |
| Business logic flow | [end-to-end: API → service → DB → response] | [sequence or bullet steps] |
| API changes | [new endpoints / changed shapes / versioning, or "N/A"] | [breaking change: YES/NO] |
| Async / background tasks | [Celery tasks / queues / scheduled jobs, or "N/A"] | [queue name, retry policy] |
| Configuration | [feature flags / service config / Helm values, or "N/A"] | [per-environment differences] |
| External service calls | [third-party APIs / LLM / storage, or "N/A"] | [auth, error handling] |

### 5. Impact Scope
Files: [list]
Modules: [list]
APIs / contracts: [list or "none"]
Data structures: [list or "none"]
Critical paths: [list or "none"]

### 6. Side Effects and Risks
[Enumerate explicitly — "no side effects" is not acceptable]
Reversible: YES/NO
Rollback approach: [description]

### 7. Analogical Investigation
Pattern this change addresses: [description]
Similar locations checked: [list with results]
Follow-up tasks created: [list or "none"]
```

**Level-specific additions**:

- **T2**: Add caller compatibility table (all callers of modified functions listed)
- **T3**: Add full Conflict Map with resolution for each location
- **T4**: Add Architecture Decision Record + phased Migration Plan + tested Rollback Procedure
- **T5**: Add Complete Usage Map including dynamic references
- **T6**: Add Breaking Change Analysis table referencing the changelog

**Field Addition Compatibility Analysis** (conditional):

If Step 1 flagged "New Fields Added to Shared Schema: YES", include this section
in the design document before Side Effects and Risks. For each new field, fill in
Q0/Q1/Q2 with a concrete recommendation — do NOT leave any answer blank or write "TBD".
Present your recommendations to the user; let them confirm or revise each one.

Read the template from:
`docs/reference/guides/delivery/technical-design-spec.md`
— section "Supplementary Analysis: Field Addition Compatibility"

When presenting Q0/Q1/Q2 to the user:
- State your recommendation first ("I recommend X because Y")
- Ask the user to confirm or correct
- Record the confirmed answer in the design document

**[GATE]** Present the complete design document. Ask the user to confirm or revise.

**If T4**: After user confirms content, additionally ask:

> **[T4 GATE]** This is a T4 Architectural Change. The design must be approved by
> the tech lead before coding begins.
>
> Has the tech lead reviewed and approved this design?
> - Yes — proceed
> - No — stop here until approval is obtained

---

## Step 4: Output and Next Steps

After the design is confirmed, write **one file**, in Chinese:

```
docs/work/delivery/[YYYY-MM]/[DD]-feature-[slug]/design.md
```

Naming rules:
- `[YYYY-MM]`: year and month from today's date
- `[dayofmonth-description]`: `DD-feature-[slug]` (day of month + description)
- `[slug]`: lowercase, hyphen-separated summary of the feature (max 5 words), e.g. `retry-logic-llm-proxy`

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
## Design Complete

Feature: [feature name]
Type: T[N]
Design document: docs/work/delivery/[YYYY-MM]/[DD]-feature-[slug]/design.md
Design status: Confirmed

---

Next step: Use /feature-checklist to generate the verification checklist.
The checklist must be generated BEFORE coding begins.
```

---

## Error Handling

| Situation | Action |
|-----------|--------|
| Feature description too vague to explore | Ask for clarification before Step 1 |
| Cannot determine T-level with confidence | Present two options with trade-offs, ask user to decide |
| T4 without tech lead approval at gate | Stop — do not proceed to checklist |
| User skips a gate explicitly | Acknowledge, note the deviation, proceed with warning |
