/**
 * vibejet E2E Global Setup
 *
 * 在所有测试开始前验证 auth-state 是否有效。
 * 若 auth 已过期或不存在：确保测试账号存在（不存在就调注册接口建），再走真实登录页登录，
 * 保存新的 auth-state（前端把会话放在 localStorage，storageState 会一并保存）。
 *
 * 环境配置通过 env-config.ts 读取（支持多环境）：
 *   E2E_ENV=local npm run test:auth:local
 */

import { chromium, devices, FullConfig, expect, request } from '@playwright/test';
import * as fs from 'fs';
import { getE2EConfig, getAuthStatePath } from './env-config';
import { SESSION_STORAGE_KEY } from '../core/helpers/constants';

/** Parse JWT payload without verifying signature — used only for expiry pre-check. */
function jwtExpiresAt(token: string): Date | null {
  try {
    const payload = JSON.parse(Buffer.from(token.split('.')[1], 'base64url').toString());
    return payload.exp ? new Date(payload.exp * 1000) : null;
  } catch {
    return null;
  }
}

/**
 * Fast pre-check: read the session the frontend stored in localStorage and verify the
 * access token is not expired. True if > 60s remain. Does NOT launch a browser.
 */
function isAuthStateValid(authStatePath: string): boolean {
  if (!fs.existsSync(authStatePath)) return false;
  try {
    const state = JSON.parse(fs.readFileSync(authStatePath, 'utf-8'));
    for (const origin of state.origins ?? []) {
      for (const { name, value } of origin.localStorage ?? []) {
        if (name !== SESSION_STORAGE_KEY) continue;
        const expiresAt = jwtExpiresAt(JSON.parse(value).accessToken ?? '');
        return expiresAt !== null && expiresAt.getTime() - Date.now() > 60_000;
      }
    }
    return false;
  } catch {
    return false;
  }
}

/** The test account is a standing fixture (Release-Check/_shared/fixtures.md): register it once if missing. */
async function ensureTestAccount(baseURL: string, username: string, password: string, email: string): Promise<void> {
  const api = await request.newContext({ baseURL });
  try {
    const login = await api.post('/api/v1/auth/login', { data: { username, password } });
    if (login.ok()) return;
    const register = await api.post('/api/v1/auth/register', { data: { username, email, password } });
    if (!register.ok()) {
      throw new Error(
        `[e2e] 测试账号 ${username} 登录失败（${login.status()}），注册也失败（${register.status()}）：${await register.text()}\n` +
        '账号已存在但密码不对时，请修正 environments.json 里的密码。'
      );
    }
    console.log(`[e2e globalSetup] 已注册测试账号 ${username}`);
  } finally {
    await api.dispose();
  }
}

export default async function globalSetup(_config: FullConfig) {
  const { name: envName, base_url: BASE_URL, username, password, email } = getE2EConfig();
  const AUTH_STATE_PATH = getAuthStatePath(envName);

  // 锁定当前环境，确保整个测试运行期间 env 一致（即使 environments.json 中途被修改）
  process.env.E2E_ENV      = envName;
  process.env.E2E_BASE_URL = BASE_URL;
  process.env.E2E_USERNAME = username;
  process.env.E2E_PASSWORD = password;

  console.log(`[e2e globalSetup] 环境: ${envName} (${BASE_URL})`);

  // ── 前置快速检查：读 JWT exp，无需开浏览器 ────────────────────────────
  if (isAuthStateValid(AUTH_STATE_PATH)) {
    console.log('[e2e globalSetup] auth 有效（JWT 未过期），跳过登录');
    return;
  }
  console.log('[e2e globalSetup] auth 不存在或已过期，执行登录...');

  await ensureTestAccount(BASE_URL, username, password, email ?? `${username}@example.com`);

  const browser = await chromium.launch({ headless: process.env.HEADLESS === 'true' });
  try {
    const loginCtx = await browser.newContext({ ...devices['Desktop Chrome'], baseURL: BASE_URL });
    const page = await loginCtx.newPage();

    await page.goto('/login', { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.getByLabel('用户名或邮箱', { exact: true }).fill(username);
    await page.getByLabel('密码', { exact: true }).fill(password);
    await page.getByRole('button', { name: '登录', exact: true }).click();

    try {
      await expect(page.getByRole('heading', { level: 1, name: /^你好，/ })).toBeVisible({ timeout: 30000 });
    } catch {
      throw new Error(
        `[e2e] 自动登录失败，当前页面：${page.url()}\n` +
        `请检查 environments.json 中 "${envName}" 的凭据是否正确。`
      );
    }

    await loginCtx.storageState({ path: AUTH_STATE_PATH });
    console.log(`[e2e globalSetup] 登录成功，${AUTH_STATE_PATH} 已保存`);

    await loginCtx.close();
  } finally {
    await browser.close();
  }
}
