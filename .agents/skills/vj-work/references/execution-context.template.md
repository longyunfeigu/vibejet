# Epic {N} {名称} — Execution Context

> Generated/updated by `vj-work` Phase 1. This file is an execution cache, not a new source of truth.
> Source truth remains the plan, task docs, `docs/project/DESIGN.md`, `docs/project/api/`, `docs/project/data/`, and repo-local layer skills.

## Mode Decision

- **Mode:** `{fast | strict}`
- **Reason:** `{strict triggers or fast rationale}`
- **Approval gate:** `{auto decision}`
- **Recording:** `{final-only | per-unit}`
- **Commit granularity:** `{feature | wave | per-unit}`

## Layer Coverage

- Backend: `{yes/no}` — source pointers: `{...}`
- Frontend: `{yes/no}` — source pointers: `{...}`
- Design: `{none/trivial/functional/critical}` — source pointers: `{...}`
- API contract: `{yes/no}` — source pointers: `{...}`
- Data model: `{yes/no}` — source pointers: `{...}`

## Epic Execution Checklist

> 10-20 high-priority constraints for this epic. Each item must be concrete, actionable, and cite a source pointer.
> This checklist is not a complete rulebook. If a Unit hits new risk or uncertainty, open the cited source section.

1. `{ID}` `{constraint}` — Source: `{path-or-doc-line}`
2. `{ID}` `{constraint}` — Source: `{path-or-doc-line}`

## Unit Context Packets

### T{NNN} — {Task title}

- **Unit:** `{U-ID}`
- **Task doc:** `{docs/tasks/work/.../TNNN-...md}`
- **Wave:** `{wave}`
- **Depends:** `{depends}`
- **Goal:** `{one-sentence goal}`
- **Acceptance / done signal:** `{observable done state + Verification}`
- **Target files:**
  - `{path}` — `{expected change}`
- **Pattern files:** max 1-3
  - `{path}` — `{pattern to follow}`
- **Relevant constraints:** max 5-10, source pointer required
  - `{ID}` `{constraint}` — Source: `{path-or-doc-line}`
- **Verification command:**
  - `{command}`
- **Non-goals:**
  - `{explicitly out of scope}`
- **Risk class:** `{low | medium | strict-trigger}` — `{reason}`
- **UI class:** `{none | trivial | functional | critical}`
- **Test policy:** `{test-first | test-with-implementation | verification-only}`
- **System-wide check:** `{none | direct-neighbors | risk-triggered-two-hop}`
- **Subagent handoff:** If delegated, pass this full packet explicitly. Do not rely on parent context.

## Final Execution Profile

> Fill during Phase 4 only. Do not update on every small step in fast mode.

- **Context files loaded:** `{paths}`
- **Unit verification commands:** `{commands/results}`
- **UI screenshot triggered:** `{yes/no, units}`
- **Review triggered:** `{yes/no, reason}`
- **Subagent triggered:** `{yes/no, units}`
- **User wait triggered:** `{yes/no, reason}`
- **Task/ledger writes:** `{count/timing}`
- **Blocked/retries:** `{summary}`
