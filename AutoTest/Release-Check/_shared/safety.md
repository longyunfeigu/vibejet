# Verification rules and safety

> Chinese version: [safety-cn.md](safety-cn.md). Maintained by QA.

Release-Check is a set of **verification guides**: each one says how to verify one change and what counts as correct, and can be used in any environment at any time. Which environment it runs in and which check items are run is up to whoever uses it; this file only defines how check items are prioritized, how deep to test, how verdicts are reached, how test data is handled, and what verification must never do.

## Check item priorities

What each priority means and how to write it: `STANDARD.md` 1.4 (P0 basic function, P1 main scenarios, P2 minor issue that does not block the main flow; untagged "Must not break" items count as P1). "Depth hints" are not part of the verdict.

**Where items run**: UAT runs every priority (P0, P1, P2, and "Must not break"); each production environment runs every `[P0]` of this release's and the regression guides, plus the production smoke items in `smoke.md`. That is why a P0 must run as written (`STANDARD.md` 1.5).

**How deep to test**, by the guide's `risk`:
- `high` (call path, database migration, large change): normal path + edge cases + error cases + neighboring features + multiple languages.
- `medium`: normal path + one error case + neighboring features.
- `low`: normal path.

## Verdicts

Each check item gets its own verdict, one of five: **pass · fail · blocked by environment** (the environment or the test facilities are broken or missing: Autotest login fails, a dependency is down, a deployment step was not done, a test tool is not built yet. Operations or QA fix it and the item is rerun; it is never the guide author's problem) **· flaky** (still inconsistent after one isolated rerun) **· guide defective** (the item itself cannot be run as written; see the table below). There is no "skipped". Every verdict cites evidence (screenshots, raw API responses, log excerpts, query results); a verdict without evidence is void. A failure is triaged: product bug / environment problem / guide written wrong.

A change with no guide (and no exemption reason in its MR) is recorded as "**no guide**" — a verdict about the change, not about a check item.

| Case | Verdict | Conditions and follow-up |
|---|---|---|
| The product behaves correctly; the guide's expectation is wrong | pass (noted "guide wrong") | The evidence must show why the product is right (PRD text, code line, or MR description); without that, it is a fail. Sent back to the guide's author |
| A neighboring problem outside what is being checked existed before this change and did not get worse (shown by code history or an old version) | pass (not introduced by this change) | **Neighboring problems only**: never applies to P0 items or to bugfix items that verify the fix itself — a bug that is not fixed is a fail. Reported to developers |
| A `[P0]` cannot run on the spot: it needs a person-supplied resource (test number, real read-only account), a stopped service, business traffic, or long observation, or its stated precondition cannot be created | guide defective | **Not waived, QA is not asked.** Returned to the author, listed separately in the report; left out of the combination |
| A P1, P2, or "Must not break" item is not tested this time | waived | **Only QA decides**; reason stated; tested later. A P0 is never waived |
| The services the guide covers are not deployed in this environment, or a dependency listed in `requires` (gray-release key, model, service, outbound) is absent here | not applicable | **Decided before running by checking the environment, QA is not asked**; a whole-guide dependency makes the guide not applicable, an item-level one only those items. Left out of the overall verdict |

**A guide's overall verdict** combines only P0, P1, and "Must not break" items (untagged ones count as P1): any fail → fail; otherwise any flaky → flaky; otherwise any blocked → blocked by environment; otherwise → pass. P2 results of any kind are only listed, never combined. Waived items are left out of the combination but stated: with waivers write "pass (N items waived)", with defective items "pass (N items guide defective)"; **when every P0 item is guide defective the guide cannot pass** — write "not verified (guide defective)". If every item is not applicable, the guide is "not applicable".

**Bugfix guides**: verify only the version under test; do not reproduce the bug on an old version. Follow "How to verify"; if the "Behavior on old version" does not appear and the items that check the fix pass, the fix is confirmed.

## Test data and operating boundary

The same in whichever environment you verify:
- Always work in the **Autotest** test organization with the QA test account (the "QA test tenant" in guides means this organization).
- Inside the test organization you **may** create test objects (agents, flows, chat agents, test accounts, …), named `e2e-<guide file name>-xxx`, deleted at the end, with anything that cannot be deleted reported; you **may** also change that organization's own settings (such as its model slots or its gray-release switches) and restore them afterwards.
- **Objects named `e2e-fixture-…` are standing fixtures** (listed in `fixtures.md`): never delete or edit them. A guide that needs one refers to it by name; a check item that would change it (edit its config, publish it, switch its orchestration mode, …) builds a temporary object `e2e-<guide file name>-xxx` instead and deletes it at the end. If a standing fixture is missing from the environment, create it as `fixtures.md` describes; where the list says the environment has no such model, judge it "not applicable".
- **The second QA test organization, `AI Builder Sandbox 4`**: whenever a guide needs "another organization" (isolation, permissions, "other organizations are unaffected"), use it. Its operating boundary is exactly that of Autotest, and "test organization" in this section covers both. Objects it lacks (agents, accounts, ...) are created on the spot as temporary `e2e-` objects and deleted afterwards.
- You **may not** touch anything that affects other tenants: system-level or platform-level shared settings, or the data and settings of customer organizations and any other non-test organization. **The test: if the action only affects a test organization (Autotest or AI Builder Sandbox 4), it is allowed.**
- **Isolation and permission checks** (such as "another tenant cannot see / delete it" or "tenants outside the gray release are unaffected") use only the two test organizations: "another organization" is AI Builder Sandbox 4; "outside the gray release" can be simulated by temporarily turning off Autotest's own gray-release switch. Never try to read, write, or delete objects of customer organizations or any other non-test organization.
- Read-only queries that only look at counts or structure and export no customer content (such as migration completeness or connection statistics) may span tenants.
- Never touch customer tenants, agents, phone numbers, or recordings.
- A guide's "Test data and cleanup" names the test objects it needs.
- **Whatever is missing, create it**: an agent, flow, knowledge base, account, or call record the guide needs and the test organization lacks is created on the spot as a temporary `e2e-` object (or a standing fixture is created per `fixtures.md`) and deleted afterwards; a gray-release key is turned on temporarily per "How to do it". Missing test data is never a verdict: it is not "blocked by environment" and it is not skipped. Where a guide says "if missing, record blocked by environment" or "do not create", follow this rule instead and return that wording to the author.
- Only two things cannot be created on the spot: a feature the environment does not have (judged "not applicable" from `services` / `requires`), and anything that needs a platform-level change, another organization, or a real external resource (a WhatsApp test number, simulated outbound numbers). The latter is a test-facility gap: record "blocked by environment", name what is missing, and QA builds it. A P0 may not depend on one.

### How to do it

Before changing a test-organization setting, record its current state; restore it afterwards and read it back to compare. Never touch instance-level settings, other organizations, or existing users.
- **Organization gray-release switches**: use the product admin API `/api/v1/admin/gray-release`. If the only way is to edit the database or Kubernetes objects directly, stop and report a plan first.
- **Organization model slots**: save the results of the two generic GETs as a snapshot first, and restore from it afterwards (`updated_at` changes; every other field must match).
- **Temporary test accounts**: create an `e2e-` user under the Autotest organization in the identity system (zitadel) and grant roles through the product's permission API; afterwards revoke the roles, delete the user, and read back to confirm it is gone (404). The admin token may be read from `secrets.permission.zitadelPat` in the target environment's common-values: read that one key only (never pull the whole file into context), keep it in memory only, and never print it, write it to disk, or put it in evidence. The gateway caches a user's roles for about 5 minutes, so test a role change with a new account.
- **Run items that change organization-level settings last, on their own**, so they do not affect other checks running at the same time.
- **Voice calls** are placed server-side through ai-simulation; before placing one, confirm the agent's **published version** is the configuration under test.
- **Login-state files** (such as the `auth.json` a browser automation saves, which holds tokens in plain text) go in a temporary directory only you can read, never in the evidence directory, and are deleted at the end; mask any JWT or `access_token=` that appears in evidence.

## Safety levels

A guide's `safety` describes what **running the whole guide** does:
- `readonly` — reads only.
- `writes-test-data` — creates data. Every created resource name starts with `e2e-` (ASCII only) and
  is deleted at the end; cleanup failures are reported, never ignored.
- `costly` — places calls or spends LLM tokens. `cost_estimate` is mandatory. Default cap: **at most
  5 calls per guide per verification run** (QA may change this).

## Never

- Modify guides, product code, tests, or deployment configuration during verification.
- Deploy, change Helm values, run `kubectl apply/delete/edit/exec` that writes, or run any git operation on a remote server.
- Go beyond the "Test data and operating boundary" above.
- Do anything in the admin console (pages under `/admin` and `/api/v1/admin/...` APIs) that affects the whole platform, in any environment: only actions scoped to the selected test organization are allowed (such as that organization's model configuration, `icc.detect.system`, or adding a test organization to or removing it from an existing gray-release key). When unsure whether an action is platform-wide, treat it as platform-wide and only look.
- Turn on test self-heal during verification.
