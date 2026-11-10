# Test Isolation & Data Management Strategy (CRITICAL)

> Loaded on demand by `SKILL.md`. **必读** before writing Phase 3 POM/Steps, and when
> deciding execution type in Phase 1 (the Three-Tier classification feeds the
> Automated/Manual decision).

**Core Rule**: Tests must run successfully in a completely empty, newly deployed environment. However, not all data must be created from scratch. In Phase 1 and when writing automation steps, you MUST strictly apply the **Three-Tier Data Classification Principle**:

| Data Type | Examples | Action Rule |
|-----------|----------|-------------|
| **Application Data** | Conversation, message, document, file, agent config | **【MUST Build & Clean】** The script MUST dynamically create this data via API in `Given` steps using the `e2e-{CaseID}` prefix, and clean it up at the end. Never assume it exists. |
| **Infra & Config** | Base URL, test-account credentials, LLM API keys | **【Pre-configured (Allowed)】** These are runtime dependencies. Read them from `config/environments.json` / `process.env`. The test accounts are standing fixtures (`Release-Check/_shared/fixtures.md`). Do NOT build via UI. |
| **Legacy / High-Cost** | Data that cannot be rebuilt through the API; long LLM runs that are too slow or too flaky | **【Downgrade to Manual】** Set `执行方式` to `手工测试-产线高危` — or `手工测试-故障注入` when the case needs an injected failure — in Phase 1 and explain in the 备注 column. |

**Why**: Tests may run with WORKERS > 1 in parallel. Shared data causes race conditions. Hardcoded IDs break across environments. Forcing high-cost data creation leads to extreme flakiness.

---

## Principle 1 — Application Data MUST be created per scenario

Every piece of application data that a scenario reads or modifies MUST be created exclusively for that scenario.

**Standard Gherkin Data Seeding Pattern (For Application Data)**:
```gherkin
@CHAT-CNV-001 @regression
Scenario: Rename a conversation
  # 1. Active Seeding (Creates the necessary environment)
  Given a conversation "e2e-chat-CHAT-CNV-001" exists via API
  # 2. Business Logic Execution
  When I rename the conversation "e2e-chat-CHAT-CNV-001" to "e2e-renamed"
  # 3. Multi-Layer Assertion
  Then the conversation list shows "e2e-renamed"
  # 4. Cleanup
  Given conversation "e2e-renamed" is cleaned up
```

The name in the feature file is **documentation only** — steps derive the actual runtime name from the `@CASE_ID` tag (via `test.info()`), so parallel workers never conflict.

---

## Principle 2 — All test data cleaned up after the scenario

**Every scenario that creates data MUST delete it** at the end, even on failure paths: the entity factory registers each id in `core/api/registry.ts`, and the global After hook (`modules/common/steps/e2e-cleanup.steps.ts`) deletes whatever the scenario did not.

Use teardown steps (last `Given` in the scenario) rather than relying only on the After hook, so failures are visible in the BDD report.

---

## Principle 3 — Resource naming follows Case ID

All e2e-created resources use the `e2e-` prefix + Case ID slug so they are:
- Identifiable as test data at a glance
- Unique per scenario (preventing parallel conflicts)
- Automatically derivable from the test's `@CASE_ID` tag

Derive the name in the step from `test.info()` (the scenario's tags), ignore the literal string in the feature. Names are ASCII only (`lint:bdd` Check D).

| Module | Prefix | Case ID format | Example runtime name |
|--------|--------|----------------|----------------------|
| auth | `e2e-auth` | `AUTH-LGN-NNN` | `e2e-auth-auth-lgn-nnn` |
| home | `e2e-home` | `HOME-DSH-NNN` | `e2e-home-home-dsh-nnn` |

---

## Principle 4 — Test data CRUD always through `core/api/entities`

All create/delete operations go through an entity factory in `core/api/entities/<x>.api.ts` (see `core/api/README.md` and `core/api/EXCEPTIONS.md`). Never create or delete data from steps or page objects with `page.request.*` (`lint:bdd` Check H), and never through the UI unless the UI action is the behavior under test.

To pass an id between steps within a scenario, store it on the page object:
```typescript
(page as unknown as Record<string, string>)['_conversationId'] = conversationId;
```
