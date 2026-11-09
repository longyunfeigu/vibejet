/**
 * Voice Agent Global Setup
 *
 * 在所有 voice-agent 测试开始前验证 auth-state 是否有效。
 * 若 auth 已过期或不存在，自动执行 SSO 登录并保存新的 auth-state。
 *
 * 环境配置通过 env-config.ts 读取（支持多环境）：
 *   npm run test:va -- --env sg   # 使用 sg 环境
 *   npm run test:va               # 使用 environments.json 中的 default 环境
 */

import { chromium, devices, FullConfig, expect } from '@playwright/test';
import * as fs from 'fs';
import { getVoiceAgentConfig, getAuthStatePath } from './env-config';

const isLoginUrl = (url: string) =>
  url.includes('/login') || url.includes('/select-org') || url.includes('auth.');

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
 * Fast pre-check: read auth-state cookies and verify the access_token is not expired.
 * Returns true if the token is still valid (> 60s remaining), false otherwise.
 * Does NOT launch a browser — completes in < 5ms.
 */
function isAuthStateValid(authStatePath: string): boolean {
  if (!fs.existsSync(authStatePath)) return false;
  try {
    const state = JSON.parse(fs.readFileSync(authStatePath, 'utf-8'));
    const cookies: Array<{ name: string; value: string }> = state.cookies ?? [];
    const accessToken = cookies.find(c => c.name === 'access_token')?.value;
    if (!accessToken) return false;
    const expiresAt = jwtExpiresAt(accessToken);
    if (!expiresAt) return false;
    const remainingMs = expiresAt.getTime() - Date.now();
    return remainingMs > 60_000; // valid if > 1 min remaining
  } catch {
    return false;
  }
}

export default async function globalSetup(_config: FullConfig) {
  const {
    name: envName,
    base_url: BASE_URL,
    username,
    password,
    org,
    understand_language,
    speak_language,
    voice,
    share_code,
    livekit_url,
    openai_api_key,
    openai_base_url,
    backend_api_url,
    sip_bridge_host,
  } = getVoiceAgentConfig();
  const AUTH_STATE_PATH = getAuthStatePath(envName);

  // 锁定当前环境，确保整个测试运行期间 env 一致（即使 environments.json 中途被修改）
  process.env.VOICE_AGENT_ENV                 = envName;
  process.env.VOICE_AGENT_BASE_URL            = BASE_URL;
  process.env.VOICE_AGENT_USERNAME            = username;
  process.env.VOICE_AGENT_PASSWORD            = password;
  process.env.VOICE_AGENT_ORG                 = org;
  if (understand_language) process.env.VOICE_AGENT_UNDERSTAND_LANGUAGE = understand_language;
  if (speak_language)      process.env.VOICE_AGENT_SPEAK_LANGUAGE       = speak_language;
  if (voice)               process.env.VOICE_AGENT_VOICE                = voice;
  if (share_code)          process.env.VOICE_AGENT_SHARE_CODE           = share_code;
  if (livekit_url)         process.env.LIVEKIT_URL                      = String(livekit_url);
  if (openai_api_key)      process.env.OPENAI_API_KEY                   = String(openai_api_key);
  if (openai_base_url)     process.env.OPENAI_BASE_URL                  = String(openai_base_url);
  if (backend_api_url)     process.env.BACKEND_API_URL                  = String(backend_api_url);
  if (sip_bridge_host)     process.env.SIP_BRIDGE_HOST                  = String(sip_bridge_host);

  console.log(`[voice-agent globalSetup] 环境: ${envName} (${BASE_URL})`);

  // ── 前置快速检查：读 JWT exp，无需开浏览器 ────────────────────────────
  if (isAuthStateValid(AUTH_STATE_PATH)) {
    console.log('[voice-agent globalSetup] auth 有效（JWT 未过期），跳过登录');
    return;
  }
  console.log('[voice-agent globalSetup] auth 不存在或已过期，执行登录...');

  const browser = await chromium.launch({ headless: process.env.HEADLESS === 'true' });

  try {
    // ── JWT 已失效，执行 SSO 自动登录 ────────────────────────────────────
    const loginCtx = await browser.newContext({ ...devices['Desktop Chrome'] });
    const page = await loginCtx.newPage();

    console.log('[voice-agent globalSetup] 正在登录...');

    await page.goto(BASE_URL, { waitUntil: 'domcontentloaded', timeout: 60000 });

    // Wait for SSO button (app may need a moment to load)
    const ssoBtn = page.getByRole('button', { name: /Sign in with Single Sign-On/i });
    await expect(ssoBtn).toBeVisible({ timeout: 30000 });
    await ssoBtn.click();

    // Zitadel page 1: username → Enter submits (button stays disabled until typed)
    const loginNameInput = page.locator('input[name="loginName"]');
    await expect(loginNameInput).toBeVisible({ timeout: 30000 });
    await loginNameInput.pressSequentially(username, { delay: 30 });
    await loginNameInput.press('Enter');

    // Zitadel page 2: password → Enter submits
    const passwordInput = page.locator('input[name="password"]');
    await expect(passwordInput).toBeVisible({ timeout: 30000 });
    await passwordInput.pressSequentially(password, { delay: 30 });
    await passwordInput.press('Enter');

    // Org selector — two possible states after OIDC callback:
    //   (a) Multi-org user → /select-org page shows org buttons → click the target org
    //   (b) Single-org user → auto-selected → already on /overview
    // Two picker UIs exist across deployments:
    //   - Legacy: org buttons render as <button role="listitem" aria-label="Select …">
    //     — the explicit role="listitem" overrides the implicit button role, so
    //     getByRole('button', {...}) does NOT match; use getByLabel instead.
    //   - Current ("Choose your workspace"): each workspace is a plain <button>
    //     inside a div[role="list"], with the org name in a child span (no aria-label).
    // Race between seeing either picker and seeing the overview h1.
    const orgButtonLegacy = page.getByLabel(`Select ${org}`);
    const orgCard = page.getByRole('button').filter({ has: page.getByText(org, { exact: true }) });
    const overviewH1 = page.locator('h1').filter({ hasText: 'Operations Console' });
    const arrived = await Promise.race([
      orgButtonLegacy.waitFor({ timeout: 30000 }).then(() => 'legacy' as const),
      orgCard.first().waitFor({ timeout: 30000 }).then(() => 'card' as const),
      overviewH1.waitFor({ timeout: 30000 }).then(() => 'overview' as const),
    ]).catch(() => null);

    if (arrived === 'legacy') {
      await orgButtonLegacy.click();
    } else if (arrived === 'card') {
      await orgCard.first().click();
    }

    try {
      await expect(overviewH1).toBeVisible({ timeout: 30000 });
    } catch {
      throw new Error(
        `[voice-agent] 自动登录失败，当前页面：${page.url()}\n` +
        `请检查 environments.json 中 "${envName}" 的凭据是否正确。`
      );
    }

    await loginCtx.storageState({ path: AUTH_STATE_PATH });
    console.log(`[voice-agent globalSetup] 登录成功，${AUTH_STATE_PATH} 已保存`);

    await loginCtx.close();
  } finally {
    await browser.close();
  }
}
