/**
 * Unified wait helpers for E2E tests.
 *
 * RULES:
 * - Never use page.waitForTimeout() — it hides race conditions.
 * - Always wait for a concrete business state (visible, hidden, text, URL).
 * - Import TIMEOUTS from constants.ts — never hardcode ms values.
 *
 * If you need a workaround sleep, route it through controlledWait() with a
 * reason so hard waits are searchable and reviewable.
 */

import { expect, Locator, Page, Response } from '@playwright/test';
import { TIMEOUTS } from './constants';

/** Wait until a locator is visible. Fails with a clear message on timeout. */
export async function expectVisible(
  locator: Locator,
  message?: string,
  timeout: number = TIMEOUTS.page_load,
): Promise<void> {
  await expect(locator, message).toBeVisible({ timeout });
}

/** Wait until a locator is hidden / removed from DOM. */
export async function expectHidden(
  locator: Locator,
  message?: string,
  timeout: number = TIMEOUTS.page_load,
): Promise<void> {
  await expect(locator, message).toBeHidden({ timeout });
}

/** Wait until a locator contains the expected text. */
export async function expectText(
  locator: Locator,
  text: string,
  timeout: number = TIMEOUTS.page_load,
): Promise<void> {
  await expect(locator).toContainText(text, { timeout });
}

/** Wait until the page URL matches a pattern. */
export async function expectUrl(
  page: Page,
  pattern: string | RegExp,
  timeout: number = TIMEOUTS.page_load,
): Promise<void> {
  await expect(page).toHaveURL(pattern, { timeout });
}

/**
 * Wait for a loading/spinner element to disappear.
 * Use after triggering async actions (save, upload, generate).
 *
 * @param spinner - Locator for the loading indicator
 * @param timeout - Max wait time (defaults to api_response)
 */
export async function waitForLoadingDone(
  spinner: Locator,
  timeout: number = TIMEOUTS.api_response,
): Promise<void> {
  await expect(spinner).toBeHidden({ timeout });
}

/**
 * Wait for a row/item to reach a terminal status text (e.g. "Completed", "Failed").
 * Replaces polling loops with waitForTimeout.
 *
 * @param row - The row locator
 * @param statusText - Expected status text
 * @param timeout - Max wait (defaults to document_processing)
 */
export async function waitForStatus(
  row: Locator,
  statusText: string,
  timeout: number = TIMEOUTS.document_processing,
): Promise<void> {
  await expect(row.getByText(statusText)).toBeVisible({ timeout });
}

/**
 * Wait for a dialog / modal to open (checks for a key element inside it).
 * Replaces arbitrary sleep after button clicks.
 */
export async function waitForDialogOpen(
  dialogLocator: Locator,
  timeout: number = TIMEOUTS.page_load,
): Promise<void> {
  await expect(dialogLocator).toBeVisible({ timeout });
}

/**
 * Wait for a dialog / modal to close.
 */
export async function waitForDialogClose(
  dialogLocator: Locator,
  timeout: number = TIMEOUTS.page_load,
): Promise<void> {
  await expect(dialogLocator).toBeHidden({ timeout });
}

/**
 * Wait for a count of matching elements to stabilise at an expected number.
 * Useful after delete / create operations.
 */
export async function expectCount(
  locator: Locator,
  count: number,
  timeout: number = TIMEOUTS.page_load,
): Promise<void> {
  await expect(locator).toHaveCount(count, { timeout });
}

/**
 * Click a button and wait for a visible result locator to appear.
 * Combines action + business assertion in one call.
 */
export async function clickAndWait(
  button: Locator,
  resultLocator: Locator,
  timeout: number = TIMEOUTS.page_load,
): Promise<void> {
  await button.click();
  await expect(resultLocator).toBeVisible({ timeout });
}

/**
 * Perform ANY action and wait for a matching network response to complete.
 *
 * WHY THIS EXISTS
 * ───────────────
 * Many UI state changes are unreliable signals for backend completion:
 *  • Optimistic updates: a toggle turns green immediately, but the API is still in-flight.
 *  • Debounced toasts: "Saved" appears 500 ms after the response, not at response time.
 *  • Silent operations: no visible DOM change at all (e.g. a DELETE that just removes a row).
 *  • Page navigation: goto() resolves on DOMContentLoaded, but data-fetch XHRs fire after.
 *
 * Waiting for the network response is the most precise signal that the backend
 * has processed the request, eliminating an entire class of flaky tests.
 *
 * HOW IT WORKS
 * ────────────
 * Playwright listens at the browser network layer. The helper resolves as soon
 * as a matching response arrives — immediately if the API is fast, or after
 * however long the backend takes. It never wastes time beyond what is necessary.
 *
 * RACE CONDITION RULE (critical)
 * ──────────────────────────────
 * The listener MUST be registered BEFORE the action that triggers the request.
 * If the response arrives before the listener is set up, it is missed and the
 * helper times out. This helper enforces the correct order internally.
 *
 *   // ❌ wrong — response may arrive before listener is set
 *   await saveBtn.click();
 *   await page.waitForResponse('/api/save');
 *
 *   // ✅ correct — listener armed before any action
 *   await withResponse(() => saveBtn.click(), '/api/save', page);
 *
 * MULTI-WORKER SAFETY
 * ───────────────────
 * Each Playwright worker has its own browser context and network listener.
 * There is no cross-worker interference. `page` is required explicitly so
 * the listener is always scoped to the correct worker context.
 *
 * USAGE EXAMPLES
 * ──────────────
 * // 1. Click (save button)
 * await withResponse(() => saveBtn.click(), /\/api\/agents\/\d+\/hotwords/, page);
 *
 * // 2. Page navigation (data fetch fires after DOMContentLoaded)
 * await withResponse(
 *   () => page.goto('./agents'),
 *   r => r.url().includes('/api/agents') && r.status() === 200,
 *   page,
 * );
 *
 * // 3. Form submit / input change
 * await withResponse(() => input.press('Enter'), '/api/search', page);
 *
 * // 4. Assert the response status code
 * const resp = await withResponse(
 *   () => deleteBtn.click(),
 *   r => r.url().includes('/api/agents') && r.request().method() === 'DELETE',
 *   page,
 * );
 * expect(resp.status()).toBe(204);
 *
 * @param action         - Async thunk that triggers the request (click, goto, fill+Enter, …).
 * @param urlOrPredicate - URL substring, regex, or full predicate (url + method + status).
 * @param page           - The Playwright Page whose network layer to listen on.
 * @param timeout        - Max wait in ms (default: api_response = 10 s).
 * @returns The matched Response object (status, body, headers available).
 */
export async function withResponse(
  action: () => Promise<void>,
  urlOrPredicate: string | RegExp | ((response: Response) => boolean | Promise<boolean>),
  page: Page,
  timeout: number = TIMEOUTS.api_response,
): Promise<Response> {
  // Arm the listener BEFORE the action to guarantee no response is missed.
  const responsePromise = page.waitForResponse(urlOrPredicate, { timeout });
  await action();
  return responsePromise;
}

/**
 * WORKAROUND sleep — use only when there is no observable DOM state change.
 * MUST include a comment explaining why and when to remove.
 *
 * @param ms - Max 2000ms. Anything higher should use a proper wait.
 * @param reason - Required explanation (enforced by convention, not runtime).
 */
export async function workaroundSleep(page: Page, ms: number, _reason: string): Promise<void> {
  if (ms > 2000) {
    throw new Error(
      `workaroundSleep: ${ms}ms exceeds 2000ms limit. Use a business-state wait instead.`,
    );
  }
  await controlledWait(page, ms, _reason);
}

/**
 * Controlled escape hatch for unavoidable fixed delays.
 *
 * Prefer business-state waits. Use this only for debounce intervals, polling
 * backoff, UI animation settling, or third-party widgets with no observable
 * DOM/network state. The reason is mandatory to make each usage reviewable.
 */
export async function controlledWait(page: Page, ms: number, reason: string): Promise<void> {
  if (!reason.trim()) {
    throw new Error('controlledWait requires a reason');
  }
  // Keep the page parameter so call sites make the browser context explicit.
  await page.evaluate(() => undefined).catch(() => {});
  await new Promise<void>(resolve => setTimeout(resolve, ms));
}

/**
 * Navigate with lightweight retry for transient transport errors seen in shared UAT.
 * This is intentionally narrow: only retries known connection-reset style failures.
 */
export async function gotoWithRetry(
  page: Page,
  url: string,
  options: Parameters<Page['goto']>[1] = { waitUntil: 'domcontentloaded' },
  maxAttempts = 3,
): Promise<void> {
  let lastError: unknown;
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      await page.goto(url, options);
      return;
    } catch (error) {
      lastError = error;
      const message = error instanceof Error ? error.message : String(error);
      const isTransient =
        message.includes('ERR_CONNECTION_CLOSED') ||
        message.includes('ERR_CONNECTION_RESET') ||
        message.includes('ECONNRESET') ||
        message.includes('ETIMEDOUT');
      if (!isTransient || attempt === maxAttempts) {
        throw error;
      }
      await controlledWait(
        page,
        1200 * attempt,
        `Transient navigation error (${attempt}/${maxAttempts}) for ${url}; retrying`,
      );
    }
  }
  throw lastError instanceof Error ? lastError : new Error(String(lastError));
}
