import { test } from 'node:test';
import assert from 'node:assert/strict';
import { suggestGuideFileName, checkGuidePath } from '../guide-name';
import { ParsedGuide } from '../parse-guide';

const cases: [string, string, string][] = [
  ['feature/native-voice-preview_Lei_20261016', 'Lei', 'Lei-native-voice-preview.md'],
  ['fix/agent-flow-db-conn-held-across-llm_yuehan_20261015', 'yuehan', 'yuehan-agent-flow-db-conn-held-across-llm.md'],
  ['feature-batch-agent-search-yosia-20261020', 'yosia', 'yosia-batch-agent-search.md'],
  ['change-intentcode-anthony-20261020', 'anthony', 'anthony-intentcode.md'],
  ['fix/text-test-system-time', 'someone', 'someone-text-test-system-time.md'],
  ['feat/detection-rules-advanced-ux', 'someone', 'someone-detection-rules-advanced-ux.md'],
  ['feature-outbound-test-phase-2-yosia-20261012-2', 'yosia', 'yosia-outbound-test-phase-2.md'],
  ['codex/issue-ai-tma-migration', 'wen.xu', 'wen.xu-issue-ai-tma-migration.md'],
  ['bugfix-llm-connection-pool-yosia-20261009', 'yosia.deshilkia', 'yosia.deshilkia-llm-connection-pool.md'],
  ['feature/realtime-thirdparty-tts_Lei_20261020', 'wanglei', 'wanglei-realtime-thirdparty-tts.md'],
  ['fix/agent-flow-lazy-client-names_yuehan_20261022', 'yuehan.wu', 'yuehan.wu-agent-flow-lazy-client-names.md'],
];

for (const [branch, author, expected] of cases) {
  test(`${branch} + ${author} → ${expected}`, () => {
    assert.equal(suggestGuideFileName(branch, author), expected);
  });
}

test('dash-joined last word is kept when it is not the author', () => {
  assert.equal(
    suggestGuideFileName('feature/decision-via-gateway-20261020', 'someone'),
    'someone-decision-via-gateway.md',
  );
});

test('branch person name differing from GitLab username is still stripped', () => {
  assert.equal(
    suggestGuideFileName('feature/native-voice-preview_Lei_20261016', 'lei.wang'),
    'lei.wang-native-voice-preview.md',
  );
});

const guide = (type: string, author: string): ParsedGuide => ({
  frontmatter: { type, author },
  body: '',
  sections: new Map(),
  unknownHeadings: [],
});

test('checkGuidePath: valid path has no issues', () => {
  assert.deepEqual(checkGuidePath('DEV-20261021/bugfix/yuehan-x.md', guide('bugfix', 'yuehan')), []);
});

test('checkGuidePath: bugfix guide under feature/ is rejected', () => {
  const issues = checkGuidePath('DEV-20261021/feature/yuehan-x.md', guide('bugfix', 'yuehan'));
  assert.ok(issues.some(i => i.rule === 'path' && i.severity === 'error'));
});

test('checkGuidePath: release folder not matching DEV-/HOTFIX- is rejected', () => {
  const issues = checkGuidePath('release-1/bugfix/yuehan-x.md', guide('bugfix', 'yuehan'));
  assert.ok(issues.some(i => i.rule === 'path'));
});

test('checkGuidePath: file name not starting with author is rejected', () => {
  const issues = checkGuidePath('HOTFIX-20261022/bugfix/x-yuehan.md', guide('bugfix', 'yuehan'));
  assert.ok(issues.some(i => i.rule === 'path'));
});
