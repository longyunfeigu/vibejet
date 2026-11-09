# Verification rules and safety

> Adapted for vibejet from the voice-agent original. The priority, depth and verdict rules are unchanged; the test-data boundary is rewritten for vibejet's test accounts and environments.

Release-Check is a set of **verification guides**: each one says how to verify one change and what counts as correct, and can be used in any environment at any time. Which environment it runs in and which check items are run is up to whoever uses it; this file only defines how check items are prioritized, how deep to test, how verdicts are reached, how test data is handled, and what verification must never do.

## Check item priorities

What each priority means and how to write it: `STANDARD.md` 1.4 (P0 basic function, P1 main scenarios, P2 minor issue that does not block the main flow; untagged "Must not break" items count as P1). "Depth hints" are not part of the verdict.

**Where items run**: verifying a month's changes runs every priority (P0, P1, P2, and "Must not break"); after any environment is upgraded, every `[P0]` of the month's guides and of the regression guides runs again there, plus the smoke items in `smoke.md`. That is why a P0 must run as written (`STANDARD.md` 1.5).

**How deep to test**, by the guide's `risk`:
- `high` (auth / ownership, database migration, large change): normal path + edge cases + error cases + neighboring features.
- `medium`: normal path + one error case + neighboring features.
- `low`: normal path.

## Verdicts

Each check item gets its own verdict, one of five: **pass · fail · blocked by environment** (the environment or the test facilities are broken or missing: test-account login fails, a dependency is down, a migration was not run, a test tool is not built yet. Whoever runs the environment fixes it and the item is rerun; it is never the guide author's problem) **· flaky** (still inconsistent after one isolated rerun) **· guide defective** (the item itself cannot be run as written; see the table below). There is no "skipped". Every verdict cites evidence (screenshots, raw API responses, log excerpts, query results); a verdict without evidence is void. A failure is triaged: product bug / environment problem / guide written wrong.

A change with no guide (and no `Release-Check: exempt` trailer) is recorded as "**no guide**" — a verdict about the change, not about a check item.

| Case | Verdict | Conditions and follow-up |
|---|---|---|
| The product behaves correctly; the guide's expectation is wrong | pass (noted "guide wrong") | The evidence must show why the product is right (PRD text, code line, or commit message); without that, it is a fail. Sent back to the guide's author |
| A neighboring problem outside what is being checked existed before this change and did not get worse (shown by code history or an old version) | pass (not introduced by this change) | **Neighboring problems only**: never applies to P0 items or to bugfix items that verify the fix itself — a bug that is not fixed is a fail. Reported to developers |
| A `[P0]` cannot run on the spot: it needs a person-supplied resource (real customer account, third-party quota), a stopped service, real traffic, or long observation, or its stated precondition cannot be created | guide defective | **Not waived, nobody is asked.** Returned to the author, listed separately in the report; left out of the combination |
| A P1, P2, or "Must not break" item is not tested this time | waived | **Only the verification owner decides**; reason stated; tested later. A P0 is never waived |
| The services the guide covers are not deployed in this environment, or a dependency listed in `requires` is absent here | not applicable | **Decided before running by checking the environment, nobody is asked**; a whole-guide dependency makes the guide not applicable, an item-level one only those items. Left out of the overall verdict |

**A guide's overall verdict** combines only P0, P1, and "Must not break" items (untagged ones count as P1): any fail → fail; otherwise any flaky → flaky; otherwise any blocked → blocked by environment; otherwise → pass. P2 results of any kind are only listed, never combined. Waived items are left out of the combination but stated: with waivers write "pass (N items waived)", with defective items "pass (N items guide defective)"; **when every P0 item is guide defective the guide cannot pass** — write "not verified (guide defective)". If every item is not applicable, the guide is "not applicable".

**Bugfix guides**: verify only the version under test; do not reproduce the bug on an old version. Follow "How to verify"; if the "Behavior on old version" does not appear and the items that check the fix pass, the fix is confirmed.

## Test data and operating boundary

The same in whichever environment you verify:
- Always act as the test accounts in `fixtures.md`: `e2e-fixture-user-a` for everything, and `e2e-fixture-user-b` whenever a guide needs "another account" (ownership, isolation, "a non-owner gets 404"). Their passwords come from the environment config (`AutoTest/config/environments.json`, never committed).
- You **may** create test objects (conversations, documents, files, agent configs, extra users) owned by a test account and named `e2e-<guide file name>-xxx`, and delete them at the end; report anything that cannot be deleted. Users cannot be deleted through the API, so prefer the two standing accounts over creating new ones.
- **Objects named `e2e-fixture-…` are standing fixtures**: never delete or edit them (no password or profile change). A check item that would change one builds a temporary `e2e-<guide file name>-xxx` object instead and deletes it at the end. If a standing fixture is missing from the environment, create it as `fixtures.md` describes.
- You **may not** read, change, or delete data that belongs to a real user, or change instance-level settings. **The test: if the action only affects objects owned by a test account, it is allowed.** Read-only queries that only look at counts or structure and export no user content may span users.
- **Whatever is missing, create it**: a conversation, document, agent config or account the guide needs is created on the spot as a temporary `e2e-` object (or a standing fixture is created per `fixtures.md`) and deleted afterwards. Missing test data is never a verdict: it is not "blocked by environment" and it is not skipped. Where a guide says "if missing, record blocked by environment" or "do not create", follow this rule instead and return that wording to the author.
- Only two things cannot be created on the spot: a feature the environment does not have (judged "not applicable" from `services` / `requires`), and anything that needs a platform-level change or a real external resource (a real OAuth provider account, a paid third-party key). The latter is a test-facility gap: record "blocked by environment" and name what is missing. A P0 may not depend on one.

### How to do it

- **Tokens**: `POST /api/v1/auth/login` (`backend/api/routes/auth.py:53`) with a test account returns `access_token`; send it as `Authorization: Bearer <token>`. Keep tokens in memory only; never print them, write them to disk outside the gitignored auth-state files, or put them in evidence; mask any JWT that appears in evidence.
- **Creating a missing test account**: `POST /api/v1/auth/register` (`backend/api/routes/auth.py:39`) with `username`, `email`, `password`.
- **Database**: only through the `db-readonly` tool (read-only transaction, 30 s timeout). Never connect with a write-capable client.
- **Logs**: read the backend's log output (`app-logs`); never change the log level or restart a service to get more logs.
- **Run items that change account-level settings last, on their own**, so they do not affect other checks running at the same time.
- **Login-state files** (the Playwright storage state holds tokens in plain text) stay in `AutoTest/config/auth-state-*.json`, which is gitignored, and never go into the evidence directory.

## Safety levels

A guide's `safety` describes what **running the whole guide** does:
- `readonly` — reads only.
- `writes-test-data` — creates data. Every created resource name starts with `e2e-` (ASCII only) and is deleted at the end; cleanup failures are reported, never ignored.
- `costly` — makes LLM calls or spends paid third-party quota. `cost_estimate` is mandatory. Default cap: **at most 20 LLM calls per guide per verification run**.

## Never

- Modify guides, product code, tests, or deployment configuration during verification.
- Run migrations, change environment variables, restart or redeploy services, or run any git operation on a server.
- Go beyond the "Test data and operating boundary" above.
- Use an admin or superuser account for anything a test account can do.
- Turn on test self-heal during verification.
