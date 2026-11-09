import { APIRequestContext, APIResponse, Page } from '@playwright/test';

/** Bound short timeout so cleanup never inherits a @slow test's inflated timeout. */
export const API_TIMEOUT_MS = 15_000;

/** DELETE /api/agents/{id} requires source_agent_region matching the deployment env. */
export function deleteAgentRegion(env: string | undefined = process.env.VOICE_AGENT_ENV): string {
  return (env ?? 'uat').toUpperCase();
}

export function buildAgentDeletePath(agentId: number | string, region: string): string {
  return `/api/agents/${agentId}?source_agent_region=${region}`;
}

/**
 * Thin wrapper over Playwright's request context.
 *
 * - Reuses the page's logged-in storage state (no token management here).
 * - Reads return the APIResponse; callers decide how to interpret it.
 * - `safeDelete` is best-effort: it never throws, only warns (cleanup must never
 *   fail a passing test). Writes that MUST succeed (test preconditions) use the
 *   request context directly in the entity factory and throw on failure.
 *
 * TENANT HEADER: `get_tenant_id()` on ai-simulation-api reads `X-Selected-Tenant-Id`,
 * falling back to the `selected_tenant_id` cookie. The real frontend sets this
 * header explicitly from client-known state (see suiteApi.ts's `headers(tenantId)`)
 * — it does NOT rely on the cookie fallback working through the proxy. That
 * fallback in fact doesn't work here: RD/docker/caddy/Caddyfile's `@ai_sim` block
 * (unlike `@flow_api`/`@kbhub_api`) has no `header_up X-Selected-Tenant-Id
 * {http.request.cookie.selected_tenant_id}` directive AND strips the Cookie header
 * upstream (`header_up -Cookie`) — so a raw API call through this proxy with no
 * explicit header always resolves to tenant_id="" server-side, silently mis-scoping
 * every write to no tenant. Every `ApiClient` request reads the same
 * `selected_tenant_id` cookie the frontend uses and forwards it explicitly so
 * this works regardless of that proxy gap.
 */
export class ApiClient {
  private readonly request: APIRequestContext;
  private readonly page: Page;

  constructor(page: Page) {
    this.page = page;
    this.request = page.request;
  }

  private async tenantHeaders(): Promise<Record<string, string>> {
    const cookies = await this.page.context().cookies();
    const tenantCookie = cookies.find(c => c.name === 'selected_tenant_id');
    return tenantCookie ? { 'X-Selected-Tenant-Id': tenantCookie.value } : {};
  }

  async getJson<T>(url: string): Promise<T> {
    const headers = await this.tenantHeaders();
    const resp = await this.request.get(url, { headers, timeout: API_TIMEOUT_MS });
    if (!resp.ok()) {
      const body = await resp.text().catch(() => '');
      throw new Error(`GET ${url} failed [${resp.status()}]: ${body}`);
    }
    return (await resp.json()) as T;
  }

  async post<T>(url: string, data: unknown): Promise<T> {
    const headers = await this.tenantHeaders();
    const resp = await this.request.post(url, { data, headers, timeout: API_TIMEOUT_MS });
    if (!resp.ok()) {
      const body = await resp.text().catch(() => '');
      throw new Error(`POST ${url} failed [${resp.status()}]: ${body}`);
    }
    return (await resp.json()) as T;
  }

  async put<T>(url: string, data: unknown): Promise<T> {
    const headers = await this.tenantHeaders();
    const resp = await this.request.put(url, { data, headers, timeout: API_TIMEOUT_MS });
    if (!resp.ok()) {
      const body = await resp.text().catch(() => '');
      throw new Error(`PUT ${url} failed [${resp.status()}]: ${body}`);
    }
    return (await resp.json()) as T;
  }

  /** Raw GET response for negative cases that intentionally expect a non-2xx result. */
  async getResponse(url: string): Promise<APIResponse> {
    const headers = await this.tenantHeaders();
    return this.request.get(url, { headers, timeout: API_TIMEOUT_MS });
  }

  /** Raw PUT response for negative cases that intentionally expect a non-2xx result. */
  async putResponse(url: string, data: unknown): Promise<APIResponse> {
    const headers = await this.tenantHeaders();
    return this.request.put(url, { data, headers, timeout: API_TIMEOUT_MS });
  }

  /** Best-effort delete: logs warnings, never throws. Returns true on 2xx. */
  async safeDelete(url: string): Promise<boolean> {
    const headers = await this.tenantHeaders();
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
