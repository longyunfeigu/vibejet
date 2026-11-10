---
name: vj
description: Route and execute Vibe Engineering work through the smallest reliable VJ delivery track. Use for “用 vj 做/处理/实现”, “走 vibe engineering workflow”, workflow selection, or when another vj skill needs to decide between a direct patch, bounded Story, and full Epic delivery.
---

# VJ Delivery Router

Choose the smallest track that can produce observable evidence without hiding risk. Read
`docs/reference/guides/ai-workflow.md` only when the selected track needs its detailed handoff.

## 1. Classify

| Track | Use when | Required artifacts |
|-------|----------|--------------------|
| **Patch** | Local bug or adjustment; behavior is clear; no strict trigger | Reproduction or explicit assertion, diff, verification evidence |
| **Story** | Bounded user-visible capability; normally 2-5 files or one frontend/backend slice; no strict trigger | Lightweight Intent Contract, execution steps, verification evidence |
| **Epic** | Multiple capabilities or bounded contexts, or any strict trigger | Epic/Story WHAT, reviewed execution pack, run state, evidence |

Strict triggers are defined once in `AGENTS.md` under **Plan 规范**. Do not copy the list here.
Ambiguity that changes behavior is strict until resolved.

## 2. Establish the two contracts

Before editing, state:

1. **Intent Contract**: requested outcome, in-scope behavior, explicit non-goals, observable done
   signals, and unresolved decisions.
2. **Execution Contract**: selected track/policy, write surface, verification commands, and whether
   commits are allowed.

Do not ask for confirmation when the request and reversible implementation are already clear.
Use one intent gate only when a product choice changes observable behavior. Use one execution gate
only for unresolved destructive, security, migration, external-side-effect, or other strict decisions.
An explicit user authorization satisfies the gate for already disclosed risks; it does not resolve an
unknown product decision.

## 3. Initialize run state

Create runtime state with:

```bash
python3 .agents/skills/_shared/scripts/workflow_state.py init \
  --name <slug> --source <prompt-or-story-path> --track <Patch|Story|Epic> \
  --policy <fast|strict> --commit-policy <enabled|disabled-by-user>
```

The returned `.vj/runs/.../run-state.json` is the execution-state source. Follow
`.agents/skills/_shared/runtime-contract.md` for tool adapters. User instructions such as “不要
commit” always set `disabled-by-user` and suppress every workflow commit step.

## 4. Execute the selected track

### Patch

Read the affected code and call sites, reproduce or define the failing assertion, make the narrow
change, run focused verification, then apply the repo review trigger. Do not create Epic/Story/Plan
documents.

### Story

Use `vj-feature` only if the capability needs a durable Story. Do not create a review pack by default.
Execute from the Story plus a concise in-session plan; run focused tests, affected-neighbor checks,
and the repo review trigger. Escalate to Epic when a strict trigger or cross-context dependency
appears.

### Epic

Use `vj-feature` or `vj-epic-story` to establish WHAT, then `vj-epic-plan`, `vj-plan-review`, and
`vj-work`. Run `workflow_doctor.py plan <pack> --for-execution` before code changes. Use `vj-test`
only when cross-task end-to-end risk justifies it.

## 5. Close the run

Transition `running -> verifying -> completed` only after externally observable evidence passes.
Record test, browser, lint, and review evidence with `workflow_state.py evidence`. A failed required
check transitions to `blocked`; never relabel it as completed. Product status remains in Epic
frontmatter (and standalone Story frontmatter when the format provides it) and is updated once
during closeout.

## Completion

- The selected track is no heavier than its risk requires.
- Required behavior has outcome evidence, not only document/lint compliance.
- No unplanned human gate or commit occurred.
- Run state validates and the user receives changed files, verification, and residual risks.
