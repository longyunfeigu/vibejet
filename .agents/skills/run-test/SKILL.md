---
name: run-test
description: |
  Execute E2E test cases using Playwright (default) or agent-browser strategy.
  Supports tag-based filtering (smoke/regression/negative), module-scoped runs, and specific scenario runs.
  BDD feature files live in modules/{module}/features/, step definitions in modules/{module}/steps/.
  Reports: Playwright → report/test-results/, smoke report → report/test-reports-{env}/playwright/smoke-test-report-YYYYMMDD.md
  agent-browser "run all" uses a task list file to track progress and support resuming.

  Use when the user says things like:
  - "run smoke tests" / "跑 smoke 测试"
  - "run all regression tests for knowledge-base"
  - "执行 knowledge-base 的 BDD 测试"
  - "跑一下所有 Playwright 测试" / "run all tests"
  - "npm run test:kb:sg"
  - "npm run test:bdd"
  - "继续执行 agent-browser 测试" (resume interrupted run)
  - "--tag smoke" / "--tag regression" / "--tag negative"
allowed-tools: |
  Bash(npx playwright*:*)
  Bash(npm test:*)
  Bash(npm run*:*)
  Bash(agent-browser:*)
  Bash(mkdir:*)
  Read(*)
  Write(*)
  Glob(*)
---

# Run Test

## Step 1: Parse User Input

Determine:
- **Scope**: specific scenario, module, tag filter, or all
- **Strategy**: `playwright` (default) or `agent-browser` (only if explicitly requested)
- **Strategy**: BDD（所有新測試）via `npm run test:*` 命令
- **Tag filter**: `@smoke`, `@regression`, `@negative`, `@slow`
- **Resume**: if user says "继续" or "resume", check last run results

### npm 命令（首選）

| 用戶輸入 | 命令 |
|---------|------|
| 全量測試 (SG) | `npm run test:all:sg` |
| 全量測試 (UAT) | `npm run test:all:uat` |
| 全量測試 (DEV) | `npm run test:all:dev` |
| knowledge-base 模組 | `npm run test:kb:sg` |
| voice-agent 模組 | `npm run test:va:sg` |
| ai-simulation 模組 | `npm run test:ai:sg` |
| mcp-registry 模組 | `npm run test:mcp:sg` |
| whatsapp 模組 | `npm run test:wa:sg` |
| 所有 BDD | `npm run test:all` |
| 僅生成 spec | `npm run bdd:gen` |

### Tag 過濾運行

```bash
VOICE_AGENT_ENV=sg npm run bdd:gen && VOICE_AGENT_ENV=sg npx playwright test --config config/playwright.config.ts --project=bdd --grep @smoke
```

### Scope 解析

| 用戶輸入 | 命令 |
|---------|------|
| `@smoke` | `npm run test:all:sg -- --grep @smoke` |
| `knowledge-base` | `npm run test:kb:sg` |
| `all` | `npm run test:all:sg` |

---

## Step 2: Verify Test Files Exist

| Required files |
|----------------|
| `modules/{module}/features/*.feature` |
| `modules/{module}/steps/*.steps.ts` |
| `modules/{module}/pages/*.ts` |

If files missing, inform the user and suggest generating them with `test-case-generator` first.

---

## Step 3: Execute

### BDD Tests — All modules

```bash
npm run test:bdd
```

### BDD Tests — Specific module (if supported by config)

```bash
npx playwright test --project=bdd --config config/playwright.config.ts modules/{module}/features/
```

### Playwright BDD — Specific module

```bash
npm run test:kb:sg    # knowledge-base
npm run test:va:sg    # voice-agent
npm run test:ai:sg    # ai-simulation
npm run test:mcp:sg   # mcp-registry
npm run test:wa:sg    # whatsapp
```

### Playwright BDD — All modules

```bash
npm run test:all:sg
```

Report generated at `report/test-results/` (configured in `config/playwright.config.ts`).
After execution, tell the user to run `npm run test:report` to open the HTML report.

---

### agent-browser — Specific scenario

Read `modules/{module}/requirements/` for scenario context, then execute each `agent-browser` command via Bash **one by one**. Stop immediately on first failure.

**Resolve `{{BASE_URL}}` before execution:**
Before executing any command, check `config/environments.json` or env vars to get the `base_url` value.
If the env var `{MODULE_ENV_VAR}_BASE_URL` is set (e.g. `KNOWLEDGE_HUB_BASE_URL`), it takes priority.

**Session isolation (required):** Prepend `--session {module}-{scenario}` to **every** `agent-browser` command.

```bash
# At the end, always close the session:
agent-browser --session {module}-{scenario} close
```

The session name format: `{module}-{scenario}` (e.g., `knowledge-base-004-chunk-crud-success`).

After execution, write result to `report/test-reports-{env}/{module}/agent-browser/{scenario}/result.md` using `assets/result-template.md`.

---

### agent-browser — All tests (task list mode)

agent-browser execution consumes significant context. Use a task list file as a checkpoint to track progress and support resuming after context loss.

**Task list path:**
- Module scope: `report/test-reports-{env}/{module}/agent-browser/task-list.md`
- Global scope: `report/test-reports-{env}/agent-browser-all/task-list.md`

#### Starting a new run

1. Scan all available test cases:
   ```bash
   # Module scope
   ls modules/{module}/requirements/
   # Global scope
   find modules -name "*.feature" -path "*/features/*"
   ```
2. Create task list using `assets/agent-browser-task-list-template.md`, listing all scenarios as `pending`
3. Execute each scenario **in order**, one at a time:
   - Run the scenario (including `--session {module}-{scenario}` and `close` at the end)
   - **Immediately after each scenario**: update task list status (passed / failed)
   - Write the individual `result.md` for that scenario
4. When all tasks are done, delete the task list file and report final summary

#### Resuming an interrupted run

1. Read existing task list file
2. Find all `pending` tasks
3. Continue from the first pending task, following the same per-scenario flow
4. Update task list after each completion

**Key rule**: Always update the task list **before** moving to the next scenario, not at the end of all runs.

---

## Step 4: Report to User

**Playwright:**
```
Passed: N  Failed: N  Skipped: N
Report: report/test-results/
Run `npm run test:report` to open the HTML report.
```

**agent-browser (single):**
```
PASSED / FAILED at step N: {step description}
Report: report/test-reports-{env}/{module}/agent-browser/{scenario}/result.md
```

**agent-browser (all):**
```
Completed: N/Total  Passed: N  Failed: N
Individual reports: report/test-reports-{env}/{module}/agent-browser/{scenario}/result.md
```
Task list is deleted after all tests complete. If interrupted, task list remains for resuming.

## Assets

- `assets/result-template.md` — template for individual scenario result reports
- `assets/agent-browser-task-list-template.md` — template for agent-browser all-tests task list
