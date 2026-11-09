import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as fs from 'fs';
import * as path from 'path';
import { parseGuide } from '../parse-guide';
import { extractCheckItems } from '../priority';
import { lintGuide, LintContext, LintIssue } from '../rules';

const FEATURE = fs.readFileSync(path.join(__dirname, 'fixtures', 'valid-feature.md'), 'utf-8');
const ctx: LintContext = { toolRegistry: new Set(['browser', 'api']), guideExists: () => false };

const lint = (text: string) => lintGuide(parseGuide(text), ctx);
const priorityIssues = (issues: LintIssue[]) => issues.filter(i => i.rule === 'priority-tag');
const withVerify = (verify: string) => FEATURE.replace(/(## 怎么算对\n)[\s\S]*?(?=\n## )/, `$1${verify}\n`);

test('extractCheckItems: reads tags in order, skips nested items and group headings', () => {
  const items = extractCheckItems([
    '**A. 列表页**',
    '',
    '1. [P0] 列表能打开',
    '   - 子项不算检查项',
    '2. [P2] 横向滚动时首列固定',
    '- [P1] 无序列表也认',
  ].join('\n'));
  assert.deepEqual(items.map(i => i.priority), ['P0', 'P2', 'P1']);
  assert.equal(items[0].text, '列表能打开');
});

test('extractCheckItems: an untagged item has priority null', () => {
  const items = extractCheckItems('1. 没有标签\n2. [P3] 标签不合法');
  assert.deepEqual(items.map(i => i.priority), [null, null]);
});

test('priority-tag: valid fixture with a P0 item has no issue', () => {
  assert.deepEqual(priorityIssues(lint(FEATURE)), []);
});

test('priority-tag: an untagged check item is an error', () => {
  const issues = priorityIssues(lint(withVerify('1. [P0] 有标签\n2. 没有标签')));
  assert.equal(issues.length, 1);
  assert.equal(issues[0].severity, 'error');
  assert.match(issues[0].message, /第 2 条/);
});

test('priority-tag: an invalid tag such as [P3] is an error', () => {
  const issues = priorityIssues(lint(withVerify('1. [P3] 标签不合法')));
  assert.ok(issues.some(i => i.severity === 'error'));
});

test('priority-tag: a verify section with no list items is an error', () => {
  const issues = priorityIssues(lint(withVerify('列表接口返回的每一项都有字段 last_call_at。')));
  assert.ok(issues.some(i => i.severity === 'error' && /列表/.test(i.message)));
});

test('priority-tag: a guide without any P0 item only gets a warning', () => {
  const issues = priorityIssues(lint(withVerify('1. [P1] 主要场景\n2. [P2] 小问题')));
  assert.equal(issues.length, 1);
  assert.equal(issues[0].severity, 'warning');
  assert.match(issues[0].message, /基本功能/);
});
