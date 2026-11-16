import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import { execFileSync } from 'child_process';
import { fileURLToPath } from 'url';
import { buildCaseIndex } from '../../core/runner/lib/case-index.mjs';
import { classify, EXEC_TYPE, EXEC_TYPE_CN } from '../../core/runner/lib/classify-rules.mjs';
import { decideCode, patchCsv } from '../../core/runner/classify-cases.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, 'fixtures-backend-unit');
const LEGACY_ROOT = path.join(__dirname, 'fixtures');
const COVERAGE = path.join(__dirname, '../../core/runner/automation-coverage.mjs');
const FIXTURE_CSV = path.join(ROOT, 'modules/demo/feat/cases/manual-test-cases-cn.csv');

function runCoverage(root) {
  return execFileSync('node', [COVERAGE, '--root', root], { encoding: 'utf8' });
}

// ── classify-rules ───────────────────────────────────────────────────────

test('classify: 后端单测 column or Backend-Unit notes marker -> BACKEND', () => {
  assert.equal(EXEC_TYPE_CN.BACKEND, '后端单测');
  assert.equal(EXEC_TYPE.BACKEND, 'Backend-Unit');
  assert.equal(classify('Every table purged', '', '后端单测').code, 'BACKEND');
  assert.equal(classify('Every table purged', '', 'Backend-Unit').code, 'BACKEND');
  assert.equal(classify('Every table purged', 'Backend-Unit').code, 'BACKEND');
  assert.equal(classify('Every table purged', '对应验收：A25；由后端单测覆盖：test_account_deletion.py').code, 'BACKEND');
});

test('classify: BACKEND outranks PROD title, FAULT notes and manual pins', () => {
  assert.equal(classify('Upload published agent as template', '', '后端单测').code, 'BACKEND');
  assert.equal(classify('Rollback', 'requires fault injection of the DB', '后端单测').code, 'BACKEND');
  assert.equal(classify('Rollback', 'Manual-Fault-Injection; Backend-Unit').code, 'BACKEND');
});

test('classify regression: original three values keep their old classification', () => {
  // Passing the current column value changes nothing for the original vocabulary.
  for (const exec of ['', '自动化测试', '手工测试-产线高危', '手工测试-故障注入']) {
    assert.equal(classify('Render settings form', '', exec).code, 'AUTO');
    assert.equal(classify('Upload published agent as template', '', exec).code, 'PROD');
    assert.equal(classify('Fallback', 'requires fault injection of the TTS provider', exec).code, 'FAULT');
    assert.equal(classify('Any', 'Manual-Prod-Unsafe', exec).code, 'PROD');
    assert.equal(classify('Any', 'Manual-Fault-Injection', exec).code, 'FAULT');
  }
  // Automated rows that are *additionally* backed by backend tests stay AUTO.
  assert.equal(classify('Formula breakdown', '对应验收：A3；公式精确值另由后端单测覆盖').code, 'AUTO');
  assert.equal(classify('Bypass page', '对应验收：A18；由后端单测覆盖（页面看不到）；E2E 在接口层自动化').code, 'AUTO');
});

// ── classify-cases ───────────────────────────────────────────────────────

test('classify-cases: decideCode keeps 后端单测, otherwise unchanged precedence', () => {
  const idx = buildCaseIndex(ROOT);
  const byId = Object.fromEntries(idx.cases.map((c) => [c.caseId, decideCode(c)]));
  assert.deepEqual(
    Object.fromEntries(Object.entries(byId).map(([id, d]) => [id, d.bucket])),
    { 'BE-DEMO-001': 'Automated', 'BE-DEMO-002': 'AUTO', 'BE-DEMO-003': 'PROD', 'BE-DEMO-004': 'FAULT', 'BE-DEMO-005': 'BACKEND' },
  );
  // Even if a 后端单测 row were (wrongly) tagged in a feature, it is not rewritten to Automated.
  assert.equal(decideCode({ title: 'x', notes: '', executionType: '后端单测', automated: true }).code, 'BACKEND');
  // Automated wins over classify() for the original vocabulary (old behaviour).
  assert.equal(decideCode({ title: 'Upload published agent as template', notes: '', executionType: '手工测试-产线高危', automated: true }).code, 'AUTO');
});

test('classify-cases --write leaves every fixture row as-is (后端单测 not rewritten)', () => {
  const tmp = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'classify-')), 'manual-test-cases-cn.csv');
  fs.copyFileSync(FIXTURE_CSV, tmp);
  const codeById = new Map(buildCaseIndex(ROOT).cases.map((c) => [c.caseId, decideCode(c).code]));
  assert.equal(patchCsv(tmp, codeById, true), 0);
  assert.equal(fs.readFileSync(tmp, 'utf8'), fs.readFileSync(FIXTURE_CSV, 'utf8'));
});

test('classify-cases --write still rewrites drifted original values (old behaviour)', () => {
  const tmp = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'classify-')), 'manual-test-cases-cn.csv');
  // BE-DEMO-002 is an AUTO target but was hand-marked prod-unsafe; BE-DEMO-005 stays 后端单测.
  fs.writeFileSync(tmp, fs.readFileSync(FIXTURE_CSV, 'utf8').replace(
    'Show the empty state,positive,P1,自动化测试', 'Show the empty state,positive,P1,手工测试-产线高危'));
  const codeById = new Map(buildCaseIndex(ROOT).cases.map((c) => [c.caseId, decideCode(c).code]));
  assert.equal(patchCsv(tmp, codeById, true), 1);
  // patchCsv joins records without a final EOL (pre-existing behaviour), so compare trimmed.
  assert.equal(fs.readFileSync(tmp, 'utf8'), fs.readFileSync(FIXTURE_CSV, 'utf8').trimEnd());
});

// ── automation-coverage ──────────────────────────────────────────────────

test('coverage: 后端单测 rows leave the denominator and get their own line', () => {
  const out = runCoverage(ROOT);
  // 4 scored rows (AUTO x2, PROD, FAULT), 1 automated; BE-DEMO-005 excluded.
  assert.match(out, /^Automation coverage: 1\/4 = 25\.0%$/m);
  assert.match(out, /^后端单测 1 行（由后端测试覆盖，不计入）$/m);
  assert.match(out, /^ {4}1\/ {2}4 {2}gap= {2}3 {2}demo {2}（后端单测 1 行，不计入）$/m);
});

test('coverage regression: trees without 后端单测 print exactly as before', () => {
  const out = runCoverage(LEGACY_ROOT);
  assert.equal(out, [
    'Automation coverage: 1/3 = 33.3%',
    '',
    'Per-module (auto/total, sorted by gap):',
    '    1/  3  gap=  2  demo',
    '',
  ].join('\n'));
});
