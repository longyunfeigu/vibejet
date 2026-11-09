---
name: run-test
status: experimental
description: |
  Execute AutoTest E2E cases with Playwright (playwright-bdd). Supports tag filtering
  (smoke/regression/negative), module-scoped runs and single scenarios by Case ID.
  Feature files live in modules/{module}/{feature}/features/, steps in modules/{module}/{feature}/steps/.
  Reports: report/test-reports-{env}/playwright/ (HTML + results.json) and, when anything fails,
  report/test-results/failed-cases-{env}-*.csv.

  Use when the user says things like:
  - "run smoke tests" / "跑 smoke 测试"
  - "run the auth E2E tests" / "跑一下登录的 E2E"
  - "跑一下所有 Playwright 测试" / "run all tests"
  - "npm run test:auth:local"
  - "--tag smoke" / "--tag regression" / "--tag negative"
allowed-tools: |
  Bash(npx playwright*:*)
  Bash(npx bddgen*:*)
  Bash(npm run*:*)
  Read(*)
  Glob(*)
---

# Run Test

Working directory: `AutoTest/`. The app under test must be running first (`AutoTest/AGENTS.md`, 「前置」).

## Step 1: Parse User Input

Determine:
- **Scope**: specific scenario (Case ID), module, tag filter, or all
- **Env**: an environment name in `config/environments.json` (default `local`)
- **Tag filter**: `@smoke`, `@regression`, `@negative`, `@slow`

### npm commands (preferred)

| Request | Command |
|---------|---------|
| all modules | `npm run test:all:local` |
| smoke only | `npm run test:smoke:local` |
| auth module | `npm run test:auth:local` |
| home module | `npm run test:home:local` |
| generate specs only | `npm run bdd:gen` |

### Tag or single-scenario runs

```bash
E2E_ENV=local npm run bdd:gen && \
E2E_ENV=local HEADLESS=true npx playwright test --config config/playwright.config.ts --project=bdd --grep "@smoke"
# one case:
E2E_ENV=local HEADLESS=true npx playwright test --config config/playwright.config.ts --project=bdd --grep "@AUTH-LGN-002"
```

---

## Step 2: Verify Test Files Exist

| Required files |
|----------------|
| `modules/{module}/{feature}/features/*.feature` |
| `modules/{module}/{feature}/steps/*.steps.ts` |
| `modules/{module}/{feature}/pages/*.ts` |

If files are missing, tell the user and suggest generating them with the `prd-to-bdd` skill.

---

## Step 3: Execute

Run the command from Step 1. `core/runner/run-bdd.sh` regenerates the specs, runs Playwright, and writes the
failed-cases CSV when anything fails.

---

## Step 4: Report to User

```
Passed: N  Failed: N  Flaky: N
Report: report/test-reports-{env}/playwright/index.html
Failed cases: report/test-results/failed-cases-{env}-*.csv (only when something failed)
```

For each failure give the Case ID, the first error line, and whether it looks like a product bug or a test
problem; to repair test-side failures in a loop, use the `test-self-heal` skill.

> The voice-agent source also had an `agent-browser` strategy (an LLM driving a browser CLI command by
> command). It is not ported: the CLI is not installed here, and ad-hoc browser checks use the `web-access` skill.
