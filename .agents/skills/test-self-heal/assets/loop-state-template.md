# Test Self-Heal Loop — State ({MODULE} / {ENV})

> Loop Engineering State/Memory. One file per (module, env). Append per round; never rewrite history.

## Intent
Drive module **{MODULE}** to all-green.
Test-side failures (waits/locators/isolation/flaky) auto-fixed; suspected real bugs reported, not patched.

## Stop Conditions
- Green (0 fail) → success
- No-progress: 2 consecutive rounds, failing set did not shrink → stop
- Max rounds: {ROUNDS} → stop
- Real bug classified → stop fixing that case, report

## Scope
- Env: {ENV}
- Module: {MODULE}  (run: `npm run test:{MODULE}:{ENV}`)
- Mode: {fix | dry-run}
- Feedback: `report/test-reports-{ENV}/playwright/results.json` + `report/test-results/failed-cases-{ENV}-*.csv`

## Round Log

### Round 0 — Pre-check
- bdd:gen: {pass/fail} | env reachable: {http} | auth: {valid / auto-relogin}

### Round 1
- passed / failed:
- failing set (Case IDs):
- triage: [Case ID → test-side|real-bug → action]
- fixes applied / files:
- verify (re-run + heal-verifier): [Case ID → genuine|overfit]

<!-- append further rounds below; do not edit earlier rounds -->

## Outcome
- stopped by:
- auto-fixed:
- real bugs (need human):
- remaining:
