import * as path from 'path';
import { defineConfig, devices } from '@playwright/test';
import { defineBddProject } from 'playwright-bdd';
import { getE2EConfig } from './env-config';

const e2eConfig = getE2EConfig();

// 报告目录按环境隔离：report/test-reports-{env}/playwright/
const reportEnv = process.env.E2E_ENV ?? e2eConfig.name;
const reportDir = `../report/test-reports-${reportEnv}/playwright`;

// Every project runs signed in as the test account (state written by global-setup.ts).
const signedInBrowser = {
  ...devices['Desktop Chrome'],
  baseURL: e2eConfig.base_url,
  storageState: path.join(__dirname, `auth-state-${reportEnv}.json`),
};

// 公共 steps（跨模块复用）
const COMMON_STEPS = '../modules/common/steps/**/*.ts';

// Feature files are English-only (no .cn.feature companions). Excluded from execution:
//   *.pending.feature — scenarios written from PRD but code not yet implemented
//   *.cn.feature      — defensive guard only; these are not authored
// Only plain *.feature files (English, non-pending) are run by the test runner.
const featureGlob = (moduleGlob: string) =>
  moduleGlob.replace('**/*.feature', '**/!(*cn|*pending).feature');

// ── 按模块运行 ───────────────────────────────────────────────────────────
const moduleProject = (name: string) => ({
  ...defineBddProject({
    name,
    features: featureGlob(`../modules/${name}/**/*.feature`),
    featuresRoot: path.join(__dirname, `../modules/${name}`),
    steps: [`../modules/${name}/**/steps/**/*.ts`, COMMON_STEPS],
    outputDir: `../core/.gen-bdd/${name}`,
  }),
  use: signedInBrowser,
});

export default defineConfig({
  timeout: 60000,
  // Scenarios tagged @slow get 3x this timeout via playwright-bdd's built-in @slow tag (test.slow()).
  workers: parseInt(process.env.WORKERS ?? '1'),  // default 1; set WORKERS=N to parallelise
  globalSetup: './global-setup.ts',
  // Playwright wipes outputDir on every run — keep it apart from report/test-results/,
  // where gen-failed-cases-csv.mjs accumulates failed-case CSV history.
  outputDir: '../report/test-artifacts',
  use: {
    headless: process.env.HEADLESS === 'true',  // default: headed; set HEADLESS=true for headless
    screenshot: 'only-on-failure',
    video: 'off',
    trace: 'on-first-retry',
    actionTimeout: 30000,
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
      use: signedInBrowser,
    },
    moduleProject('auth'),
    moduleProject('home'),
  ],
});
