---
name: prd-to-bdd
status: experimental
description: Use when generating test cases from delivery or PRD docs under docs/work/delivery or docs/product, when the user says "从交付文档生成用例" / "generate cases from delivery docs" / "prd to bdd", or provides a path under those directories. Also use when the user says "激活 pending 用例" / "activate pending" to activate previously generated pending cases.
---

# Delivery Docs → BDD Full Pipeline Skill

**Description**: Reads product requirements from `docs/product/` and delivery design/checklist documents from `docs/work/delivery/`, synthesizes business + technical context, then generates Chinese case docs (CSV) → English-only `.feature` files → Page Object + Step Definitions. Validates the full chain at each phase.

> **Feature language policy (CRITICAL)**: `.feature` files are **English-only**. Do NOT generate or maintain `.cn.feature` companions — they are no longer authored, and `lint:bdd` no longer checks feature bilingual sync. Case documentation lives only in `cases/manual-test-cases-cn.csv` (vibejet writes outputs in Chinese).

## Single Source of Truth (CRITICAL)

`prd-to-bdd` is the only authoritative workflow for:

- case generation standards
- execution-type decision (`Automated` / `Manual-Prod-Unsafe` / `Manual-Fault-Injection`)
- case-to-BDD conversion rules


---

## Key Design Principle — Delivery Docs 先于代码是正常状态

Delivery docs 描述交付意图、设计方案和验收清单，代码是实现。两者之间有时差，这是正常的。
本 skill 的输出因此分为两条路径：

```
Delivery doc 出来，代码已实现  →  写入  {module}-{feature}.feature（可执行）+ POM + Steps
Delivery doc 出来，代码未实现  →  写入  {module}-{feature}.pending.feature（不执行）+ csv 规划行
                              代码上线后 → 从 pending 移到主 feature + 补 POM + Steps
```

**Pending 文件命名规则**：
- `modules/{module}/{feature}/features/{module}-{feature}.pending.feature`（English，待激活）
- Playwright 配置已排除 `*.pending.feature`，不会被 CI 执行
- 不再生成 `.cn.feature` / `.pending.cn.feature` 中文副本——feature 文件仅英文

**激活触发语**：用户说 "激活 pending 用例" / "activate pending" / "代码上线了，激活用例" 时，执行下方 Activation Pipeline，而不是主 Pipeline。

> **通用错误模式 — 避免以下两种思维定势**:
>
> **1. Delivery doc 路径 ≠ 实现路径**
> Delivery doc 里写的 API 路径、组件名、字段名是**交付意图/设计意图**，不是已实现的接口。
> 永远不要把 delivery doc 里的路径直接用于测试用例——应该从代码出发，找实际实现。
> 调试路径错误时，正确顺序是：
> - 前端组件 → 找实际 API 调用（`fetchWithAuth(url)`）
> - `apiClient` → 找完整 endpoint URL
> - 后端 `main.py` → 确认路由是否已注册
>
> **2. 功能未实现时应测什么**
> 当 delivery doc 描述的功能尚未实现时，不是跳过测试，也不是测 delivery doc 里的规划路径——
> 而是找**当前已实现的同类功能**，测它。
> 例如：delivery doc 描述了未来的 `agentic-run` 接口，但当前已实现的是
> `generate-greeting-evaluation` 接口——应该测后者，不是前者。
> 未来功能放 `pending.feature`，已有功能放主 feature 文件。

---

## Pipeline Overview

```
docs/product/{prd}.md + docs/work/delivery/{YYYY-MM}/{DD-type-slug}/design.md
        ↓  Phase 1  合并业务需求与技术设计 → 提炼场景 → 追加 csv 行
modules/{module}/{feature}/cases/manual-test-cases-cn.csv
        ↓  Phase 2  读 csv 用例行 → 转换为 Gherkin 场景（仅英文 feature）
modules/{module}/{feature}/features/{module}-{feature}.feature
        ↓  Phase 3  读 feature → 补 Page Object + Steps
modules/{module}/{feature}/pages/{FeatureName}Page.ts
modules/{module}/{feature}/steps/{module}-{feature}.steps.ts
        ↓  Phase 4
npm run bdd:gen && npm run typecheck && npm run lint:bdd
        ↓  Phase 5  重算自动化覆盖率
npm run coverage
```

## Execution Rule — 引用文件必须先读后做 (CRITICAL)

本 skill 把详细规范拆到了同目录的引用文件。**任何 Phase 标注了 `必读 xxx.md` 时,你必须先用 Read 工具读取该文件,再开始该 Phase 的工作——不得凭记忆或推测跳过。** 引用文件清单:

| 文件 | 触发 Phase |
|---|---|
| [`case-generate.md`](./case-generate.md) | Gate A / Phase 1(用例设计四法 + 封装规则 P1–P3 + 覆盖审计表) |
| [`test-data-strategy.md`](./test-data-strategy.md) | Phase 1.4 执行方式判断 / Phase 3 写 POM/Steps |
| [`e2e-stability.md`](./e2e-stability.md) | Phase 3 写或修 POM/Steps |
| [`activation.md`](./activation.md) | 用户说"激活 pending"时(另一条工作流) |

## Dual-Core Gates (CRITICAL)

This skill must satisfy two goals at the same time:

1. Expert-level test case quality (High-Value QA Analysis)
2. Stable BDD executability

Neither goal is optional.

Before Phase 2 (BDD conversion), ensure all three gates pass:

- **Gate A - Case Quality**: You MUST act as a Senior Testing Expert. Apply the formal test-design techniques in **[`case-generate.md`](./case-generate.md)** (equivalence partitioning, boundary-value analysis, decision tables, error guessing) to systematically derive **test points**, then package test points into cases using the **Case Packaging rules P1–P3** in the same file — one test point is NOT automatically one case (same-flow data variants merge into one parameterized case; consecutive checkpoints on one user journey merge into one multi-layer-assertion case). Gate A's required output artifact is the **Coverage Audit table** (format in `case-generate.md` §6): the gate fails if any acceptance criterion or coverage dimension maps to neither a Case ID nor an explicit N/A justification. Do not just test the happy path. Coverage MUST explicitly include:
  - **State Transitions**: Test how entities move between states (e.g., Draft -> Published -> Deleted).
  - **Permission Boundaries**: Test access control (Admin vs. Read-Only user vs. Unauthorized).
  - **Data Boundary Conditions**: Test empty states, max limits, and invalid inputs.
  - **Error States & Recovery**: Test how the system handles and recovers from expected failures.
- **Gate B - Execution Decision**: every case has an explicit execution type (`Automated`, `Manual-Prod-Unsafe`, or `Manual-Fault-Injection`) with rationale.
- **Gate C - Traceability**: each scenario in feature files can be traced back to exactly one Case ID row.

---

## Phase 1 — Read PRD + Delivery Docs → Generate Case Docs (Chinese)

### 1.1 Locate and Synthesize Source Docs (PRD + Delivery)
- If the user provides a file path under `docs/product/` or `docs/work/delivery/`, read it directly.
- If only one side is provided, search the other directory for the corresponding doc by feature/bugfix keywords.
- Read both sources when available:
  - **Business truth (PRD)**: `docs/product/*.md` for user stories, business goals, acceptance criteria, and business rules.
  - **Technical truth (Delivery)**: `docs/work/delivery/**/*.md` for UI components, routes/APIs, checklist/review constraints, and implementation intent.
- vibejet writes delivery docs once, in Chinese; read them directly.
- If multiple files exist for one delivery item:
  - PRD side: prefer primary requirement file + acceptance addendum
  - Delivery side: `design.md` first, then `checklist.md`, then `review.md`
- Extract and synthesize:
  - **Source document set**: list every PRD and Delivery file used.
  - **Business value and user flows**: primarily from PRD.
  - **Acceptance criteria**: primarily from PRD, constrained by delivery checklist.
  - **UI elements and API endpoints**: primarily from delivery docs.
  - **Edge cases**: synthesized from PRD business rules + delivery error handling.

**CRITICAL CONSTRAINT FOR PHASE 1:**
Phase 1 is strictly for **Business Analysis and QA Design**. You MUST NOT use `grep`, `find`, or any other tool to search the codebase for implementations or existing steps during Phase 1. Focus entirely on designing high-value test cases based on the documents. The Implementation Gate check belongs exclusively to Phase 2.0. *(Exception: You may use `grep` and `find` explicitly as instructed in Phase 1.2 Step 3 ONLY for module mapping resolution).*

**CRITICAL: Before moving to 1.2, you MUST output a QA Analysis Matrix:**
1. List all source files used (PRD + Delivery).
2. Summarize core business value and acceptance criteria from PRD.
3. Identify exact URL paths/API endpoints/components projected in the delivery docs.
4. Output the **Coverage Audit table** (format in [`case-generate.md`](./case-generate.md) §6): every requirement change point / acceptance criterion × Gate A dimension (Happy Path, State Transitions, Permissions, Boundaries, Error Recovery) mapped to planned Case IDs, with an explicit one-line N/A justification for any empty dimension. For each dimension, derive test points using the four techniques (equivalence partitioning, boundary-value analysis, decision tables, error guessing), then package test points into cases with rules P1–P3 — run the P1 self-check (two titles differing only by a noun = merge) before finalizing the list.

### 1.2 Determine module mapping

**Step 1 — Check the delivery docs for an explicit module keyword**

Future delivery docs may include a line like `**AutoTest Module**: auth` in their frontmatter or header.
If present, use it directly and skip Steps 2–3.

**Step 2 — Use the static mapping table**

| Product Area | AutoTest Module |
|---|---|
| Login / registration / session | `auth` |
| Home dashboard | `home` |

Conversations, documents, files and agent configs have no module yet; the first feature that needs one creates it.

**Step 3 — If still ambiguous, search the codebase**

When the delivery doc's product area does not obviously match the table above, resolve the module
by inspecting the source code. Examples:

```bash
# Find which backend route / application service owns the feature
grep -rln "{keyword}" backend/api/routes backend/application --include="*.py"

# Find the frontend feature folder
ls frontend/src/features/
grep -rln "{keyword}" frontend/src/features frontend/src/routes

# Cross-reference existing AutoTest step files for related keywords
grep -r "{keyword}" modules/ --include="*.ts" -l
```

Map the owning backend / frontend area to the AutoTest module using the table above or create a new
module only when no existing module is a reasonable fit.

If none match even after codebase inspection, create a new module directory following the standard structure.

### 1.2.5 Determine feature directory (CRITICAL)

Every delivery doc maps to a **feature directory** inside the module. Files are created at:

```
modules/{module}/{feature}/
├── cases/      ← CSV test case doc (Chinese: manual-test-cases-cn.csv)
├── features/   ← .feature (English-only; no .cn.feature)
├── pages/      ← Page Object class
└── steps/      ← Step Definitions
```

**Existing modules**: `auth` (feature `login`) and `home` (feature `dashboard`). New features go as sibling feature directories under their module, e.g. `modules/auth/register/`.

**Naming rules for `{feature}`:**
- Derive from the delivery doc filename: strip leading date prefix, take the meaningful slug
  - `260319-asr-hotwords.md` → `hotwords`
  - `260319-global-exception-handling-phase1.md` → `fallback-rules`
  - `260305-shared-link-demo-upgrade.md` → `shared-link`
- Use kebab-case, 1–3 words, no module name prefix
- If the delivery doc covers a broad area with no clear slug, use the primary feature keyword from the PRD title

**Check for an existing directory first:**
```bash
ls modules/{module}/
```
If a directory with the same feature already exists, append to it rather than creating a duplicate.

### 1.3 Append cases to the feature CSV files (CRITICAL)

> **Idempotency Check (防重复检查)**:
> Before generating any new scenarios, you MUST read the existing `modules/{module}/{feature}/cases/manual-test-cases-cn.csv` (if it exists).
> Compare your planned scenarios with the existing rows (check the `Requirement/Bug ID` and `Scenario Title` columns).
> - If a scenario is already fully covered in the CSV, **skip it**.
> - Only generate and append NEW cases that represent missing coverage or recent updates in the source documents.
> - If ALL planned scenarios already exist in the CSV, stop the pipeline and report: "All scenarios are already covered. No new cases generated."

Case documentation lives in **CSV** format, NOT markdown. Each feature directory has exactly one file, in Chinese, with the CN header row:
- `modules/{module}/{feature}/cases/manual-test-cases-cn.csv`
  **Columns (16, in order)** (the file uses the CN names):

| # | EN Column | CN Column |
|---|-----------|-----------|
| 1 | Case ID | 用例编号 |
| 2 | Requirement/Bug ID **(MANDATORY)** | 需求/缺陷编号 **(必填)** |
| 3 | Module | 模块 |
| 4 | Feature | 功能点 |
| 5 | Scenario Title | 场景标题 |
| 6 | Case Type | 用例类型 |
| 7 | Priority | 优先级 |
| 8 | Execution Type | 执行方式 |
| 9 | Preconditions | 前置条件 |
| 10 | Test Data | 测试数据 |
| 11 | Steps | 测试步骤 |
| 12 | Expected Result | 预期结果 |
| 13 | Post-cleanup | 后置清理 |
| 14 | BDD Tag | BDD 标签 |
| 15 | Owner | 负责人 |
| 16 | Notes | 备注 |

**Requirement/Bug ID (MANDATORY — never leave column 2 empty)**:
Every case row MUST carry a source identifier in column 2. It traces the case
back to what it covers and is used by the Idempotency Check above to dedupe.
Derive the value, in priority order:
1. **Delivery doc** — the source folder name under `docs/work/delivery/YYYY-MM/`,
   written as `YYYY-MM-DD-<slug>` (e.g. `2026-05-27-feature-template-middleware-voice-agent-orchestration`,
   `2026-05-22-bugfix-fallbacktts-streaming-ttfb`).
2. **Product requirement** — the requirement filename stem under
   `docs/product/` (e.g. `prd-auth`)
   when the case derives from a PRD rather than a dated delivery doc.
3. **Bug/ticket ID** — the tracker ID (e.g. `UER-01`) for bug-driven cases.

For foundational/baseline cases with no dated delivery doc, use the canonical
product-area PRD stem (`prod-*`). If no source can be identified, STOP and ask
the user — do NOT leave it blank. One source ID may be shared across all cases
generated from the same doc.

**Case ID format (MANDATORY)**: `{MODULE}-{FEATURE_CODE}-{NNN}`
- `MODULE`: product/module code (`AUTH`, `HOME`, ...)
- `FEATURE_CODE`: **3-5 uppercase letters**, human-recognizable, derived from feature domain (no opaque numeric fragment like `AE01`)
- `NNN`: 3-digit sequence, zero-padded (`001`, `002`, ...)

Examples:
- `VA-AEL-001` (`audio-e2e-latency`)
- `VA-CSL-002` (`connection-latency` / call setup latency)
- `VA-CHS-001` (`call-history-source`)
- `VA-SHL-001` (`shared-link`)

**Forbidden patterns**:
- `VA-XX01-001` (opaque + numeric fragment)
- `VA-XY4-001` (legacy mixed code + number)
- `VA-XY1-003` (legacy short code + number)

**vibejet feature code registry (use these exact codes; add a line when you create a feature):**
- `AUTH-LGN` = `auth/login`
- `HOME-DSH` = `home/dashboard`

> The Case ID in the csv is the tracking ID. The corresponding BDD scenario gets a `@{CASE_ID}` tag (e.g., `@VA-SHL-001`). Record the Case ID tag in the **BDD Tag** column (column 14) alongside the execution tag (e.g., `@VA-SHL-001 @smoke`).

**Test Data column for parameterized cases (Rule P1)**: when a case merges same-flow data variants per Case Packaging Rule P1 (`case-generate.md` §5), column 10 (Test Data) MUST enumerate the variant matrix (e.g. `provider ∈ {Deepgram, Cartesia, ElevenLabs, WIZ}`). Phase 2 converts such a row into a single `Scenario Outline` with one `Examples` row per variant.

**Case Type values** (EN/CN): `Smoke/冒烟`, `Regression/回归`, `Runtime/Slow/回归`, `Negative/负向`  
**Execution Type values** — canonical 3-value vocabulary enforced by `npm run lint:bdd`; vibejet's case file is Chinese, so use the CN values:

| File | Automated | Manual (prod-unsafe / hard-to-observe) | Manual (fault injection) |
|------|-----------|----------------------------------------|--------------------------|
| `manual-test-cases-cn.csv` | `自动化测试` | `手工测试-产线高危` | `手工测试-故障注入` |

- `Automated` / `自动化测试`: standard UI/API flows automatable via Playwright
- `Manual-Prod-Unsafe` / `手工测试-产线高危`: mutates shared/global/cross-env state (upload/publish/taxonomy/global config), needs physical audio/video or complex visual verification, RBAC accounts not provisioned in CI, or 3rd-party auth outside our control
- `Manual-Fault-Injection` / `手工测试-故障注入`: requires injecting a failure or unavailable dependency (wrong endpoint URL, revoked DB grant, upstream timeout) that CI cannot safely and deterministically produce

> Legacy values `AutoTest` / `Manual` / `手工测试` are INVALID — lint:bdd rejects them.

> **Mindset Shift: Design for the User, not for Playwright (CRITICAL)**
> Do NOT restrict your test case generation to only what Playwright can automate. You must generate a comprehensive test suite that covers ALL business value, edge cases, and user flows. Mark the hard-to-automate scenarios as `Manual-Prod-Unsafe/手工测试-产线高危` or `Manual-Fault-Injection/手工测试-故障注入`. They are just as valuable.

### 1.4 Execution-Type Decision Matrix (MUST)

> Before scoring, read the Three-Tier data classification in [`test-data-strategy.md`](./test-data-strategy.md):
> "Legacy / High-Cost" data (un-rebuildable via API, or too flaky/expensive) MUST be classified
> `Manual` here regardless of score. The classification directly drives this AutoTest/Manual decision.

Score each case from 0-2 on each dimension:

- Repeatability in CI
- Observability of expected results
- Environment control level
- Data setup and cleanup complexity
- Flake risk
- Maintenance cost

Total score range: 0-12. Decision rule:

- 4-12 → `Automated` (EN) / `自动化测试` (CN)
- 0-3 → Manual. Pick the flavor:
  - needs an injected failure / unavailable dependency → `Manual-Fault-Injection` (EN) / `手工测试-故障注入` (CN)
  - everything else (shared-state mutation, audio/visual verification, missing RBAC accounts, 3rd-party auth) → `Manual-Prod-Unsafe` (EN) / `手工测试-产线高危` (CN)

For non-`Automated` cases, Notes must include:

- Why full automation is not suitable now
- What manual signal must be verified
- What condition enables future migration to automation

**How to append**:
1. If `modules/{module}/{feature}/cases/` does not exist yet, create it with `mkdir -p`.
2. **Compute the next Case ID defensively** — do NOT just read the last line (trailing blank lines, comment rows, or a concurrent edit will break it). Parse ALL rows, filter empties, collect every existing Case ID for this `{FEATURE_CODE}`, take `max(sequence) + 1`, and print the full ID list as a sanity check before appending. (Same approach as Phase 2.2's "find next Case ID".) If the file doesn't exist, start at `001`.
3. Create a temporary python script (e.g., `tmp_append_cases.py` in the workspace root) using the `csv` module to append new rows — do NOT overwrite existing rows. Write the rows to the CN file. **Always use the `csv` module (never naked string concatenation) — test steps contain commas/quotes/newlines that only proper CSV quoting handles safely.** If you prefer Node over Python, use a real CSV library (`csv-stringify`/`papaparse`), not `fs` string append.
4. Execute the script via `run_shell_command` and then delete the script.

```python
import csv

def collect_existing_ids(filepath, feature_code):
    """Defensive next-ID: scan all non-empty rows, not just the last line."""
    try:
        with open(filepath, newline='', encoding='utf-8') as f:
            rows = [r for r in csv.reader(f) if r and r[0]]
    except FileNotFoundError:
        return []
    return [r[0] for r in rows if r[0].startswith(f"{feature_code}") or "-" in r[0]]

def append_cases(filepath, rows):
    with open(filepath, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow(row)
```

---

## Phase 2 — Cases (csv) → Feature Files (English-only)

### 2.0 Verify the feature is implemented (CRITICAL — do this before writing feature files)

Before converting CSV scenarios to `.feature` scenarios, verify that the backend API routes and frontend components described in the delivery docs actually exist in the codebase. This determines whether you write to the active or pending feature file.

```bash
# Backend: is the route registered? (routes live in backend/api/routes, prefixes in backend/main.py)
grep -rn "{api-path-keyword}" backend/api/routes --include="*.py"
grep -n "include_router" backend/main.py

# Frontend: does the component exist? (source files, not tests)
find frontend/src -name "{ComponentName}.tsx" 2>/dev/null
find frontend/src -type f \( -name "*.tsx" -o -name "*.ts" \) -not -name "*.test.*" | xargs grep -l "{feature-keyword}" 2>/dev/null | head -5
```

> **Avoid false positives (CRITICAL)**: a broad keyword (`status`, `update`, `config`) over-matches and wrongly marks a pending feature as implemented — you then waste effort writing POM/Steps for code that doesn't exist. Do NOT conclude "implemented" from hit count alone:
> - Prefer a specific signature over a generic word: the exact route path string (`"/api/v1/agents/{id}/hotwords"`), the registered router include in `main.py`, or the exact component name from the delivery doc.
> - If grep returns many hits, open the top files and confirm they are the **specific** endpoint/component described in THIS delivery doc — not a namesake elsewhere.
> - When you cannot confirm with confidence, treat the feature as NOT implemented and write to `.pending.feature` (false-negative is cheap; false-positive costs a red test run).

| Code status | Write to (English-only) |
|---|---|
| Feature implemented in codebase | `modules/{module}/{feature}/features/{module}-{feature}.feature` (append) |
| Feature NOT yet implemented | `modules/{module}/{feature}/features/{module}-{feature}.pending.feature` (append/create) |

**If the feature is NOT implemented**:
- Still generate the scenarios, but append them to the `.pending.feature` file.
- Add a comment block above new pending scenarios: `# Delivery doc: {delivery-doc-filename} — activation gate: {grep command}`
- **Do NOT create** POM methods or step definitions in Phase 3.
- Add a note in the Notes column (col 16) of the csv: `Implementation pending — feature not yet in codebase`.

**入口**：读取 Phase 1 写入的 csv 用例行，逐行转换为 Gherkin 场景。
不要再次从 delivery docs 直接推导 feature——feature 内容必须**与 csv 用例一一对应**：
- 每个 csv 行 → 一个 Scenario；若该行「Test Data」列含变体矩阵（Rule P1 合并的参数化用例）→ 一个 `Scenario Outline` + `Examples` 表（每个变体一行 Examples）
- BDD Tag 列 → 场景标签（`@smoke` / `@regression` / `@negative` / `@slow`）
- Scenario Title 列 → Scenario 标题
- Steps 列 → When/And 步骤
- Expected Result 列 → Then 断言

**输出路径**（feature 目录结构，仅英文）：
- 英文主文件：`modules/{module}/{feature}/features/{module}-{feature}.feature` (或 pending)
- 不再生成 `.cn.feature` 中文伴随文件。

如果目录不存在，先 `mkdir -p modules/{module}/{feature}/features/`。

```python
# 读取新增的用例行（仅筛选适合自动化的用例生成 feature）
import csv
new_rows = []
# new_case_ids should be collected from Phase 1 append result, e.g. {"VA-SHL-001", "VA-SHL-002"}
new_case_ids = set(...)
with open('modules/{module}/{feature}/cases/manual-test-cases-cn.csv', newline='', encoding='utf-8') as f:
    reader = csv.reader(f)
    next(reader)  # skip header
    for row in reader:
        case_id = row[0] if row else ''
        exec_type = row[7] if len(row) > 7 else ''
        # Filter by newly added Case IDs using a tracked start marker, not lexical string compare
        if case_id in new_case_ids and exec_type in ['Automated', '自动化测试']:
            new_rows.append(row)
```

### 2.1 Rules (CRITICAL)
- **Generate Gherkin scenarios only for rows where "Execution Type" is `自动化测试`.** Manual cases (`Manual-Prod-Unsafe` / `Manual-Fault-Injection`) must stay in the CSV file as documentation and MUST NOT be written to the `.feature` files.
- **feature 内容来自 csv，不是直接从 delivery docs 推导**
- **English `.feature` is the execution source** — playwright-bdd runs this file only
- **Do NOT create a `.cn.feature` companion** — feature files are English-only; case docs live in `cases/manual-test-cases-cn.csv`
- No CSS selectors, API paths, or technical details in the feature file
- All variable values wrapped in double quotes
- **Every scenario MUST have a `@{CASE_ID}` tag placed first (see TC Tag Rules below)**

### 2.2 TC Tag Rules (CRITICAL)

Every scenario MUST have exactly one `@{CASE_ID}` tag placed **first** on the tag line, before other tags.
A `Scenario Outline` carries exactly one `@{CASE_ID}` tag like a normal Scenario — all its Examples rows share that one Case ID (they are variants of ONE case, not separate cases).

**Format**: `@{CASE_ID}` where `{CASE_ID}` comes directly from the **Case ID column (col 1)** of `modules/{module}/{feature}/cases/manual-test-cases-cn.csv`.

The csv Case ID follows the pattern `{MODULE}-{FEATURE}-{NNN}` (e.g., `AUTH-LGN-002`, `HOME-DSH-001`), so the tag is `@AUTH-LGN-002`, `@HOME-DSH-001`, etc.

**Workflow — always assign csv Case ID first**:
1. Append the new case row to the csv (Phase 1.3) — this assigns the Case ID
2. Use that Case ID as the TC tag when writing the scenario

**How to find the next Case ID**:
```python
import csv
with open('modules/{module}/{feature}/cases/manual-test-cases-cn.csv', newline='', encoding='utf-8') as f:
    rows = [r for r in csv.reader(f) if r and r[0]]
last_id = rows[-1][0]  # e.g. "KB-KB3-013" → next is "KB-KB3-014"
```

**Conflict avoidance**: `git pull` before adding new scenarios. If two contributors assign the same Case ID, `npm run lint:bdd` (Check F) catches the duplicate — the merger renumbers to resolve.

### 2.3 Multi-Layer Assertions (多维深度断言 - CRITICAL)

When defining the `Expected Result` in CSV (Phase 1) and writing `Then` steps in Gherkin (Phase 2), you MUST apply **Multi-Layer Assertions**. A simple "success toast" check is NEVER enough.

A robust success verification must check **at least two** of the following layers:
1. **Immediate UI Feedback (Action completed)**: The submit button stops spinning, the creation modal disappears. *(Anti-pattern: Do not solely rely on "Toast message appears", as they are flaky and disappear quickly).*
2. **State / Data Persistence (Crucial)**: The page redirects to the list, and the explicitly named item (e.g., "e2e-va-xyz-001") is visible in the table. Or the detail page reloads and displays the newly saved exact value.
3. **Network / API Truth**: (Optional but recommended) Verify that the underlying API responded with HTTP 200/201 and the correct payload.

**Gherkin Example of Robust Assertions:**
```gherkin
# ❌ Bad (Shallow, flaky)
Then I should see a success message

# ✅ Good (Multi-Layer)
Then the creation modal should disappear
And the agent "e2e-va-xyz-001" should appear in the agent list with status "Active"
And the agent detail page should display "Language: English"
```

### 2.4 English feature format

File: `modules/{module}/{feature}/features/{module}-{feature}.feature`

```gherkin
# language: en
Feature: {Module Name} — {Feature Title}

  Background:
    Given I {navigate to / am logged in and on} the {Page Name} page

  @{CASE_ID_001} @smoke
  Scenario: {Business verb phrase describing the happy path}
    Given {precondition if needed}
    When I {action}
    Then {assertion}

  @{CASE_ID_002} @regression
  Scenario: {Full flow description}
    Given {setup}
    When {sequence of actions}
    Then {assertions}

  @{CASE_ID_003} @negative
  Scenario: {Error case description}
    Given {invalid precondition}
    When {action that should fail}
    Then {error state assertion}

  @{CASE_ID_004} @regression
  Scenario Outline: {Same flow across data variants — ONE case, one outline (Rule P1)}
    When I open the {page} for provider "<provider>"
    Then the "{field}" input should be visible
    And {further multi-layer assertions using "<provider>"}

    Examples:
      | provider   |
      | Deepgram   |
      | Cartesia   |
      | ElevenLabs |
```

> **Gherkin Anti-patterns to AVOID:**
> - ❌ Two or more Scenarios whose steps differ only in one data value (provider / language / page name) — merge into one `Scenario Outline` per Rule P1 in [`case-generate.md`](./case-generate.md) §5
> - ❌ One Scenario per checkpoint of the same user journey (`field visible` / `save works` / `value persists` as 3 scenarios) — merge into one journey Scenario per Rule P2
> - ❌ `When I click the element with xpath "//div[@id='submit']"` (No UI locators in feature files)
> - ❌ `Then I see a red text box with 14px font` (Keep assertions business-focused, abstract away CSS)
> - ❌ `Then I should see the success message` (Too shallow, violates Multi-Layer Assertions)
> - ✅ `When I submit the form` / `Then the modal should disappear` / `And the item should appear in the list`
> - **CRITICAL:** Variables passed to steps MUST be enclosed in double quotes (e.g., `When I click the "Save" button`).

### 2.5 Tag selection rules
| Scenario type | Tag |
|---|---|
| Page loads, key element visible, < 30s | `@smoke` |
| Full happy path with data creation/deletion | `@regression` |
| AI generation, polling, > 60s | `@slow` (add alongside `@regression`) |
| Error input, permission denied, validation | `@negative` |

---

## E2E Stability Rules — 写 POM / Steps / 修复 flaky 时必须遵守

写或修任何 Page Object / Step Definition 前，**必读** [`e2e-stability.md`](./e2e-stability.md)：
禁止 `waitForTimeout`、乐观更新的网络等待、`.waitFor({state})` → `expect` 迁移、
`wait-utils.ts` 用法、Locator 优先级、以及 `npm run lint:bdd` 的 stability 检查。

---

## Phase 3 — Feature → Page Object + Steps

*(Note: The implementation gate check is now handled in Phase 2.0. If you are in Phase 3, you are only writing code for features confirmed to exist in the codebase.)*

### 3.0.5 Test Isolation & Data Management Strategy (CRITICAL)

写本阶段的 POM/Steps 前，**必读** [`test-data-strategy.md`](./test-data-strategy.md)：
Three-Tier 数据分类（Application Data 必建必清 / Infra & Config 预置 / Legacy 高成本降级 Manual）、
per-scenario 数据播种、`e2e-{CaseID}` 命名、以及 测试数据 CRUD 必须走 `core/api/entities`。
该分类同样驱动 Phase 1 的 AutoTest/Manual 执行方式判断。

### 3.1 Scan for existing coverage
Before writing anything:
```bash
# Check existing steps in this feature's steps file (if it exists)
grep -n "Given\|When\|Then" modules/{module}/{feature}/steps/{module}-{feature}.steps.ts 2>/dev/null
# Check sibling feature directories for reusable steps
grep -rn "Given\|When\|Then" modules/{module}/*/steps/ --include="*.ts"
# Check common steps
grep -n "Given\|When\|Then" modules/common/steps/common.steps.ts
```
Reuse any step whose sentence matches exactly. Do NOT redefine an existing step.

### 3.2 Page Object rules
File: `modules/{module}/{feature}/pages/{FeatureName}Page.ts`

- If the feature only needs methods that already exist on a sibling's Page class, import that class directly rather than creating a new one.
- If new methods are needed, create `{FeatureName}Page.ts` in the feature's own `pages/` directory.
- Import path from `{feature}/pages/` to shared helpers: `../../../common/` (3 levels up to `modules/`), `../../../../core/` (4 levels up to `AutoTest/`).

- All locators MUST be defined in the Page class — never in steps
- Group methods by operation: navigate, fill*, click*, assert*, wait*, get*
- `navigate()` must wait for a key element before returning (timeout: 30000ms)
- Use `this.frame.getBy*` for iframe content; `this.page.getBy*` for main page
- For shared remote environments: all `waitFor` timeouts ≥ 20000ms
- **Action & Wait combo:** Every method that triggers a network request or major DOM change (e.g., `clickSave()`, `submitForm()`) MUST wait for the expected outcome before returning. Do NOT rely on the step definition to handle the wait.
  - **优先 UI 等待**: 如果操作引发明显的 UI Loading 变化，使用 `await expect(locator).toBeVisible()`。
  - **结合网络等待**: 如果是核心写入操作、弹窗无感消失或 UI 状态变化不可靠，必须结合 `waitForResponse` 拦截网络层。
  - **Multi-Layer Assertions**: NEVER return booleans from POM methods for assertions. Perform the `expect(...)` directly inside the POM method. When asserting creation/updates, always locate the element by its unique text/name generated for this specific scenario (e.g., `this.page.getByText(agentName)`).

```typescript
// Add only methods needed by the new feature scenarios
async clickNewFeatureButton(): Promise<void> {
  // 推荐模式：网络监听 + 点击触发 + 动态等待
  const resPromise = this.page.waitForResponse(r => r.url().includes('/api/feature') && r.status() === 200);
  await this.frame.getByRole('button', { name: 'Button Label' }).click();
  await resPromise;
  await expect(this.frame.locator('.result-indicator')).toBeVisible({ timeout: 20000 });
}
```

### 3.3 Step Definition rules
File: `modules/{module}/{feature}/steps/{module}-{feature}.steps.ts`

Create the `steps/` directory if it doesn't exist: `mkdir -p modules/{module}/{feature}/steps/`

- Each step calls exactly one POM method — no inline Playwright code
- Use `{string}` parameters for all variable values
- Background step must call `new {Module}Page(page).navigate()`

```typescript
When('I click the {string} button in the new feature', async ({ page }, label: string) => {
  await new ModulePage(page).clickNewFeatureButton();
});
```

---


## Phase 4 — Validation

Run all three commands in order. Fix any errors before reporting done:

```bash
npm run bdd:gen      # Must: 0 missing step definitions
npm run typecheck    # Must: 0 TypeScript errors
npm run lint:bdd     # Must: all checks PASS
```

If `bdd:gen` reports missing steps → go back to Phase 3 and add them.
If `typecheck` errors → fix types in POM or steps.
If `lint:bdd` fails TC tag coverage → every scenario needs a valid `@{CASE_ID}` tag; fix format or add missing tags.

---

## Phase 5 — Coverage

Run `npm run coverage` and report automated / total; `npm run coverage:check` fails below 80%.
(The voice-agent source also synced a product feature tree generated from a PM feature catalog;
vibejet has no feature catalog, so that step is not ported.)

---

## Output Report

After completing all phases, report:

```
=== Delivery Docs → BDD Pipeline Complete ===

Delivery docs: {file path(s)}
Module: {module}
Case slug: {case-slug}

Phase 1 — Cases
  ✓ {n} rows appended to modules/{module}/{feature}/cases/manual-test-cases-cn.csv

Phase 2 — Features
  ✓ {n} scenario(s) written to modules/{module}/{feature}/features/{module}-{feature}.feature

Phase 3 — Implementation
  ✓ {n} method(s) added to {feature}/pages/{FeatureName}Page.ts
  ✓ {n} step(s) added to {feature}/steps/{module}-{feature}.steps.ts
  (reused {n} existing step(s))

Phase 4 — Validation
  ✓ bdd:gen: 0 missing steps
  ✓ typecheck: 0 errors
  ✓ lint:bdd: all checks PASS

Phase 5 — Coverage
  ✓ npm run coverage → {automated}/{total}

Run: npm run test:{module-alias}:local
```

---

## Activation Pipeline — 代码上线后激活 Pending 用例

当用户说 "激活 pending 用例" / "activate pending" / "代码上线了，激活用例" 时，**这是另一条工作流**，
不要走上面的主 Pipeline。**必读** [`activation.md`](./activation.md) 并严格按其 Step A–G 执行
（确认目标 → 实现门检查 → 从 pending 移入主 feature → 补 POM/Steps → 验证 → 更新 csv）。

> 激活完成后，被激活的用例已变为自动化，同样要执行 Phase 5（`npm run coverage`）。
