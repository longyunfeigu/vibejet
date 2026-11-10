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
