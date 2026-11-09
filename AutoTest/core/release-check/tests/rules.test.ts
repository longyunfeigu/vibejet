import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as fs from 'fs';
import * as path from 'path';
import { parseGuide } from '../parse-guide';
import { lintGuide, LintContext, LintIssue } from '../rules';

const FIXTURES = path.join(__dirname, 'fixtures');
const read = (name: string) => fs.readFileSync(path.join(FIXTURES, name), 'utf-8');
const FEATURE = read('valid-feature.md');
const BUGFIX = read('valid-bugfix.md');

const ctx: LintContext = {
  toolRegistry: new Set(['browser', 'api']),
  guideExists: p => p === 'DEV-20261014/feature/alice-old.md',
};

const lint = (text: string) => lintGuide(parseGuide(text), ctx);
const errors = (issues: LintIssue[]) => issues.filter(i => i.severity === 'error');
const rulesOf = (issues: LintIssue[]) => errors(issues).map(i => i.rule);

test('valid fixtures produce no errors', () => {
  assert.deepEqual(errors(lint(FEATURE)), []);
  assert.deepEqual(errors(lint(BUGFIX)), []);
});

test('frontmatter: rejects unknown service', () => {
  const text = FEATURE.replace('services: [voiceAgent.backend]', 'services: [voiceAgent.nope]');
  const frontmatterErrors = errors(lint(text)).filter(i => i.rule === 'frontmatter');
  assert.equal(frontmatterErrors.length, 1);
});

test('frontmatter: a guide has no envs field', () => {
  assert.ok(!/^envs:/m.test(FEATURE));
  assert.deepEqual(errors(lint(FEATURE)), []);
});

test('sections: bugfix without reproduction conditions is accepted', () => {
  const text = BUGFIX.replace(/## 复现条件\n(?:[^#\n][^\n]*\n|\n)*/, '');
  assert.ok(!text.includes('## 复现条件'));
  assert.deepEqual(errors(lint(text)), []);
});

test('sections: bugfix without old-behavior is rejected', () => {
  const text = BUGFIX.replace(/## 旧版本的错误现象\n[^\n]*\n/, '');
  assert.ok(rulesOf(lint(text)).includes('sections'));
});

test('sections: section containing only an HTML comment counts as empty', () => {
  const text = FEATURE.replace('Agent 列表页。', '<!-- 写入口 -->');
  assert.ok(rulesOf(lint(text)).includes('sections'));
});

test('vague-phrase: flagged in verify section', () => {
  const text = FEATURE.replace(/(## 怎么算对\n)[^\n]*/, '$1功能正常');
  assert.ok(rulesOf(lint(text)).includes('vague-phrase'));
});

test('vague-phrase: not flagged in pitfalls section', () => {
  const text = FEATURE.replace(/(## 容易误判的地方\n)[^\n]*/, '$1页面闪一下但功能正常，不算失败');
  assert.ok(!rulesOf(lint(text)).includes('vague-phrase'));
});

test('not-self-contained: flags 群消息', () => {
  const text = FEATURE.replace('无需造数据，只读。', '数据见群消息。');
  assert.ok(rulesOf(lint(text)).includes('not-self-contained'));
});

test('hardcoded-env: flags https://demo.wiz.ai/x and 10.0.0.12', () => {
  const url = FEATURE.replace('Agent 列表页。', '打开 https://demo.wiz.ai/x');
  const ip = FEATURE.replace('Agent 列表页。', '连 10.0.0.12');
  assert.ok(rulesOf(lint(url)).includes('hardcoded-env'));
  assert.ok(rulesOf(lint(ip)).includes('hardcoded-env'));
});

test('hardcoded-env: allows https://wiz-ai.sg.larksuite.com/docx/abc', () => {
  const text = FEATURE.replace('Agent 列表页。', 'Agent 列表页，PRD 见 https://wiz-ai.sg.larksuite.com/docx/abc');
  assert.ok(!rulesOf(lint(text)).includes('hardcoded-env'));
});

test('unregistered-tool: flags tool missing from registry', () => {
  const text = FEATURE.replace('tools: [browser]', 'tools: [browser, telepathy]');
  assert.ok(rulesOf(lint(text)).includes('unregistered-tool'));
});

test('cost-estimate: costly without cost_estimate is an error', () => {
  const text = FEATURE.replace('safety: readonly', 'safety: costly');
  assert.ok(rulesOf(lint(text)).includes('cost-estimate'));
  const withEstimate = text.replace('risk: low', 'risk: low\ncost_estimate: 3 calls');
  assert.ok(!rulesOf(lint(withEstimate)).includes('cost-estimate'));
});

test('dry_run is not required: a guide without it gets no issue at all', () => {
  const text = FEATURE.replace(/dry_run:\n(  .*\n)+/, '');
  assert.deepEqual(lint(text), []);
});

test('supersedes: non-existent path is an error', () => {
  const bad = FEATURE.replace('risk: low', 'risk: low\nsupersedes: DEV-20261014/feature/alice-missing.md');
  const good = FEATURE.replace('risk: low', 'risk: low\nsupersedes: DEV-20261014/feature/alice-old.md');
  assert.ok(rulesOf(lint(bad)).includes('supersedes'));
  assert.ok(!rulesOf(lint(good)).includes('supersedes'));
});

test('hardcoded-env: flags hosts in backticks, without protocol, and before punctuation', () => {
  for (const snippet of ['`https://demo.wiz.ai`', 'demo.wiz.ai', 'https://demo.wiz.ai, then', '打开 https://demo.talkbots.cn。', '<https://demo.wiz.ai>']) {
    const text = FEATURE.replace('Agent 列表页。', snippet);
    assert.ok(rulesOf(lint(text)).includes('hardcoded-env'), snippet);
  }
});

test('hardcoded-env and not-self-contained: checked in unknown sections and before the first heading', () => {
  const unknownSection = `${FEATURE}\n## Notes\n连 10.0.0.12，数据见群消息\n`;
  const preamble = FEATURE.replace('## 背景与目标', '# Title\n连 10.0.0.12，数据见群消息\n\n## 背景与目标');
  for (const text of [unknownSection, preamble]) {
    const rules = rulesOf(lint(text));
    assert.ok(rules.includes('hardcoded-env'));
    assert.ok(rules.includes('not-self-contained'));
  }
});

test('unknown-heading: an unrecognized level-2 heading is a warning', () => {
  const issues = lint(`${FEATURE}\n## How to verify (怎么算对)\nx\n`);
  assert.ok(issues.some(i => i.rule === 'unknown-heading' && i.severity === 'warning'));
});

test('not-self-contained: a UI button named 确认 is not flagged', () => {
  const text = FEATURE.replace('Agent 列表页。', 'Agent 列表页，找到「确认」按钮并点击。');
  assert.ok(!rulesOf(lint(text)).includes('not-self-contained'));
});

test('not-self-contained: asking a person to confirm is flagged', () => {
  const text = FEATURE.replace('无需造数据，只读。', '数据找研发确认一下。');
  assert.ok(rulesOf(lint(text)).includes('not-self-contained'));
});

const warnings = (issues: LintIssue[]) => issues.filter(i => i.severity === 'warning').map(i => i.rule);

test('verdict-override: 不适用 in verify is an error', () => {
  const text = FEATURE.replace('值为 ISO 时间或 null。', '值为 ISO 时间或 null。没有数据时本条判「不适用」。');
  assert.ok(rulesOf(lint(text)).includes('verdict-override'));
});

test('verdict-override: not applicable in must-not-break is an error', () => {
  const text = FEATURE.replace('列表分页数量不变。', 'Paging is unchanged; not applicable when there is no traffic.');
  assert.ok(rulesOf(lint(text)).includes('verdict-override'));
});

test('verdict-override: 不适用 in pitfalls is allowed', () => {
  const text = FEATURE.replace('从未打过电话的 agent 显示「-」是正确的。', '这个开关不适用于外呼 agent，不算失败。');
  assert.ok(!rulesOf(lint(text)).includes('verdict-override'));
});

test('reproduce-old: asking to reproduce on the old version is a warning, not an error', () => {
  const text = BUGFIX.replace('状态码全部为 200。', '状态码全部为 200；先在旧版本上复现 500 再对比。');
  const issues = lint(text);
  assert.ok(warnings(issues).includes('reproduce-old'));
  assert.ok(!rulesOf(issues).includes('reproduce-old'));
});

test('reproduce-old: the old-behavior section may describe the old bug', () => {
  assert.ok(!warnings(lint(BUGFIX)).includes('reproduce-old'));
});

test('cost-mismatch: no-call estimate but the guide places a call', () => {
  const costly = FEATURE
    .replace('safety: readonly', 'safety: costly\ncost_estimate: 约 6 轮文字对话；不打电话')
    .replace('列表分页数量不变。', 'Live Test 页打一通测试电话，开场白不变。');
  assert.ok(warnings(lint(costly)).includes('cost-mismatch'));
});

test('cost-mismatch: no-call estimate with ai-simulation-call tool', () => {
  const costly = FEATURE
    .replace('safety: readonly', 'safety: costly\ncost_estimate: no calls')
    .replace('tools: [browser]', 'tools: [browser, ai-simulation-call]');
  assert.ok(warnings(lint(costly)).includes('cost-mismatch'));
});

test('cost-mismatch: an estimate that counts calls is fine', () => {
  const costly = FEATURE
    .replace('safety: readonly', 'safety: costly\ncost_estimate: 2 calls')
    .replace('列表分页数量不变。', '打一通测试电话，开场白不变。');
  assert.ok(!warnings(lint(costly)).includes('cost-mismatch'));
});

const withP0 = (item: string) =>
  FEATURE.replace('1. [P0] 列表接口返回的每一项都有字段 last_call_at，值为 ISO 时间或 null。', `1. [P0] ${item}`);

test('p0-direct: P0 that stops a service is rejected', () => {
  assert.ok(rulesOf(lint(withP0('暂停 flow-backend 服务 30 秒，guardrail 重试步不卡住。'))).includes('p0-direct'));
  assert.ok(rulesOf(lint(withP0('Scale the flow-backend deployment to 0 and check the retry step.'))).includes('p0-direct'));
});

test('p0-direct: P0 that observes for hours is rejected', () => {
  assert.ok(rulesOf(lint(withP0('连续观察 4 小时，日志里没有 POOL_GUARD。'))).includes('p0-direct'));
  assert.ok(rulesOf(lint(withP0('Observe for 4 hours; no POOL_GUARD lines.'))).includes('p0-direct'));
});

test('p0-direct: P0 that relies on business traffic is rejected', () => {
  assert.ok(rulesOf(lint(withP0('有业务流量时，连接池占用下限为 0。'))).includes('p0-direct'));
});

test('p0-direct: P0 that touches another organization is rejected', () => {
  assert.ok(rulesOf(lint(withP0('用其他企业的账号删除该任务，返回 403。'))).includes('p0-direct'));
});

test('p0-direct: the same text on a P1 item is allowed', () => {
  const text = FEATURE.replace('1. [P0] 列表接口返回的每一项都有字段 last_call_at，值为 ISO 时间或 null。',
    '1. [P0] 列表接口返回的每一项都有字段 last_call_at。\n2. [P1] 连续观察 4 小时，日志里没有 POOL_GUARD。');
  assert.ok(!rulesOf(lint(text)).includes('p0-direct'));
});

test('p0-direct: a time window in the data is not an observation', () => {
  assert.ok(!rulesOf(lint(withP0('GET /api/calls?hours=24 返回最近 24 小时的通话，状态码 200。'))).includes('p0-direct'));
});

test('frontmatter: requires accepts the documented entry kinds', () => {
  const text = FEATURE.replace('tools: [browser]',
    'tools: [browser]\nrequires: [gray:gpt-live, model:gpt-realtime, "model:audioe2e|kausap", service:template-middleware-backend, outbound]');
  assert.deepEqual(errors(lint(text)), []);
});

test('frontmatter: requires rejects an entry without a kind', () => {
  const text = FEATURE.replace('tools: [browser]', 'tools: [browser]\nrequires: [gpt-live]');
  assert.ok(rulesOf(lint(text)).includes('frontmatter'));
});

test('frontmatter: requires must be a list', () => {
  const text = FEATURE.replace('tools: [browser]', 'tools: [browser]\nrequires: gray:gpt-live');
  assert.ok(rulesOf(lint(text)).includes('frontmatter'));
});

test('p0-direct: another organization named as the second QA organization is allowed', () => {
  assert.ok(!rulesOf(lint(withP0('用 AI Builder Sandbox 4 的账号查，别的企业看不到这个任务，返回 404。'))).includes('p0-direct'));
  assert.ok(!rulesOf(lint(withP0('Another organization (AI Builder Sandbox 4) cannot read it: 404.'))).includes('p0-direct'));
});

test('frontmatter: regression may be omitted (defaults to false)', () => {
  const text = FEATURE.replace(/^regression: .*\n/m, '');
  assert.ok(!rulesOf(lint(text)).includes('frontmatter'));
});

test('frontmatter: regression must be a boolean when present', () => {
  const text = FEATURE.replace(/^regression: .*$/m, 'regression: yes-please');
  assert.ok(rulesOf(lint(text)).includes('frontmatter'));
});
