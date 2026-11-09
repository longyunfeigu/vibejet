---
name: test-self-heal
description: |
  Run a self-healing E2E test loop (Loop Engineering): run tests → read failures →
  triage against the known-pitfalls table → auto-fix test-side issues → re-run only the
  fixed cases to verify → repeat until green or a stop condition fires. Test-side problems
  (waits/locators/isolation/flaky) are auto-fixed; suspected real product bugs are reported, never patched.

  Use when the user says things like:
  - "自愈循环" / "self-heal" / "跑测试并自动修复失败"
  - "loop until green" / "一直跑到全绿" / "修到全过为止"
  - "跑 {模块} 自愈" / "run self-heal for knowledge-base"
  - "test-self-heal kb uat" / "/test-self-heal va uat --dry-run"
  - "有头模式跑自愈" / "self-heal --headed" / "无头跑" / "屋头模式"
  - "帮我盯着这个模块的测试，失败就修"

  Parameters (positional + flags):
  - {module}: kb | va | ai | mcp | wa | pn   (required)
  - {env}: sg | uat | dev                    (default: uat)
  - --rounds N: max loop rounds              (default: 3)
  - --dry-run: triage + report only, never modify code
  - --headed | --headless: browser visibility (default: headless; use --headed to watch the run / debug SSO login)
  - --workers N: parallel workers (default: 1; e.g. --workers 6 to parallelise — faster but can surface agent-state isolation flake)
allowed-tools: |
  Bash(npm run*:*)
  Bash(npx*:*)
  Bash(node*:*)
  Bash(git diff*:*)
  Bash(git stash*:*)
  Read(*)
  Write(*)
  Edit(*)
  Glob(*)
  Grep(*)
  Task(*)
---

# Test Self-Heal Loop

A Loop Engineering harness for E2E tests. You are the **loop engine**: you run the loop, observe
feedback, decide what to fix, and decide when to stop. Do NOT prompt the user between rounds — drive
the loop autonomously until a stop condition fires, then report.

**输出语言（CRITICAL）**：所有面向用户的过程信息——每轮进度播报、观察到的通过/失败、分诊结论、修复说明、最终报告——一律用**中文**呈现。每轮结束后给用户一句中文进度（如「第 2 轮：3 失败 → 分诊 2 个等待问题已修、1 个疑似真 bug，重跑验证中」）。本文件的指令可保持英文，但跑给用户看的内容用中文。

```
 Intent ──→ Action ──→ Observation ──→ Triage ──→ Adjustment ──→ Verify ─┐
 (green)    (run)      (results.json)  (classify)  (fix test-side)  (re-run)│
   ↑                                                                        │
   └──────────────  Stop: green / no-progress / max-rounds / real-bug  ─────┘
```

## Stop Conditions (HARD — never loop past these)

The single biggest LE failure mode is a loop that never converges and burns tokens. Enforce ALL:

1. **Green** — 0 failures → success, stop.
2. **No-progress (thrashing)** — 2 consecutive rounds where the failing-case set did not shrink → stop, report remaining.
3. **Max rounds** — reached `--rounds` (default 3) → stop, report remaining.
4. **Real bug** — a failure is classified as a product defect (not a test issue) → stop fixing THAT case, report it.

## Step 0: Parse Input + Pre-check

1. Parse `{module}`, `{env}`, `--rounds`, `--dry-run`, browser mode, and `--workers` from the user request. Map module alias via `core/runner/run-bdd.sh` (kb/va/ai/mcp/wa/pn).
   - Browser mode: default **headless**. `--headed`/"有头" → headed; `--headless`/"无头"/"屋头" → headless.
   - Workers: default **1**. `--workers N` parallelises (`playwright.config.ts` reads `parseInt(process.env.WORKERS ?? '1')`).
   - Build one **`RUN_PREFIX`** env string and reuse it for every test command below:
     - headless adds `HEADLESS=true `; headed adds nothing (`process.env.HEADLESS === 'true'`, default headed).
     - workers>1 adds `WORKERS=N `.
     - e.g. headless + 6 workers → `RUN_PREFIX = "HEADLESS=true WORKERS=6 "`; headed + 1 worker → `RUN_PREFIX = ""`.
   - Prefer **headless** for `/loop` unattended patrol (no popups, faster); **headed** for a first run / debugging SSO login. Prefer **`--workers 1`** when verifying a fix in Step 5 (parallelism can itself cause flake — see Triage).
2. Initialise State file from `assets/loop-state-template.md` → write to `report/le-loop-state-{module}-{env}.md`. Fill Intent, Stop Conditions, Scope.
3. Fast pre-check (cheap, avoids a wasted first round):
   ```bash
   npx bddgen test --config config/playwright.config.ts   # step matching + compile
   curl -s -o /dev/null -w "%{http_code}" "$(node -e "console.log(require('./config/environments.json').environments['{env}'].base_url)")"
   ```
   - `bddgen` non-zero → fix missing steps / type errors FIRST (that IS the loop's first repair).
   - env unreachable (not 2xx/3xx) → STOP, report environment blocker. Do not keep looping against a down env.
   - Auth state may be expired; `config/global-setup.ts` auto re-logs-in via SSO, so do not treat expired auth as a blocker.

## Step 1: Action — Run the module

Reuse the project's own runner (do not reinvent). Apply `RUN_PREFIX` from Step 0. Run in background for long modules:

```bash
${RUN_PREFIX}npm run test:{module}:{env} > report/le-round{N}.log 2>&1
# headless, 1 worker  → HEADLESS=true npm run test:kb:uat ...
# headless, 6 workers → HEADLESS=true WORKERS=6 npm run test:kb:uat ...
# headed,   1 worker  → npm run test:kb:uat ...
```

`run-bdd.sh` already calls `gen-failed-cases-csv.mjs` at the end, so a failed-cases CSV is emitted automatically.

## Step 2: Observation — Read structured feedback

Read failures from the JSON reporter (authoritative), not by scraping stdout:

```bash
# failing specs: title, tags (Case ID), first error message
node -e "const r=require('./report/test-reports-{env}/playwright/results.json'); /* walk suites→specs, collect ok=false */"
```

- Summarise: `passed / failed / flaky`. If 0 failed → go to Step 6 (success).
- Also read `report/test-results/failed-cases-{env}-*.csv` (latest) for the human-readable four-column failure list.
- Record the **failing-case set** (Case IDs) into the State file for this round — needed for the no-progress check.

## Step 3: Triage — classify each failure (the core decision)

For each failing case, classify as **test-side (fixable)** or **real-bug (report-only)**.
Match the error against the known-pitfalls table in `../../../CLAUDE.md` (section 四「常见陷阱与修复」):

| Symptom | Class | Action |
|---|---|---|
| `Missing step definitions` | test-side | add Given/When/Then in steps file |
| `Multiple definitions matched` | test-side | extract to `modules/common/steps/common.steps.ts` |
| `locator.* Timeout` / `click Timeout` / element not found | test-side | fix wait (`expect(...).toBeVisible`), fix locator priority |
| `Test timeout` on a long flow | test-side | add `@slow` tag to scenario |
| `409 Conflict` (resource exists) | test-side | add `deleteXxxIfExists()` + wait `not.toBeVisible` |
| flake (passes on isolated re-run) | test-side | apply isolation: dedicated `e2e-{module}-{caseid}` agent |
| **assertion on business value fails** (correct element, wrong/absent data; API 4xx/5xx from product) | **real-bug** | DO NOT patch the test — report it |

Decision rule for the ambiguous case: **if the test correctly drove the UI but the product produced the wrong
result, it is a real bug.** When you cannot confidently tell, re-run that one case in isolation once; still
failing on a value/assertion (not a wait/locator) → treat as real bug. False "real bug" is cheap; silently
"fixing" a test to pass over a real defect is the worst outcome.

**Concurrency check (only when this round ran with `--workers > 1`)**: parallel runs can fail for a reason that
has nothing to do with the test's logic — two cases sharing the same agent mutate its state at once (CLAUDE.md
零「并发执行时多个用例同时修改同一 agent 状态导致互相干扰」). Before classifying a parallel failure as test-side
or real-bug, **re-run that single case in isolation with `--workers 1`**:
- passes solo, failed under parallel → **isolation flake**: fix by giving the scenario a dedicated
  `e2e-{module}-{caseid}` agent (create at start, clean up at end), per CLAUDE.md 零节. Do NOT touch assertions.
- still fails solo → it is a genuine test-side issue or real bug; classify normally per the table above.

**Before any fix**, read the stability rules: `../prd-to-bdd/e2e-stability.md` (no `waitForTimeout`, locator
priority, wait-utils). Never introduce a hard wait to "fix" flake.

## Step 4: Adjustment — fix test-side issues

- `--dry-run`: skip all edits. Only record the triage verdict + proposed fix per case in the State file.
- Otherwise: fix only **test-side** cases. Edit POM / steps / feature under `modules/{module}/`.
- **CRITICAL (project rule)**: if you change a `.feature` expected result/step, sync the matching row in both
  `cases/manual-test-cases-en.csv` and `cases/manual-test-cases-cn.csv` (CLAUDE.md 零「修改 Feature 必须同步 Case CSV」).
- After edits, validate locally before re-running:
  ```bash
  npm run bdd:gen && npm run typecheck && npm run lint:bdd
  ```
- Record in the State file: per case → {verdict, what changed, files}.

## Step 5: Verify — re-run ONLY the fixed cases (anti-overfitting)

Do not re-run the whole module — re-run just the cases you touched, by Case ID tag:

Re-run the fixed cases with **`--workers 1`** (verification must be deterministic — don't let parallelism reintroduce flake):

```bash
VOICE_AGENT_ENV={env} npm run bdd:gen && \
HEADLESS={true|''} VOICE_AGENT_ENV={env} npx playwright test --config config/playwright.config.ts \
  --workers 1 --project={project} --grep "@{CASE_ID_1}|@{CASE_ID_2}"
```

Then dispatch the **heal-verifier** sub-agent (Task tool, `subagent_type: heal-verifier`) with the diff and the
re-run result, to judge **real fix vs overfit** (e.g. did the fix just loosen an assertion or add a blind wait?).
- verifier says overfit → revert that fix (`git diff` the file, restore), reclassify, count toward no-progress.
- verifier says genuine → keep.

Then loop back to **Step 1** for a full-module round (catches regressions the fix may have introduced), subject to Stop Conditions.

## Step 6: Report

Append a final block to the State file, and report to the user **in Chinese** using this template:

```
=== 测试自愈完成（{module} / {env}）===
执行轮次：N（停止原因：全绿 | 无进展 | 达上限 | 判定真bug）
开始：X 通过 / Y 失败
结束：X' 通过 / Y' 失败
已自动修复（测试侧）：[Case ID — 改了什么]
真 bug（仅报告，需人工 / RD 介入）：[Case ID — 症状 + 证据]
仍未解决：[Case ID — 原因]
State 文件：report/le-loop-state-{module}-{env}.md
```

If real bugs were found, make them the headline of the Chinese report — that is the loop's most valuable output.

## Triggering this loop automatically

- One-shot: `/test-self-heal kb uat`
- Scheduled (unattended patrol): `/loop 2h /test-self-heal kb uat` (Claude Code loops auto-stop after 3 days)
- After git pull / on a schedule: wire a hook in `settings.json` that triggers this skill; the hook only triggers — triage stays here.
