#!/usr/bin/env node
/**
 * Report E2E automation coverage and enforce the production-safety gate.
 *
 * Coverage = (# case-IDs with an executable .feature tag) / (# documented cases,
 * excluding Backend-Unit / 后端单测 rows — those are proven by backend tests, not a
 * browser-automation gap, and are reported on a separate line).
 * Gate: a case classified P (prod-unsafe) or C (manual-only) MUST NOT have a feature.
 *
 * Usage:
 *   node core/runner/automation-coverage.mjs            # print report
 *   node core/runner/automation-coverage.mjs --min 80   # exit 1 if below 80% or gate violated
 *   node core/runner/automation-coverage.mjs --root DIR # scan a different tree (tests)
 */
import { buildCaseIndex } from './lib/case-index.mjs';
import { classify } from './lib/classify-rules.mjs';

const args = process.argv.slice(2);
const rootIdx = args.indexOf('--root');
const root = rootIdx >= 0 ? args[rootIdx + 1] : undefined;
const minIdx = args.indexOf('--min');
const min = minIdx >= 0 ? Number(args[minIdx + 1]) : null;
if (min !== null && Number.isNaN(min)) {
  console.error('FAIL: --min requires a numeric argument');
  process.exit(1);
}

const idx = buildCaseIndex(root);
const isBackend = (c) => classify(c.title, c.notes, c.executionType).code === 'BACKEND';
const scored = idx.cases.filter((c) => !isBackend(c));
const backendCount = idx.cases.length - scored.length;
const automated = scored.filter((c) => c.automated).length;
const pct = scored.length ? (100 * automated) / scored.length : 0;

// Per-module table
const byMod = new Map();
for (const c of idx.cases) {
  const m = byMod.get(c.module) || { total: 0, auto: 0, backend: 0 };
  if (isBackend(c)) m.backend++;
  else { m.total++; if (c.automated) m.auto++; }
  byMod.set(c.module, m);
}
console.log(`Automation coverage: ${automated}/${scored.length} = ${pct.toFixed(1)}%`);
if (backendCount) console.log(`后端单测 ${backendCount} 行（由后端测试覆盖，不计入）`);
console.log('\nPer-module (auto/total, sorted by gap):');
for (const [mod, m] of [...byMod].sort((a, b) => (b[1].total - b[1].auto) - (a[1].total - a[1].auto))) {
  const backendNote = m.backend ? `  （后端单测 ${m.backend} 行，不计入）` : '';
  console.log(`  ${String(m.auto).padStart(3)}/${String(m.total).padStart(3)}  gap=${String(m.total - m.auto).padStart(3)}  ${mod}${backendNote}`);
}

// Production-safety gate: PROD/FAULT cases must not be automated.
const violations = idx.cases.filter((c) => c.automated && ['PROD', 'FAULT'].includes(classify(c.title, c.notes).code));
if (violations.length) {
  console.error(`\nPRODUCTION-SAFETY GATE VIOLATION (${violations.length}): these cases write shared/prod state or require fault-injection but have a .feature:`);
  for (const v of violations) console.error(`  ${v.caseId}  [${classify(v.title, v.notes).code}]  ${v.title}`);
}

let failed = false;
if (min !== null && pct < min) { console.error(`\nFAIL: coverage ${pct.toFixed(1)}% < required ${min}%`); failed = true; }
if (violations.length) failed = true;
process.exit(failed ? 1 : 0);
