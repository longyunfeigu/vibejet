import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseGuide, GuideParseError } from '../parse-guide';

const EN = `---
type: feature
---
## Background and goal
why

## How to verify
field status equals "done"
`;

const CN = `---
type: feature
---
## 背景与目标
为什么

## 怎么算对
字段 status 等于 "done"
`;

test('parses frontmatter and maps English and Chinese headings to the same section ids', () => {
  const en = parseGuide(EN);
  const cn = parseGuide(CN);
  assert.equal(en.frontmatter.type, 'feature');
  assert.equal(cn.frontmatter.type, 'feature');
  assert.equal(en.sections.get('verify'), 'field status equals "done"');
  assert.equal(cn.sections.get('verify'), '字段 status 等于 "done"');
  assert.equal(en.sections.get('background'), 'why');
  assert.equal(cn.sections.get('background'), '为什么');
});

test('strips BOM and normalizes CRLF', () => {
  const g = parseGuide('﻿---\r\ntype: bugfix\r\n---\r\n## 怎么算对\r\nx');
  assert.equal(g.frontmatter.type, 'bugfix');
  assert.equal(g.sections.get('verify'), 'x');
});

test('throws GuideParseError when frontmatter is missing', () => {
  assert.throws(() => parseGuide('## 怎么算对\nx'), GuideParseError);
});

test('throws GuideParseError with the yaml reason when frontmatter is malformed', () => {
  assert.throws(
    () => parseGuide('---\ntype: [feature\n---\n## 怎么算对\nx'),
    (e: unknown) => e instanceof GuideParseError && /yaml/i.test((e as Error).message),
  );
});

test('collects unrecognized level-2 headings into unknownHeadings', () => {
  const g = parseGuide('---\ntype: feature\n---\n## Something else\ntext\n');
  assert.deepEqual(g.unknownHeadings, ['Something else']);
});
