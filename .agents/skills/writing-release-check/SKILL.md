---
name: writing-release-check
description: Use when writing, updating or fixing a Release-Check guide under AutoTest/Release-Check/<release branch>/{feature,bugfix}/ -- an MR targeting DEV-* or HOTFIX-* needs one, or the MR review rejected a guide (STANDARD 1.3, 1.5, 1.11, 1.12, 1.13, 1.14, 1.15).
---

# Writing a Release-Check guide

> Chinese companion: [SKILL-cn.md](SKILL-cn.md)

## Overview

A guide is accepted only when it passes **lint and the AI review** on the MR. Lint checks format; the AI review checks the rules marked *(AI review)* in `AutoTest/Release-Check/STANDARD.md`. Passing lint locally does not mean the guide is done. This skill turns the reviewer's checklist into writing steps, so the first push passes.

Read before writing: `AutoTest/Release-Check/STANDARD.md` (section 1 is the hard rules), `_shared/safety.md`, `_shared/fixtures.md`, `_shared/tools.md`.

## Steps

### 1. Write the guide against the final code

Commit the code change first. Line numbers and endpoints come from the commit you push.

```bash
SRC=$(git branch --show-current)          # source_branch
TARGET=DEV-YYYYMMDD                        # the MR target branch = the guide folder
git diff --stat origin/$TARGET...HEAD      # what this MR changes
```

Copy `TEMPLATE-feature.md` or `TEMPLATE-bugfix.md` (or the `-cn` version) to `AutoTest/Release-Check/$TARGET/{feature|bugfix}/<gitlab-user>-<short-name>.md`. Name the file as `README.md` says. Fill in the front matter as STANDARD section 3 says; `tools` uses names from `_shared/tools.md` only.

### 2. Build a fact table before writing any prose

List every endpoint, log line, page element, console output, env var and DB column you will mention. Find each one in the code on the source branch and write down `fact → path:line`.

| Fact | How to find it |
|---|---|
| Endpoint | `git grep -nE '@router\.(get\|post\|put\|patch\|delete)\(' -- RD/<service>` and the `include_router(..., prefix=...)` in that service's `main.py`. Full path = prefix + decorator path. |
| Log keyword | `git grep -n '<words>' -- RD/<service>`. Copy the literal text from the logger call. |
| Page element | Look up the visible text or `aria-label` in the frontend source. |
| Env var / setting | Find the settings field and its default. |
| Expected value | Every value you promise ("returns `pregen`", "422", "key absent") comes from the code path: read the schema defaults, validators and serializers. A field with a default is never "missing" on read. |

**If you cannot find it in the code, it does not exist. Do not write it.** Never write an endpoint from memory or by analogy. For example, `POST /api/case-sets` does not exist; creating a case set is `POST /api/agents/{flow_id}/case-sets`.

### 3. Write "Entry points" and "How to verify" from that table

- Put the reference right after each fact: `` `POST /api/case-sets/{suite_id}/runs` (`RD/ai-simulation/backend/runs/routers/runs.py:129`) ``. Do this for every fact, including each endpoint in a list of several.
- Use repo-root paths. A bare `agents.py` or `App.tsx` matches several files, and a bare `:N` is unclear about which file it means.
- For each item in "How to verify" and "Must not break", check:

| Rule | The item must |
|---|---|
| 1.4 | start with `[P0]`, `[P1]` or `[P2]` |
| 1.2 / 1.3 | give exact signals (status code, field = value, log line, DB value, threshold). The guide has at least one signal a program can check. |
| 1.5 (P0 only) | use only Autotest, fixtures from `_shared/fixtures.md`, or objects created on the spot and deleted afterwards. It needs no phone numbers, WhatsApp numbers or real accounts, and no restarts, scaling or platform config. It does not wait for traffic, runs in minutes, and is safe on production (at most 2 calls). An item that cannot do all of this becomes `[P1]` or is removed. |
| 1.11 / 1.15 | say how to **create** each precondition in Autotest (`e2e-<file-name>-xxx`, deleted afterwards). Something the environment may lack (gray switch, model, outbound, extra service) goes into front-matter `requires` (`gray:` / `model:` / `service:` / `outbound`), plus `(requires: ...)` on the item. Do not write "not applicable", "if missing, mark as environment issue", "do not create" or "skip". |
| 1.12 | check only the new version. It does not reproduce the old bug, switch images, or build the old error path first. |
| 1.8 | contain no environment names, hosts, IPs, accounts or keys |
| 1.3 | not use text the model writes as the signal ("the reply says X"); check the routing / jump log, the selected task or outlet, or an API field. An expected row count names its scope (e.g. rows created before the migration) |
| 1.13 | for a page element, give the click path from a left-nav page and confirm the component renders on that route (not only that the text exists in the source) |
| 1.15 | list a gray key in `requires` when a page option only shows for orgs holding it, even if the code ships everywhere |

### 4. Keep other guides in step (1.14)

```bash
git grep -n -e '<endpoint or field you changed>' -- AutoTest/Release-Check/
```

If this change alters behavior that another guide describes (in `$TARGET/`, or any guide with `regression: true`), update that guide in this MR, or set `supersedes: <path>`.

### 5. Self-check before pushing

Fix every finding and rerun until all three are clean:

```bash
(cd AutoTest && npm run lint:release-check -- Release-Check/$TARGET/<type>/<file>.md)            # 0 errors
python3 .claude/skills/writing-release-check/scripts/check_refs.py AutoTest/Release-Check/$TARGET/<type>/<file>.md   # 0 errors
```

`check_refs.py` checks that every endpoint has a reference, that the referenced line defines that endpoint, and that every `file:line` resolves. For each warning, open the line and confirm it.

Then go through the table in step 3 again, item by item. **Every time you add a code commit, rerun `check_refs.py`**, because line numbers drift.

## Mistakes that got guides rejected

| Mistake | Fix |
|---|---|
| A line lists several endpoints, and only some have `file:line` | One reference per endpoint |
| Endpoint written from memory, so it does not exist | Fact table first (step 2) |
| Line numbers stale after more commits | Rerun `check_refs.py` after the last commit |
| "If missing, record as environment issue" with no `requires` | Say how to create the precondition, or declare `requires` |
| P0 needs a real phone number, traffic or a restart | Make it P1, or replace it with a self-contained check |
| "The reply contains `One moment.`" | The model does not repeat node instructions word for word; check the jump log or an API field (1.3) |
| Page element found in the source but not reachable (wrong section, a dialog nothing opens) | Give the click path and confirm it renders on that route (1.13) |
| "The query returns 0" while others keep creating rows | Scope the query, e.g. rows created before the migration (1.3) |
| The way to build a precondition does not build it (fallback path, unchanged tab not saved, prompt too short) | Trace the code path the step triggers before writing it (fallbacks, skipped unchanged tabs, length limits) and confirm it builds the precondition (1.13) |
| UI option behind a gray key, no `requires` | Add `gray:<key>` (1.15) |
