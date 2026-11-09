import { test } from 'node:test';
import assert from 'node:assert/strict';
import { loadToolRegistry } from '../tool-registry';

test('reads backticked names from the first column and ignores header and separator rows', () => {
  const md = [
    '# Tools',
    '',
    '| Name | What it does | Read/Write |',
    '|---|---|---|',
    '| `browser` | Drive web UI | read |',
    '| `kubectl-readonly` | Inspect pods | read |',
    '| plain-text | not registered without backticks | read |',
  ].join('\n');
  assert.deepEqual([...loadToolRegistry(md)].sort(), ['browser', 'kubectl-readonly']);
});

test('returns empty set when the file has no table', () => {
  assert.equal(loadToolRegistry('# Tools\nnothing here').size, 0);
});
