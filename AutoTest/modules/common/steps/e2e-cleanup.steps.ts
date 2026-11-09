/**
 * Global After hook for e2e test data lifecycle management.
 *
 * After each test: clean up all data created during this test, dispatched by
 * entity type via the core/api registry. Entity factories auto-register ids at
 * creation time, so this runs even when a test fails before its in-scenario
 * cleanup step.
 *
 * Loaded for ALL test projects via the COMMON_STEPS glob in playwright.config.ts.
 */

import { createBdd } from 'playwright-bdd';
import { Page } from '@playwright/test';
import { registry } from '../../../core/api/registry';
import { AgentApi } from '../../../core/api/entities/agent.api';
import { CaseSetApi } from '../../../core/api/entities/case-set.api';
import { SimulationApi } from '../../../core/api/entities/simulation.api';
import { QrIntentApi } from '../../../core/api/entities/qr-intent.api';
import { registerAgentForCleanup } from '../agent/cleanup-registry';

const { After } = createBdd();

// Re-exported so existing `import { registerAgentForCleanup } from '.../e2e-cleanup.steps'`
// call sites keep working unchanged.
export { registerAgentForCleanup };

// ── Global hooks ───────────────────────────────────────────────────────────

// No Before hook needed: each Given step uses ensureFresh (delete-then-create),
// which guarantees a clean state before creation.

After(async ({ page }: { page: Page }) => {
  const drained = registry.flushAll();
  const api = new AgentApi(page);
  // Numeric ids registered by agentApi.create at creation time.
  for (const id of drained['agent'] ?? []) await api.delete(id);
  // Names registered via the legacy shim / UI-create call sites.
  for (const name of drained['agent-name'] ?? []) await api.deleteByName(name);

  // case-set cleanup is best-effort and mostly redundant with agent deletion
  // (deleting the owning agent orphans its suites), but archiving explicitly
  // here also covers tenant-wide suites created by an agent OTHER than the
  // one under test's own dedicated-agent cleanup (tenant-testset-list fixtures).
  const caseSetApi = new CaseSetApi(page);
  for (const id of drained['case-set'] ?? []) await caseSetApi.deleteById(Number(id));

  const simulationApi = new SimulationApi(page);
  for (const id of drained['simulation'] ?? []) await simulationApi.delete(id);

  // QR (filler) intents are tenant-level, not agent-level, so deleting the scenario's
  // agent does NOT orphan them — a scenario that fails before its cleanup step would
  // otherwise leave a bound intent live for the whole tenant.
  const qrApi = new QrIntentApi(page);
  for (const id of drained['qr-intent'] ?? []) await qrApi.deleteById(Number(id));
});
