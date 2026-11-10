import { APIRequestContext, APIResponse, Page } from '@playwright/test';
import { SESSION_STORAGE_KEY } from '../helpers/constants';

/** Bound short timeout so cleanup never inherits a @slow test's inflated timeout. */
export const API_TIMEOUT_MS = 15_000;

/**
 * Thin wrapper over Playwright's request context.
 *
 * - Acts as the account signed in to the page: the backend's /api/v1 is bearer-only, and the
 *   frontend keeps the token pair in localStorage (frontend/src/lib/authStore.ts), so every
 *   request reads the current access token from the context's storage state.
 * - Relative URLs resolve against the project baseURL (the frontend); its dev server proxies
 *   /api to the backend.
 * - Reads return the parsed body; callers decide how to interpret it.
 * - `safeDelete` is best-effort: it never throws, only warns (cleanup must never fail a passing
 *   test). Writes that MUST succeed (test preconditions) throw on failure.
 */
export class ApiClient {
  private readonly request: APIRequestContext;
  private readonly page: Page;

  constructor(page: Page) {
    this.page = page;
    this.request = page.request;
  }

  private async authHeaders(): Promise<Record<string, string>> {
    const state = await this.page.context().storageState();
    for (const origin of state.origins) {
      for (const item of origin.localStorage) {
        if (item.name !== SESSION_STORAGE_KEY) continue;
        const token = (JSON.parse(item.value) as { accessToken?: string }).accessToken;
        if (token) return { Authorization: `Bearer ${token}` };
      }
    }
    return {};
  }

  async getJson<T>(url: string): Promise<T> {
    const headers = await this.authHeaders();
    const resp = await this.request.get(url, { headers, timeout: API_TIMEOUT_MS });
    if (!resp.ok()) {
      const body = await resp.text().catch(() => '');
      throw new Error(`GET ${url} failed [${resp.status()}]: ${body}`);
    }
    return (await resp.json()) as T;
  }

  async post<T>(url: string, data: unknown): Promise<T> {
    const headers = await this.authHeaders();
    const resp = await this.request.post(url, { data, headers, timeout: API_TIMEOUT_MS });
    if (!resp.ok()) {
      const body = await resp.text().catch(() => '');
      throw new Error(`POST ${url} failed [${resp.status()}]: ${body}`);
    }
    return (await resp.json()) as T;
  }

  async put<T>(url: string, data: unknown): Promise<T> {
    const headers = await this.authHeaders();
    const resp = await this.request.put(url, { data, headers, timeout: API_TIMEOUT_MS });
    if (!resp.ok()) {
      const body = await resp.text().catch(() => '');
      throw new Error(`PUT ${url} failed [${resp.status()}]: ${body}`);
    }
    return (await resp.json()) as T;
  }

  /** Raw GET response for negative cases that intentionally expect a non-2xx result. */
  async getResponse(url: string): Promise<APIResponse> {
    const headers = await this.authHeaders();
    return this.request.get(url, { headers, timeout: API_TIMEOUT_MS });
  }

  /** Raw PUT response for negative cases that intentionally expect a non-2xx result. */
  async putResponse(url: string, data: unknown): Promise<APIResponse> {
    const headers = await this.authHeaders();
    return this.request.put(url, { data, headers, timeout: API_TIMEOUT_MS });
  }

  /** Best-effort delete: logs warnings, never throws. Returns true on 2xx. */
  async safeDelete(url: string): Promise<boolean> {
    const headers = await this.authHeaders();
    const resp: APIResponse | null = await this.request
      .delete(url, { headers, timeout: API_TIMEOUT_MS })
      .catch((err: unknown) => {
        console.warn(`[ApiClient] DELETE ${url} threw: ${(err as Error).message}`);
        return null;
      });
    if (!resp) return false;
    if (!resp.ok()) {
      const detail = await resp.text().catch(() => '');
      console.warn(`[ApiClient] DELETE ${url} -> HTTP ${resp.status()} ${detail}`.trim());
      return false;
    }
    return true;
  }
}
