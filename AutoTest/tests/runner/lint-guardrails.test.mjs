import { test } from 'node:test';
import assert from 'node:assert/strict';
import { findApiCallViolations, countControlledWaits } from '../../core/runner/lib/guardrails.mjs';

test('flags page.request.* usage in step/page source', () => {
  const src = [
    'const r = await page.request.get("/api/agents");',
    'await page.request.delete(url);',
  ].join('\n');
  const v = findApiCallViolations('hotwords/steps/x.steps.ts', src);
  assert.equal(v.length, 2);
});

test('ignores comments and lines marked api-lint-exempt', () => {
  const src = [
    '// await page.request.get("/api/agents")',
    'await page.request.post(url); // api-lint-exempt',
  ].join('\n');
  assert.deepEqual(findApiCallViolations('x/steps/y.steps.ts', src), []);
});

test('counts controlledWait/workaroundSleep calls, ignores comments', () => {
  const src = [
    'await controlledWait(page, 500, "x");',
    '// await controlledWait(page, 500, "y")',
    'await workaroundSleep(page, 300, "z");',
  ].join('\n');
  assert.equal(countControlledWaits(src), 2);
});

// ── Check G / Check J: Backend-Unit (后端单测) execution type ──────────────

import { EXEC_TYPES_CN, collectFeatureCaseIds, findBackendUnitViolations } from '../../core/runner/lib/guardrails.mjs';

test('Check G vocabulary: adds 后端单测, keeps the original three, legacy values stay invalid', () => {
  for (const v of ['自动化测试', '手工测试-产线高危', '手工测试-故障注入', '后端单测']) {
    assert.ok(EXEC_TYPES_CN.includes(v), v);
  }
  assert.equal(EXEC_TYPES_CN.length, 4);
  for (const legacy of ['AutoTest', 'Manual', '手工测试', '手动测试', 'Backend-Unit']) {
    assert.ok(!EXEC_TYPES_CN.includes(legacy), legacy);
  }
});

test('collectFeatureCaseIds reads case-ID tags from feature source', () => {
  const src = '  @DEMO-FT-001 @smoke\n  Scenario: a\n  @DEMO-FT-018 @negative\n  Scenario: b\n';
  assert.deepEqual([...collectFeatureCaseIds(src)].sort(), ['DEMO-FT-001', 'DEMO-FT-018']);
});

test('Check J: 后端单测 row tagged in a .feature or without a test pointer is flagged', () => {
  const tagged = new Set(['DEMO-FT-031']);
  const row = (exec, notes, caseId = 'DEMO-FT-031') => ({ where: 'x.csv:2', caseId, exec, notes });
  const ok = '对应验收：A27；由后端单测覆盖：test_account_deletion.py::test_failure_rolls_back';
  assert.equal(findBackendUnitViolations(row('后端单测', ok), tagged).length, 1); // has a feature tag
  assert.deepEqual(findBackendUnitViolations(row('后端单测', ok, 'DEMO-FT-099'), tagged), []);
  assert.deepEqual(findBackendUnitViolations(row('后端单测', '对应验收：A27；见 test_account_deletion.py', 'DEMO-FT-099'), tagged), []);
  const noPointer = findBackendUnitViolations(row('后端单测', '对应验收：A27', 'DEMO-FT-099'), tagged);
  assert.equal(noPointer.length, 1);
  assert.match(noPointer[0], /Notes do not name the backend test/);
  assert.equal(findBackendUnitViolations(row('后端单测', '对应验收：A27'), tagged).length, 2);
});

test('Check J regression: original three values are never flagged, feature tag or not', () => {
  const tagged = new Set(['DEMO-FT-018']);
  for (const exec of ['自动化测试', '手工测试-产线高危', '手工测试-故障注入']) {
    assert.deepEqual(findBackendUnitViolations({ where: 'x', caseId: 'DEMO-FT-018', exec, notes: '' }, tagged), []);
  }
});
