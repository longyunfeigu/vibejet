/**
 * Global After hook for e2e test data lifecycle management.
 *
 * After each test: clean up all data created during this test, dispatched by
 * entity type via the core/api registry. Entity factories register ids at
 * creation time, so this runs even when a test fails before its in-scenario
 * cleanup step.
 *
 * Loaded for ALL test projects via the COMMON_STEPS glob in playwright.config.ts.
 */

import { createBdd } from 'playwright-bdd';
import { Page } from '@playwright/test';
import { registry } from '../../../core/api/registry';

const { After } = createBdd();

// Entity type -> delete. Add a handler next to each entity factory in core/api/entities/
// (see core/api/EXCEPTIONS.md); a type with no handler is reported, never silently dropped.
const CLEANUP: Record<string, (page: Page, id: string) => Promise<unknown>> = {};

After(async ({ page }: { page: Page }) => {
  for (const [type, ids] of Object.entries(registry.flushAll())) {
    const clean = CLEANUP[type];
    if (!clean) {
      console.warn(`[e2e-cleanup] no cleanup handler for "${type}"; left behind: ${ids.join(', ')}`);
      continue;
    }
    for (const id of ids) await clean(page, id);
  }
});
