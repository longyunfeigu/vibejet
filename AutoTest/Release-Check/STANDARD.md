# Release-Check guide standard

A guide is good enough when **the AI can test the change from this guide and `_shared/` alone, without asking anyone.** Items marked *(lint)* are checked by `npm run lint:release-check`; the rest by the AI review on the MR.

## 1. Hard rules (any violation blocks the merge)

### 1.1 Write only the behavior of this change
Write what this feature or this fix must do. Whether services start, whether they restart, generic errors in logs, database migrations, and deployment settings are service health and stay out of a guide. A log keyword tied to this specific bug may be written as an auxiliary signal.

### 1.2 No vague phrases *(lint: `vague-phrase`)*
"How to verify" and "Expected after fix" say **what can be seen**: exact status codes, fields, log lines, page text.

| Not acceptable | Acceptable |
|---|---|
| Works as expected. | Every item in `GET /agents` has `last_call_at`, an ISO-8601 time or `null`. |
| The page displays correctly. | The agent list has a new "Last call" column showing `-` for agents never called. |
| No errors. | During 20 consecutive saves the backend log contains no `QueuePool limit`. |

`works as expected`, `works correctly`, `displays correctly`, `no error(s)`, `功能正常`, `符合预期`, `显示正确`, `正常显示`, `无报错` in those two sections block the merge; they are fine in "Easy to misjudge".

### 1.3 At least one deterministic signal *(AI review)*
"How to verify" contains at least one signal a program can check: a field value, a status code, a database row, a log keyword, a number with a threshold. Pure judgment ("the reply sounds natural") comes with its criteria.

- **Text a model writes is not a signal.** A prompt that says "reply with X" does not make the model say X, so the same setup can say different words on two runs. Check a log line, a stored record, or an API field instead. Reply text may only be checked as "non-empty" or "does not contain X".
- **A count states its scope.** An expected row count ("the query returns 0") names the rows it covers, for example rows created before the migration, or rows of the objects this guide created. Other people keep creating data in the same environment.

### 1.4 A priority on every check item *(lint: `priority-tag`)*
"How to verify" is a numbered or bulleted list, and **every** item starts with a priority:

| Priority | What belongs here | If it fails |
|---|---|---|
| `[P0]` | the basic function of the change works / the bug is fixed | the guide fails |
| `[P1]` | main scenarios | the guide fails |
| `[P2]` | a minor issue that does not block or affect the main flow | recorded; does not decide whether the guide passes |

```markdown
## How to verify
1. [P0] `GET /api/v1/admin/model-slots` returns 200 and its keys are exactly ...
2. [P1] `PUT` a model for the QA tenant -> 200, the response ...
3. [P2] the 6 new cards have no temperature input ...
```

- Indented sub-items, group headings (such as `**A. List page**`), tables, and prose are not check items.
- Items under "Must not break" count as `[P1]` when untagged; an item that only needs recording is tagged `[P2]`; do not use `[P0]` there.
- A guide with no `[P0]` gets a lint warning: it checks no basic function.

### 1.5 A P0 runs as written *(lint: `p0-direct`, AI review)*
P0 items run on every environment the product is deployed to, so every `[P0]` item must:
- use only the test accounts, the standing fixtures in `_shared/fixtures.md`, or objects created on the spot and deleted afterwards;
- need no resource from a person: no real customer account, third-party quota, or account with special permissions;
- not stop, restart, or scale a service, not change platform-level configuration, and not touch real users' data (when "another account" is needed, name the second test account `e2e-fixture-user-b`);
- not depend on business traffic or long observation; each item finishes within minutes;
- be safe on production: read-only, or touching only the test accounts' own objects; at most 2 calls per item.

An item that cannot meet this is not a P0: make it P1, or drop it and attach developer evidence (unit tests, logs, screenshots) to the PR instead. A dependency on an extra service goes into `requires` (1.15) and does not make the item indirect. A P0 that cannot run during verification is recorded as "guide defective" and returned to the author; it is not waived (see `_shared/safety.md`).

### 1.6 Bug fixes show the old failure *(lint: `sections`)*
A bugfix guide states what the **old version** visibly did wrong (status code, log line, wrong value, call behavior). Verification runs on the new version only: the fix holds when that behavior no longer appears.

### 1.7 Self-contained *(lint: `not-self-contained`)*
Everything the AI needs is in the guide or in `_shared/`. No "ask X", "see the group chat", or "same as last time". "Test data and cleanup" names the test objects the guide needs; a standing fixture from `_shared/fixtures.md` (`e2e-fixture-…`) is referred to by name, with no create or cleanup steps, and must not be changed.

### 1.8 No environments or credentials *(lint: `hardcoded-env`)*
No environment names, hosts, IPs, accounts, passwords, or keys. Links to PRDs or Lark documents are fine.

### 1.9 Registered tools only *(lint: `unregistered-tool`)*
`tools` lists only names from `_shared/tools.md`. Register a new tool in `_shared/tools.md` first, in the same branch.

### 1.10 Honest safety level *(lint: `frontmatter`, `cost-estimate`)*
`safety` says what running the whole guide does: `readonly`, `writes-test-data`, or `costly`. A `costly` guide (LLM calls, paid third-party APIs) states `cost_estimate`, counting every call the guide asks for, including those in "Must not break". An estimate that says "no calls" while the guide places calls is flagged.

### 1.11 Do not decide verdicts *(lint: `verdict-override`)*
The four verdicts and when each applies are defined in `_shared/safety.md`; a guide does not redefine them. In "How to verify" and "Must not break", do not write "not applicable" / 「不适用」 — the verifier decides it by checking `services` and `requires` (1.15) against the environment. When an item needs a precondition (a configured key, a mode, a record owned by the test account), say how to create it with the test account; what the environment itself may lack (an extra service) goes into `requires`. Do not write "if missing, blocked by environment" or "do not create": whatever is missing is created (`_shared/safety.md`, "Test data and operating boundary").

### 1.12 Verify on the new version only *(lint: `reproduce-old`, AI review)*
Do not ask the verifier to reproduce the old bug, switch back to an old image, or build the old failure path before checking. Every item is a signal observable on the new version. "Behavior on old version" describes what used to happen; it is not a step. An item that can only be checked by recreating the old failure is rewritten or dropped.

### 1.13 Facts in "Entry points" are traceable *(AI review)*
Each endpoint, log keyword, page element or console line named in "Entry points" and "How to verify" comes from the code on the source branch, with one `file:line` reference per fact. Do not write them from memory.

Code that exists is not code the verifier can reach. For a page element, give the click path from a page in the left navigation (route, section, button that opens a drawer or dialog), and confirm the component is rendered on that route, not only defined. A component imported only by a dialog nothing opens, or a branch shown only for another user role, cannot be checked.

### 1.14 Keep other guides in step *(AI review)*
When the change removes or alters behavior that another guide in the same month folder (or a `regression: true` guide) describes, update that guide in the same branch or set `supersedes`.

### 1.15 Environment dependencies go into `requires` *(lint: `frontmatter`, AI review)*
Some features are not present in every environment: a service that is not deployed there (for vibejet today, the gRPC server), and, for products built on this template, a gray-release key, a model the gateway has not registered, or outbound calling. List such dependencies in the front-matter `requires`. Before running, the verifier checks them against the environment; a missing one makes the items that use it "not applicable", without asking anyone.

| Entry | Meaning | How the verifier checks |
|---|---|---|
| `gray:<key>` | the gray-release key exists in the environment (if the test account does not have it on, turn it on temporarily and restore it afterwards) | keys listed by the gray-release admin API |
| `model:<name fragment>` | the model catalog has a model whose name contains the fragment; when a family has several names, separate them with `\|` and any one is enough (quote it in YAML, e.g. `"model:audioe2e\|kausap"`) | LLM / realtime model catalog |
| `service:<workload>` | the service is deployed (a dependency outside `services`, e.g. `template-middleware-backend`) | `docker compose ps` or the process list |
| `outbound` | outbound calling is enabled in the environment | the organization's outbound switch and batch API |

When the whole guide depends on it, the front matter is enough; when only some items (or part of an item) do, mark those items or that part with `(requires: gray:xxx)` and list it in the front matter as well. A front-matter entry that is also marked in the body applies only where it is marked; one not marked anywhere applies to the whole guide. `requires` only says what the environment has; anything that can be created with the test account does not belong here.


## 2. Merge gate

Before a branch with runtime behavior is merged into `master` / `main`:
- the branch adds or updates its guide under `AutoTest/Release-Check/<YYYY-MM>/`, or one of its commits carries a `Release-Check: exempt <reason>` trailer (see README);
- the guide passes lint and the AI review. CI runs `npm run lint:release-check` in `AutoTest/` on every push, so any lint error fails the branch; the AI review is the `delivery-code-review` (or `review`) pass, which checks the *(AI review)* rules above.

## 3. Front matter

| Field | Required | Value |
|---|---|---|
| `type` | yes | `feature` / `bugfix` |
| `source_branch` | yes | full branch name, used to find your commits |
| `author` | yes | git author handle (lowercase, no spaces) |
| `services` | yes | service keys the change touches: `backend`, `frontend`, `grpc` |
| `safety` | yes | `readonly` / `writes-test-data` / `costly` |
| `risk` | yes | `high` (auth / ownership, DB migration, large change) / `medium` / `low` — how deep to test (see `_shared/safety.md`) |
| `regression` | optional | default `false`; `true` to keep this guide in every future verification |
| `tools` | yes | tool names from `_shared/tools.md` |
| `cost_estimate` | when `costly` | e.g. `3 calls` |
| `requires` | optional | environment dependencies, e.g. `[service:grpc]`; see 1.15 |
| `supersedes` | optional | path (relative to `Release-Check/`) of an older guide whose behavior you changed on purpose. Without it, your intended change is reported as a regression |

## 4. Lint rules

| Rule | Severity | Meaning |
|---|---|---|
| `frontmatter` | error | a front-matter field is missing or invalid; the file cannot be parsed |
| `sections` | error | a required section is missing or empty (only an HTML comment counts as empty) |
| `vague-phrase` | error | a vague phrase in "How to verify" or "Expected after fix" |
| `not-self-contained` | error | depends on information outside the guide |
| `hardcoded-env` | error | an IP, a `localhost:<port>` address, or a credential |
| `unregistered-tool` | error | a tool not registered in `_shared/tools.md` |
| `cost-estimate` | error | `costly` without `cost_estimate` |
| `supersedes` | error | `supersedes` points to a guide that does not exist |
| `path` | error | wrong folder, a guide folder not named `YYYY-MM`, or a file name not starting with the author |
| `unknown-heading` | warning | a level-2 heading not in the template; its content counts toward no section |
| `verdict-override` | error | "How to verify" or "Must not break" declares 「不适用」 / not applicable |
| `reproduce-old` | warning | "How to verify" or "Must not break" asks to reproduce the old bug or use the old version |
| `cost-mismatch` | warning | `cost_estimate` says no calls while `tools` has `ai-simulation-call` or the body places calls |
| `p0-direct` | error | a `[P0]` item stops a service, observes for a long time, relies on business traffic, or refers to "another account" without naming `e2e-fixture-user-b` (see 1.5) |
| `priority-tag` | error / warning | "How to verify" is not a list, or an item has a missing or invalid priority (error); no `[P0]` at all (warning) |
