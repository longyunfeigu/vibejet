import * as fs from 'fs';
import * as path from 'path';
import { defineConfig, devices } from '@playwright/test';
import { defineBddProject } from 'playwright-bdd';
import { getVoiceAgentConfig } from './env-config';

const voiceAgentConfig = getVoiceAgentConfig();

// 报告目录按环境隔离：report/test-reports-{env}/playwright/
const reportEnv = process.env.VOICE_AGENT_ENV ?? voiceAgentConfig.name;
const reportDir = `../report/test-reports-${reportEnv}/playwright`;

/**
 * Acting-user identity headers for API-direct mutations.
 *
 * The backend audit-log service (RD .../services/audit_log_service.py) rejects
 * agent/config writes with 401 "missing display identity" unless the request
 * carries the acting user's display name/email. The real frontend injects these
 * on every request (frontend/src/utils/http.ts -> getIdentityHeaders, sourced
 * from localStorage user_name/user_email set at login). Our REST-direct calls
 * (page.request / in-page fetch) bypass that path, so we replicate it here as
 * context-level extraHTTPHeaders — applied to all projects via the top-level
 * `use` block, covering page.request, in-page fetch and navigations alike.
 *
 * Source of truth: the same auth-state storageState the frontend wrote at login.
 * Env vars override for fresh CI runs where the state file is not yet present.
 */
function identityHeaders(env: string): Record<string, string> {
  const envName = process.env.X_USER_DISPLAY;
  const envEmail = process.env.X_USER_DISPLAY_EMAIL;
  let name = envName;
  let email = envEmail;
  if (!name || !email) {
    try {
      const statePath = path.join(__dirname, `auth-state-${env}.json`);
      const state = JSON.parse(fs.readFileSync(statePath, 'utf8')) as {
        origins?: { localStorage?: { name: string; value: string }[] }[];
      };
      for (const origin of state.origins ?? []) {
        for (const { name: k, value } of origin.localStorage ?? []) {
          if (!name && k === 'user_name') name = value;
          if (!email && k === 'user_email') email = value;
        }
      }
    } catch {
      // No state file yet (first run) — headers stay empty; global-setup writes
      // the state, and the next run reads the identity from it.
    }
  }
  const headers: Record<string, string> = {};
  if (name) headers['X-User-Display'] = name;
  if (email) headers['X-User-Display-Email'] = email;
  return headers;
}

// 公共 steps（跨模块复用）
const COMMON_STEPS = '../modules/common/steps/**/*.ts';

// Feature files are English-only (no .cn.feature companions). Excluded from execution:
//   *.pending.feature — scenarios written from PRD but code not yet implemented
//   *.cn.feature      — defensive guard only; these are no longer authored
// Only plain *.feature files (English, non-pending) are run by the test runner.
const featureGlob = (moduleGlob: string) =>
  moduleGlob.replace('**/*.feature', '**/!(*cn|*pending).feature');

export default defineConfig({
  timeout: 60000,
  // @slow scenarios call test.setTimeout() in their first Given step to override this.
  // The global value applies only to non-@slow tests.
  workers: parseInt(process.env.WORKERS ?? '1'),  // default 1; set WORKERS=N to parallelise across modules
  globalSetup: './global-setup.ts',
  outputDir: '../report/test-results',
  use: {
    headless: process.env.HEADLESS === 'true',  // default: headed; set HEADLESS=true for headless
    screenshot: 'only-on-failure',
    video: 'off',
    trace: 'on-first-retry',
    actionTimeout: 30000,
    // Inherited by every project. Makes API-direct writes carry the acting-user
    // identity the backend audit-log guard requires (see identityHeaders above).
    extraHTTPHeaders: identityHeaders(reportEnv),
  },
  reporter: [
    ['html', { outputFolder: reportDir, open: 'never' }],
    ['json', { outputFile: `${reportDir}/results.json` }],
    ...(process.env.E2E_RUNNER ? [['dot'] as ['dot']] : [['line'] as ['line']]),
  ],
  projects: [
    // ── BDD：全量入口 ────────────────────────────────────────────────────────
    {
      ...defineBddProject({
        name: 'bdd',
        features: featureGlob('../modules/**/*.feature'),
        featuresRoot: path.join(__dirname, '../modules'),
        steps: ['../modules/**/steps/**/*.ts'],
        outputDir: '../core/.gen-bdd',
      }),
      use: {
        ...devices['Desktop Chrome'],
        baseURL: voiceAgentConfig.base_url,
        storageState: path.join(__dirname, `auth-state-${reportEnv}.json`),
        // 允許麥克風（voice-agent 場景需要），fake device 避免系統彈窗
        permissions: ['microphone'],
        launchOptions: { args: ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'] },
      },
    },
    // ── 按模块运行 ───────────────────────────────────────────────────────────
    {
      ...defineBddProject({
        name: 'knowledge-base',
        features: featureGlob('../modules/knowledge-base/**/*.feature'),
        featuresRoot: path.join(__dirname, '../modules/knowledge-base'),
        steps: ['../modules/knowledge-base/**/steps/**/*.ts', COMMON_STEPS],
        outputDir: '../core/.gen-bdd/knowledge-base',
      }),
      use: {
        ...devices['Desktop Chrome'],
        baseURL: voiceAgentConfig.base_url,
        storageState: path.join(__dirname, `auth-state-${reportEnv}.json`),
      },
    },
    {
      ...defineBddProject({
        name: 'voice-agent',
        features: featureGlob('../modules/voice-agent/**/*.feature'),
        featuresRoot: path.join(__dirname, '../modules/voice-agent'),
        steps: ['../modules/voice-agent/**/steps/**/*.ts', COMMON_STEPS],
        outputDir: '../core/.gen-bdd/voice-agent',
      }),
      // Run scenarios within the same spec file in parallel; voice-agent
      // scenarios use per-case dedicated agents (see AutoTest CLAUDE.md
      // "modify/create E2E case must use dedicated agent" rule) so they
      // are safe to interleave.
      fullyParallel: true,
      use: {
        ...devices['Desktop Chrome'],
        baseURL: voiceAgentConfig.base_url,
        storageState: path.join(__dirname, `auth-state-${reportEnv}.json`),
        permissions: ['microphone'],
        launchOptions: {
          args: [
            '--use-fake-device-for-media-stream',
            '--use-fake-ui-for-media-stream',
            // Inject a real speech file so platform VAD fires and records Server Response Latency.
            // File = 2s speech + 25s silence → Chrome loops every 27s, triggering VAD once per call.
            `--use-file-for-fake-audio-capture=${path.resolve(__dirname, '../core/helpers/e2e-test-speech.wav')}`,
          ],
        },
      },
    },
    {
      name: 'capability-e2e',
      testDir: path.join(__dirname, '../modules/voice-agent/capability-e2e'),
      testMatch: '**/*.spec.ts',
      fullyParallel: false,
      use: {
        ...devices['Desktop Chrome'],
        baseURL: voiceAgentConfig.base_url,
        storageState: path.join(__dirname, `auth-state-${reportEnv}.json`),
        permissions: ['microphone'],
        launchOptions: { args: ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'] },
      },
    },
    {
      // Open-loop production-call replay: play a recording's user channel into a
      // live agent through the browser. One room at a time (no parallel).
      name: 'call-replay',
      testDir: path.join(__dirname, '../modules/voice-agent/call-replay'),
      testMatch: '**/*.spec.ts',
      fullyParallel: false,
      use: {
        ...devices['Desktop Chrome'],
        baseURL: voiceAgentConfig.base_url,
        storageState: path.join(__dirname, `auth-state-${reportEnv}.json`),
        permissions: ['microphone'],
        launchOptions: { args: ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'] },
      },
    },
    {
      ...defineBddProject({
        name: 'ai-simulation',
        features: featureGlob('../modules/ai-simulation/**/*.feature'),
        featuresRoot: path.join(__dirname, '../modules/ai-simulation'),
        steps: ['../modules/ai-simulation/**/steps/**/*.ts', COMMON_STEPS],
        outputDir: '../core/.gen-bdd/ai-simulation',
      }),
      use: {
        ...devices['Desktop Chrome'],
        baseURL: voiceAgentConfig.base_url,
        storageState: path.join(__dirname, `auth-state-${reportEnv}.json`),
        permissions: ['microphone'],
        launchOptions: {
          args: ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'],
        },
      },
    },
    {
      ...defineBddProject({
        name: 'mcp-registry',
        features: featureGlob('../modules/mcp-registry/**/*.feature'),
        featuresRoot: path.join(__dirname, '../modules/mcp-registry'),
        steps: ['../modules/mcp-registry/**/steps/**/*.ts', COMMON_STEPS],
        outputDir: '../core/.gen-bdd/mcp-registry',
      }),
      use: {
        ...devices['Desktop Chrome'],
        baseURL: voiceAgentConfig.base_url,
        storageState: path.join(__dirname, `auth-state-${reportEnv}.json`),
      },
    },
    {
      ...defineBddProject({
        name: 'whatsapp',
        features: featureGlob('../modules/whatsapp/**/*.feature'),
        featuresRoot: path.join(__dirname, '../modules/whatsapp'),
        steps: ['../modules/whatsapp/**/steps/**/*.ts', COMMON_STEPS],
        outputDir: '../core/.gen-bdd/whatsapp',
      }),
      use: {
        ...devices['Desktop Chrome'],
        baseURL: voiceAgentConfig.base_url,
        storageState: path.join(__dirname, `auth-state-${reportEnv}.json`),
      },
    },
    {
      ...defineBddProject({
        name: 'phone-number',
        features: featureGlob('../modules/phone-number/**/*.feature'),
        featuresRoot: path.join(__dirname, '../modules/phone-number'),
        steps: ['../modules/phone-number/**/steps/**/*.ts', COMMON_STEPS],
        outputDir: '../core/.gen-bdd/phone-number',
      }),
      use: {
        ...devices['Desktop Chrome'],
        baseURL: voiceAgentConfig.base_url,
        storageState: path.join(__dirname, `auth-state-${reportEnv}.json`),
      },
    },
  ],
});
