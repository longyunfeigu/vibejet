# Test Isolation & Data Management Strategy (CRITICAL)

> Loaded on demand by `SKILL.md`. **必读** before writing Phase 3 POM/Steps, and when
> deciding execution type in Phase 1 (the Three-Tier classification feeds the
> AutoTest/Manual decision).

**Core Rule**: Tests must run successfully in a completely empty, newly deployed environment. However, not all data must be created from scratch. In Phase 1 and when writing automation steps, you MUST strictly apply the **Three-Tier Data Classification Principle**:

| Data Type | Examples | Action Rule |
|-----------|----------|-------------|
| **Application Data** | Agent, Knowledge Base, Dialog flow, Webhook records, Call History | **【MUST Build & Clean】** The script MUST dynamically create this data via UI/API in `Given` steps using the `e2e-{CaseID}` prefix, and clean it up at the end. Never assume it exists. |
| **Infra & Config** | Base URL, OpenAI API Key, LiveKit auth, SIP Trunk | **【Pre-configured (Allowed)】** These are runtime dependencies. Read them from global config or environment variables (`environments.json` / `process.env`). Do NOT build via UI. |
| **Legacy / High-Cost** | "Pre-launch historical call logs", highly complex LLM live calls | **【Downgrade to Manual】** Cannot be reliably rebuilt via API or costs too much/too flaky. Set `Execution Type` to `Manual-Prod-Unsafe` (EN) / `手工测试-产线高危` (CN) — or `Manual-Fault-Injection` / `手工测试-故障注入` when the case needs an injected failure — in Phase 1 and explain in the Notes column. |

**Why**: Tests run with WORKERS=6 in parallel. Shared data causes race conditions. Hardcoded IDs break across environments. Forcing high-cost data creation leads to extreme flakiness.

---

## Principle 1 — Application Data MUST be created per scenario

Every piece of application data that a scenario reads or modifies MUST be created exclusively for that scenario.

**Standard Gherkin Data Seeding Pattern (For Application Data)**:
```gherkin
@VA-HOT-001 @regression
Scenario: Modify hotwords for an existing agent
  # 1. Active Seeding (Creates the necessary environment)
  Given a newly created agent "e2e-hotwords-VA-HOT-001" is ready via API
  # 2. Business Logic Execution
  When I navigate to the agent "e2e-hotwords-VA-HOT-001" hotword settings
  And I add the hotword "activate"
  # 3. Multi-Layer Assertion
  Then the agent "e2e-hotwords-VA-HOT-001" should display "activate" in the list
  # 4. Cleanup
  Given agent "e2e-hotwords-VA-HOT-001" is cleaned up
```

The name in the feature file (e.g., `"e2e-hotwords-VA-HOT-001"`) is **documentation only** — steps derive the actual runtime name from the `@CASE_ID` tag automatically, so parallel workers never conflict.

---

## Principle 2 — All test data cleaned up after the scenario

**Every scenario that creates data MUST delete it** at the end, even on failure paths.

```gherkin
# Last step of every scenario that created data:
Given agent "e2e-va-xyz-001" is cleaned up
# or:
Given knowledge base "e2e-kb-xyz-001" is cleaned up
# or:
Given AI simulation test "e2e-ai-sim-xyz-001" is cleaned up
```

Use teardown steps (last `Given` in the scenario) rather than `After` hooks, so failures are visible in the BDD report.

---

## Principle 3 — Resource naming follows Case ID

All e2e-created resources use the `e2e-` prefix + Case ID slug so they are:
- Identifiable as test data at a glance
- Unique per scenario (preventing parallel conflicts)
- Automatically derivable from the test's `@CASE_ID` tag

**Agent naming** is handled by `AgentManager.buildCaseAgentName(test.info(), prefix)` in `modules/common/agent/AgentManager.ts`. For other resource types, follow the same pattern: derive the name from `test.info()` in the step, ignore the literal string in the feature.

**Agent prefix reference:**

| Module | Prefix | Case ID format | Example runtime name |
|--------|--------|----------------|----------------------|
| voice-agent (generic) | `e2e-va` | `VA-VAX-NNN` | `e2e-va-va-vax-nnn` |
| voice-agent (hotwords) | `e2e-hotwords` | `VA-HOT-NNN` | `e2e-hotwords-va-vab05-nnn` |
| voice-agent (fallback rules) | `e2e-geh` | `VA-FBR-NNN` | `e2e-geh-va-geh01-nnn` |
| ai-simulation | `e2e-ai-sim` | `AI-NNN` | `e2e-ai-sim-ai-nnn` |

---

## Principle 4 — Agent CRUD always through `AgentManager`

All agent create/delete operations MUST go through `AgentManager` in `modules/common/agent/AgentManager.ts`. Never call page-local methods like `VoiceAgentPage.deleteAllMatchingAgents()` from steps.

```typescript
// Setup
const agentName = AgentManager.buildCaseAgentName(test.info(), 'e2e-<prefix>');
await new AgentManager(page).ensureFreshAgent(agentName);  // delete-then-create

// Teardown
await new AgentManager(page).deleteAgentsByName(agentName);
```

To pass the agent ID between steps within a scenario, store it on the page object:
```typescript
(page as unknown as Record<string, string>)['_agentId'] = agentId;
```
