#!/usr/bin/env node
/**
 * Generate a CSV of failed cases from a Playwright JSON report.
 *
 * Reads report/test-reports-{env}/playwright/results.json and writes
 * report/test-results/failed-cases-{env}-{YYYYMMDD-HHMMSS}.csv with columns:
 *   用例名称, 测试目的, 测试步骤, 失败原因
 *
 * Only produced when there is at least one failed case; all-pass runs write nothing.
 * Usage: node core/runner/gen-failed-cases-csv.mjs <env>
 */
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const AUTOTEST_ROOT = path.resolve(__dirname, '../..');

const env = process.argv[2] || process.env.VOICE_AGENT_ENV || 'sg';
const resultsPath = path.join(
  AUTOTEST_ROOT,
  `report/test-reports-${env}/playwright/results.json`
);
const outDir = path.join(AUTOTEST_ROOT, 'report/test-results');

const CASE_ID_RE = /^[A-Z]+-[A-Z0-9]+-\d+$/;
const STEP_KEYWORD_RE = /^(Given|When|Then|And|But|假如|当|那么|而且|并且|但是)\b/;
const ANSI_RE = /\[[0-9;]*m/g;
const MAX_REASON_LEN = 500;

function stripAnsi(s) {
  return String(s || '').replace(ANSI_RE, '');
}

/** Collect every spec across the nested suite tree. */
function collectSpecs(suite, acc) {
  for (const spec of suite.specs || []) acc.push(spec);
  for (const child of suite.suites || []) collectSpecs(child, acc);
  return acc;
}

/** Pick the final (non-skipped) result for a test, preferring a failed one. */
function finalResult(test) {
  const results = test.results || [];
  const failed = results.find((r) => r.status === 'failed' || r.status === 'timedOut');
  return failed || results[results.length - 1] || null;
}

function caseName(spec) {
  const ids = (spec.tags || [])
    .filter((t) => CASE_ID_RE.test(t))
    .map((t) => `@${t}`)
    .join('/');
  return ids ? `${ids} ${spec.title}` : spec.title;
}

function stepsText(result) {
  const titles = (result.steps || [])
    .map((s) => (s.title || '').trim())
    .filter((t) => STEP_KEYWORD_RE.test(t));
  return titles.join(' / ');
}

function reasonText(result) {
  const msg = result.errors?.[0]?.message ?? result.error?.message ?? '';
  const clean = stripAnsi(msg).replace(/\s+/g, ' ').trim();
  return clean.length > MAX_REASON_LEN ? clean.slice(0, MAX_REASON_LEN) + '…' : clean;
}

function csvCell(value) {
  const s = String(value ?? '');
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function pad2(n) {
  return String(n).padStart(2, '0');
}

function timestamp() {
  const d = new Date();
  return (
    `${d.getFullYear()}${pad2(d.getMonth() + 1)}${pad2(d.getDate())}` +
    `-${pad2(d.getHours())}${pad2(d.getMinutes())}${pad2(d.getSeconds())}`
  );
}

function main() {
  if (!fs.existsSync(resultsPath)) {
    console.log(`[failed-cases-csv] no results.json at ${resultsPath}, skipped.`);
    return;
  }

  const report = JSON.parse(fs.readFileSync(resultsPath, 'utf-8'));
  const specs = (report.suites || []).reduce((acc, s) => collectSpecs(s, acc), []);

  const rows = [];
  for (const spec of specs) {
    if (spec.ok) continue; // only failed specs
    for (const test of spec.tests || []) {
      if (test.status === 'skipped' || test.status === 'expected') continue;
      const result = finalResult(test);
      if (!result || (result.status !== 'failed' && result.status !== 'timedOut')) continue;
      rows.push({
        name: caseName(spec),
        purpose: spec.title,
        steps: stepsText(result),
        reason: reasonText(result),
      });
    }
  }

  if (rows.length === 0) {
    console.log('[failed-cases-csv] no failed cases, no CSV written.');
    return;
  }

  fs.mkdirSync(outDir, { recursive: true });
  const outPath = path.join(outDir, `failed-cases-${env}-${timestamp()}.csv`);
  const header = ['用例名称', '测试目的', '测试步骤', '失败原因'];
  const lines = [header.map(csvCell).join(',')];
  for (const r of rows) {
    lines.push([r.name, r.purpose, r.steps, r.reason].map(csvCell).join(','));
  }
  // UTF-8 BOM so Excel opens Chinese correctly.
  fs.writeFileSync(outPath, '﻿' + lines.join('\r\n') + '\r\n', 'utf-8');
  console.log(`[failed-cases-csv] ${rows.length} failed case(s) → ${path.relative(AUTOTEST_ROOT, outPath)}`);
}

main();
