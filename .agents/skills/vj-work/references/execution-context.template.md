# Epic {N} {名称} — Execution Context

> Generated/updated by `vj-work` Phase 1. This file is an execution cache, not a new source of truth.
> Source truth remains the plan, task docs, `docs/project/DESIGN.md`, `docs/project/api/`, `docs/project/data/`, `docs/project/ui/`, and repo-local layer skills.

## Mode Decision

- **Mode:** `{fast | strict}`
- **Reason:** `{strict triggers or fast rationale}`
- **Approval gate:** `{auto decision}`
- **Recording:** `{final-only | per-task}`
- **Commit granularity:** `{feature | wave | per-task}`

## Layer Coverage

- Backend: `{yes/no}` — source pointers: `{...}`
- Frontend: `{yes/no}` — source pointers: `{...}`
- Design: `{none/trivial/functional/critical}` — source pointers: `{...}`
- API contract: `{yes/no}` — source pointers: `{...}`
- Data model: `{yes/no}` — source pointers: `{...}`
- UI Surface Delta: `{none | present | fallback}` — source pointers: `{design.md UI Surface Delta, task-index.md lanes}`
- UI Catalog: `{none | present | fallback}` — source pointers: `{docs/project/ui/surfaces.md, docs/project/ui/routes.md}`

## UI Surface / Execution Lanes

> Fill for frontend epics. Source truth is `docs/project/ui/` catalog when present; otherwise `design.md` `UI Surface Delta` and `task-index.md` `Execution lanes / Frontend composition waves`.

| Screen ID | Route | Screen type | Primary Job | Covered Units | Regions | Information Priority | Richness Floor | Forbidden Patterns | API-for-UI / Data Contract | Frontend start condition | Screen done | Source |
|-----------|-------|-------------|-------------|---------------|---------|----------------------|----------------|--------------------|----------------------------|--------------------------|-------------|--------|
| `{screen-id}` | `{route}` | `{front-of-house/operational/mixed}` | `{job}` | `{U1,U2}` | `{regions}` | `{P0/P1/P2}` | `{minimum composition}` | `{forbidden}` | `{endpoints/fields/states/errors}` | `{contract stable condition}` | `{browser-verifiable done}` | `{docs/project/ui/... or design.md UI Surface Delta}` |

| Lane | Wave | Scope | Done signal |
|------|------|-------|-------------|
| `{contract/backend-api-capability/frontend-composition/e2e-polish}` | `{wave}` | `{scope}` | `{done}` |

## Epic Execution Checklist

> 10-20 high-priority constraints for this epic. Each item must be concrete, actionable, and cite a source pointer.
> This checklist is not a complete rulebook. If a Unit hits new risk or uncertainty, open the cited source section.

1. `{ID}` `{constraint}` — Source: `{path-or-doc-line}`
2. `{ID}` `{constraint}` — Source: `{path-or-doc-line}`

## Unit Context Packets

### T{NNN} — {Task title}

- **Unit:** `{U-ID}`
- **Task scope:** `{unit | partial-unit | screen-composition}`
- **Task doc:** `{docs/tasks/work/.../TNNN-...md}`
- **Wave:** `{wave}`
- **Depends:** `{depends}`
- **Execution lane:** `{contract | backend-api-capability | frontend-composition | e2e-polish | legacy-unit}`
- **Screen context:** `{none | Screen ID / route / primary job / role / covered sibling Units / regions / key states / API-for-UI / Screen done / catalog source}`
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
- **Screen verification commands:** `{commands/results}`
- **UI screenshot triggered:** `{yes/no, units}`
- **Review triggered:** `{yes/no, reason}`
- **Subagent triggered:** `{yes/no, units}`
- **User wait triggered:** `{yes/no, reason}`
- **Task/ledger writes:** `{count/timing}`
- **Blocked/retries:** `{summary}`
