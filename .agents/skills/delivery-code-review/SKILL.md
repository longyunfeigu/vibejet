---
name: code-review
description: Code Review - reviews design document quality first, then code quality against standards. Stops if design fails. Saves a review report on completion. Works with feature-design and bug-fix-design outputs.
allowed-tools: Read, Glob, Grep, Bash(git *), Write, AskUserQuestion
user-invocable: true
argument-hint: "[--branch <target>] [design doc path]  (e.g. '--branch master RD/docs/delivery/2026-04-14-feature-ai-builder-v2-design.md')"
---

# Skill: Code Review

**Purpose**: Run a structured review after coding is complete. First validates the
design document; if it passes, reviews the code. At the end, verifies git diff
coverage. Saves a report automatically — no user confirmation gates.

**Works with**: `/feature-design`, `/bug-fix-design` outputs under `RD/docs/delivery/`.

**Reference standards**:
- `RD/CLAUDE.md` (Critical Rules)
- `RD/docs/standards/common/` (language, logging, security, exceptions, testing)
- `RD/docs/standards/backend/` (python, fastapi, validation)
- `RD/docs/standards/frontend/` (typescript-react)

---

## Severity Levels

| Level | Meaning | Consequence |
|-------|---------|-------------|
| **CRITICAL** | Correctness, security, or data safety risk | Blocks merge; design CRITICAL also stops the review |
| **WARNING** | Technical debt or reliability concern | Should be fixed or consciously accepted |
| **INFO** | Minor clarity or style improvement | Optional |

---

## Step 0: Get Two Inputs

If both were provided as arguments, use them and skip asking.
Otherwise, ask **one question** with both fields:

> 1. Path to the design document (e.g. `RD/docs/delivery/2026-04-14-feature-ai-builder-v2-design.md`)
>    — or `none` if this is a T1 change with no design document.
> 2. Target branch to merge into (e.g. `master`, `main`, `develop`).

Infer change type (feature / bug fix) from the design document filename:
- filename contains `bugfix` or `bug-fix` → bug fix
- otherwise → feature

Output:

```
## Review Context

Design document: [path or "T1 — none"]
Target branch: [branch]
Change type: [feature / bug fix]
Current branch: [output of: git branch --show-current]
```

If the user said `none` for the design document, skip Step 1 entirely and proceed
to Step 2 with a note: "T1 change — design document review skipped."

---

## Step 1: Design Document Review

Read the design document in full. Evaluate across three dimensions.

**The standard**: A reviewer with general engineering knowledge but no prior
context should read the document and understand the full picture — what is being
built, why, how, and what could go wrong — without needing to ask follow-up questions.

### 1a: Required sections check

Check each section for **substantive content** ("substantive" = real information,
not a header with "TBD" or a one-sentence placeholder).

**For all changes**:

| Section | Required | Substantive means |
|---------|----------|-------------------|
| Feature / problem description | Yes | Reader knows exactly what is changing and why |
| Background and motivation | Yes | Context and trigger are clear; why now |
| Change plan / proposed solution | Yes | Concrete description of what will be built or changed |
| Key logic | Yes | Non-obvious logic is explained, not just named |
| Modules / files affected | Yes | Specific paths or module names listed |
| Risks and trade-offs | Yes | At least one risk identified; "no risks" requires justification |
| Test and acceptance criteria | Yes | Specific, verifiable criteria — not just "manual testing" |
| Non-functional requirements | Yes | Performance, security, and data volume at minimum addressed |
| Data model / API definitions | Conditional | Required if data structures or APIs change; else state "N/A" |

**Bug fix only** (additional):

| Section | Required | Substantive means |
|---------|----------|-------------------|
| Root cause analysis | Yes | Deepest origin identified with a trace, not just the symptom |
| Why not caught earlier | Yes | Explicit reason (missing test, wrong assumption, etc.) |
| Analogical investigation | Yes | Similar locations checked; findings listed |

### 1b: Self-containment check

Read the document as a cold reader. Flag any location where:
- A term is used without being defined on first use
- A claim requires external context to evaluate ("as discussed", "per the PRD" without quoting it)
- A decision is stated without reasoning ("we will use X" — why not Y?)
- A risk is named but not addressed (no mitigation, no acceptance rationale)

### 1c: Decision quality check

For each key design decision in the document:
1. Are alternatives mentioned? (A decision with no alternatives listed was assumed, not decided)
2. Is the reasoning sound given stated constraints?
3. Are trade-offs acknowledged?

### Design review output

```
## Step 1: Design Document Review

Document: [path]

### 1a: Required Sections

| Section | Status | Finding |
|---------|--------|---------|
| Feature / problem description | PRESENT / THIN / MISSING | [note] |
| Background and motivation      | PRESENT / THIN / MISSING | [note] |
| Change plan                    | PRESENT / THIN / MISSING | [note] |
| Key logic                      | PRESENT / THIN / MISSING | [note] |
| Modules / files affected       | PRESENT / THIN / MISSING | [note] |
| Risks and trade-offs           | PRESENT / THIN / MISSING | [note] |
| Test and acceptance criteria   | PRESENT / THIN / MISSING | [note] |
| Non-functional requirements    | PRESENT / THIN / MISSING | [note] |
| Data model / API definitions   | PRESENT / THIN / MISSING / N/A | [note] |
[bug-fix rows if applicable]

### 1b: Self-containment Findings
[CRITICAL / WARNING / INFO] [location in doc] — [what is unclear and why]

### 1c: Decision Quality Findings
[CRITICAL / WARNING / INFO] [decision] — [what is missing]

### Design Review Result

CRITICAL: [N] | WARNING: [N] | INFO: [N]
```

**Stop rule**: If CRITICAL > 0, output:

```
## Review Stopped

The design document has [N] CRITICAL finding(s). Code review cannot proceed until
the design document is corrected.

Fix the following before re-running /code-review:
[numbered list of CRITICAL findings with specific locations]
```

Then halt. Do not save any files.

If CRITICAL = 0, output `Design review PASSED — proceeding to code review.`
and continue to Step 2.

---

## Step 2: Code Review

Read the files listed in the design document's "modules / files affected" section.
For each file, read it in full — not just the changed lines, because context matters.
Also read any files directly referenced from those files (callers, schemas, tests).

Review each file against all dimensions below. Every finding must include:
`[LEVEL] file:line-or-function — what is wrong — concrete suggestion`

### 2a: Standards compliance

Verify Critical Rules from `RD/CLAUDE.md`:
- No `print()` — only `logger`
- No raw `<button>/<input>/<select>` without checking shared components (frontend)
- No hardcoded hex colors — use Tailwind token classes (frontend)
- No `.env` with real secrets committed
- All inputs at system boundaries validated via Pydantic
- Commit messages in Conventional Commits format
- New `.md` files have a `-cn.md` companion

Verify language-specific standards for affected file types.

### 2b: Functional correctness

- Off-by-one errors, wrong comparison operators, wrong boolean logic
- Incorrect handling of empty / null / zero values
- Race conditions in async code; missing `await` on coroutines
- Exceptions swallowed silently or propagated incorrectly
- Wrong return values or unintended side effects

### 2c: Implementation simplicity

Over-engineering:
- Abstraction created for a single use case
- Helper function used exactly once with no reuse potential
- Feature flag or backwards-compatibility shim where the code could just be changed
- Dead code introduced

Under-implementation:
- Critical edge case unhandled
- Error path that crashes instead of degrading gracefully
- Missing validation at a system boundary

### 2d: Data compatibility

For changes to DB schemas, Pydantic models, API shapes, or message formats:
- Is the change backwards-compatible? Old clients and old data will not break?
- If not: is a migration plan present and correct?
- Are default values provided for new required fields?
- Are field types compatible with existing stored data?

### 2e: Robustness

- Network/external calls: timeout handling, error response handling (not just happy path)
- Database operations: connection error handling, transaction rollback
- File operations: file not found, permission denied
- Concurrent access: shared state protected appropriately

### 2f: Maintainability

- Magic numbers / magic strings not named as constants
- Functions exceeding 50 lines without clear justification
- Nesting depth exceeding 4 levels
- Non-trivial logic duplicated (>10 lines repeated)
- Functions doing more than one thing
- One module reaching into another module's internals

### 2g: Performance and efficiency

- N+1 query patterns (database query inside a loop)
- Unbounded queries on large tables (no LIMIT)
- Redundant computation (same value recalculated in a loop)
- Synchronous blocking call in async context
- Large in-memory structures loaded fully when streaming would work
- New query patterns without corresponding indexes

Do not speculate — flag only what the code actually does.

### 2h: Security

- SQL injection (raw string formatting in queries)
- Command injection (user input passed to shell)
- Path traversal (user-controlled file paths without sanitization)
- Hardcoded credentials or tokens
- Sensitive data in log statements (passwords, tokens, PII)
- Missing auth/authz checks on new endpoints
- CORS misconfigurations in new API routes

### 2i: Readability

Only for changed code:
- Variable or function names that do not describe their purpose
- Complex boolean expressions without intermediate named variables
- Non-obvious logic without an explaining comment
- Positional boolean parameters in function signatures

Do not add comments, docstrings, or type annotations to code that was not changed.

### 2j: Testability and test coverage

- New logic paths have corresponding test cases
- Tests cover at minimum: happy path, empty/null input, error conditions
- Tests mock only external dependencies — not internal business logic
- Tests use real assertions, not just "no exception raised"
- New public functions and endpoints have at least one test

### 2k: Extensibility

Only flag likely real limitations, not hypothetical ones:
- Hardcoded list of values that is likely to grow (should be config or enum)
- Tight coupling to a specific implementation that forecloses stated future requirements
- Shared mutable state that limits horizontal scaling

### Code review output

```
## Step 2: Code Review

Files reviewed: [list]

### 2a: Standards Compliance
[findings or "No findings."]

### 2b: Functional Correctness
[findings or "No findings."]

### 2c: Implementation Simplicity
[findings or "No findings."]

### 2d: Data Compatibility
[findings or "No findings."]

### 2e: Robustness
[findings or "No findings."]

### 2f: Maintainability
[findings or "No findings."]

### 2g: Performance and Efficiency
[findings or "No findings."]

### 2h: Security
[findings or "No findings."]

### 2i: Readability
[findings or "No findings."]

### 2j: Testability and Test Coverage
[findings or "No findings."]

### 2k: Extensibility
[findings or "No findings."]

### Code Review Summary

| Dimension | CRITICAL | WARNING | INFO |
|-----------|----------|---------|------|
| Standards compliance | [N] | [N] | [N] |
| Functional correctness | [N] | [N] | [N] |
| Implementation simplicity | [N] | [N] | [N] |
| Data compatibility | [N] | [N] | [N] |
| Robustness | [N] | [N] | [N] |
| Maintainability | [N] | [N] | [N] |
| Performance | [N] | [N] | [N] |
| Security | [N] | [N] | [N] |
| Readability | [N] | [N] | [N] |
| Testability | [N] | [N] | [N] |
| Extensibility | [N] | [N] | [N] |
| **TOTAL** | **[N]** | **[N]** | **[N]** |
```

---

## Step 3: Git Diff Coverage Check

Run:

```bash
git diff <target>..<current> --name-only
```

Compare the list of files changed in git to the list of files reviewed in Step 2.

Classify each git-diff file:
- **Reviewed** — was included in the Step 2 review
- **Not reviewed** — appeared in git diff but was not in the design document's scope

For "not reviewed" files: read them briefly and determine if they contain substantive
logic changes. Categorize:
- **Trivial** — auto-generated, formatting only, or mechanical rename → no action
- **Substantive** — contains logic changes → review them now using the same Step 2
  dimensions and append findings

Output:

```
## Step 3: Git Diff Coverage Check

### Files in Git Diff vs Files Reviewed

| File | In Review Scope | Classification |
|------|-----------------|----------------|
| [path] | YES | Reviewed |
| [path] | NO  | Trivial — [reason] |
| [path] | NO  | Substantive — reviewed below |

### Additional Findings from Unscoped Files
[findings using same format as Step 2, or "None."]
```

---

## Step 4: Save Report

Aggregate all findings from Steps 1, 2, and 3 into a final report and save it.

Determine the slug from the design document filename. If no design document,
use a slug from the current branch name.

Write **two files**:

```
RD/docs/delivery/[YYYY-MM-DD]-[type]-[slug]-review.md       ← English (primary)
RD/docs/delivery/[YYYY-MM-DD]-[type]-[slug]-review-cn.md    ← Chinese companion
```

Report structure:

```markdown
# Code Review Report

**Change**: [current branch] → [target branch]
**Change type**: [feature / bug fix]
**Design document**: [path or "T1 — none"]
**Date**: [today]

---

## Design Review Result

CRITICAL: [N] | WARNING: [N] | INFO: [N]

[full Step 1 output]

---

## Code Review Result

[full Step 2 output]

---

## Git Diff Coverage

[full Step 3 output]

---

## Overall Summary

| Dimension | CRITICAL | WARNING | INFO |
|-----------|----------|---------|------|
| Design document | [N] | [N] | [N] |
| Code quality | [N] | [N] | [N] |
| **TOTAL** | **[N]** | **[N]** | **[N]** |

### Verdict

[PASS / FAIL]

PASS: zero CRITICAL findings across all dimensions.
FAIL: list each CRITICAL finding that must be resolved before merge.
```

Then output to the conversation:

```
## Review Complete

Report (EN): RD/docs/delivery/[filename]-review.md
Report (CN): RD/docs/delivery/[filename]-review-cn.md

Design: PASSED / FAILED
Code: CRITICAL [N] | WARNING [N] | INFO [N]
Overall: PASS / FAIL

[If FAIL, list each CRITICAL finding as a numbered action item]
```

---

## Error Handling

| Situation | Action |
|-----------|--------|
| Design doc path does not exist | Stop; report the path and ask the user to verify |
| Target branch does not exist locally | Try `origin/<branch>`; if also not found, stop and ask |
| Design doc missing "modules / files affected" section | Flag as CRITICAL in design review; stop |
| Design doc passes but no source files found at listed paths | Report the discrepancy; attempt to locate files by grepping for module names |
| Git diff is empty | Report that no changes are found between the two branches; ask whether the correct branches were specified |
| A file in the design scope is deleted in git | Note the deletion; review whether the design accounted for it |
