/**
 * rules.ts — deterministic quality rules for a Release-Check guide.
 * Each rule is a small function; lintGuide only aggregates.
 */

import { ParsedGuide } from './parse-guide';
import { extractCheckItems } from './priority';
import {
  GUIDE_TYPES, GuideType, REQUIRED_SECTIONS, REQUIRES_ENTRY, RISK_LEVELS, SAFETY_LEVELS,
  SECTION_HEADINGS, SERVICES, SectionId,
} from './schema';

export type RuleId =
  | 'frontmatter' | 'sections' | 'vague-phrase' | 'not-self-contained'
  | 'hardcoded-env' | 'unregistered-tool' | 'cost-estimate'
  | 'supersedes' | 'path' | 'unknown-heading' | 'priority-tag'
  | 'verdict-override' | 'reproduce-old' | 'cost-mismatch' | 'p0-direct';

export interface LintIssue {
  rule: RuleId;
  severity: 'error' | 'warning';
  message: string;
}

export interface LintContext {
  toolRegistry: Set<string>;
  guideExists: (relPath: string) => boolean;
}

type Rule = (guide: ParsedGuide, ctx: LintContext) => LintIssue[];

const error = (rule: RuleId, message: string): LintIssue => ({ rule, severity: 'error', message });
const warning = (rule: RuleId, message: string): LintIssue => ({ rule, severity: 'warning', message });

const VERIFY_SECTIONS: SectionId[] = ['verify', 'expected-after-fix'];

// Sections whose text tells the verifier how to judge; verdict rules apply here only.
const JUDGED_SECTIONS: SectionId[] = ['verify', 'invariants'];

// safety-cn.md: 「不适用」 is decided by the verifier from services and requires; a guide may not declare it.
const NOT_APPLICABLE: RegExp[] = [/不适用/, /\bnot applicable\b/i, /\bN\/A\b/];

// Verification happens on the new version only; a guide may not ask to reproduce the old bug.
const REPRODUCE_OLD: RegExp[] = [
  /(?:在|到|用|切回)旧(?:版本|镜像)(?:上)?(?:复现|验证|跑|执行|对比|重现)/,
  /先复现|复现(?:出|一下)?(?:旧|原来的|这个) ?bug/i,
  /\breproduce\b.{0,40}\b(?:old|previous) (?:version|image|build)\b/i,
  /\b(?:roll ?back|downgrade) to the old (?:version|image)\b/i,
];

// cost_estimate saying no calls while the guide places calls.
const NO_CALL_ESTIMATE = /不打电话|无需打电话|\bno (?:phone )?calls?\b|\b0 calls?\b/i;
const PLACES_CALL: RegExp[] = [
  /打\s*(?:[一二两三四五1-9]\s*)?通(?:测试)?(?:电话|通话)/, /测试电话/, /发起(?:测试|模拟|语音)?通话/,
  /\b(?:place|make|start) (?:a |one |\d+ )?(?:test |simulated )?(?:phone )?calls?\b/i,
];

// A P0 runs on every environment as written (STANDARD.md 1.5). These are the ways it cannot.
const P0_NOT_DIRECT: { re: RegExp; why: string }[] = [
  { re: /(?:暂停|停掉|停止|关停|重启|下线)[^\n。；，]{0,15}(?:服务|pod|deployment|deploy|进程|容器)|缩容|扩缩容/i, why: '要停服务、重启或扩缩容' },
  { re: /\b(?:stop|pause|restart|kill|scale(?: down| to 0)?)\b[^.\n]{0,25}\b(?:service|pod|deployment|process|container)s?\b/i, why: '要停服务、重启或扩缩容' },
  { re: /(?:观察|持续|等待?|跑满|监控)[^\n。；]{0,6}\d+(?:\.\d+)?\s*个?小时/, why: '要长时间观察' },
  { re: /\b(?:observe|watch|monitor|wait|run)\b[^.\n]{0,20}\b\d+(?:\.\d+)? ?(?:hours?|h)\b/i, why: '要长时间观察' },
  { re: /(?:业务|真实|线上|生产)流量|\b(?:business|production|real|live|customer) traffic\b/i, why: '依赖业务流量' },
  { re: /(?:其他|别的|另一个?)(?:企业|租户|组织)|\b(?:another|other) (?:organi[sz]ation|tenant|org)s?\b/i, why: '要动其他企业（需要另一个企业时写明用第二个 QA 企业 AI Builder Sandbox 4）' },
];

// The second QA organization stands in for "another organization" (safety.md); naming it makes the item direct.
const SECOND_QA_ORG = /AI Builder Sandbox 4/i;

const VAGUE_PHRASES: RegExp[] = [
  /功能正常/, /符合预期/, /显示正确/, /正常显示/, /无报错/,
  /works as expected/i, /works correctly/i, /displays correctly/i, /\bno errors?\b/i,
];

const NOT_SELF_CONTAINED: RegExp[] = [
  /问一下/, /找[^「」『』"“”]{1,6}确认一?下/, /群消息/, /群里/, /同上次/, /口头/,
  /\bask \w+ (for|about)\b/i, /\bsee (the )?chat\b/i,
];

const HARDCODED_ENV: RegExp[] = [
  /\b(?:\d{1,3}\.){3}\d{1,3}\b/,
  // Any host under the product domains, with or without a scheme, wherever it ends.
  /(?:^|[^a-z0-9.-])(?:[a-z0-9-]+\.)+(?:wiz\.ai|talkbots\.cn)(?![a-z0-9.-])/i,
  /password\s*[:=]/i,
  /密码\s*[:：=]/,
];

const asStringList = (value: unknown): string[] | null => {
  if (!Array.isArray(value)) return null;
  return value.every(v => typeof v === 'string') ? value as string[] : null;
};

const headingOf = (id: SectionId) => SECTION_HEADINGS[id].join(' / ');

const isBlank = (content: string) => content.replace(/<!--[\s\S]*?-->/g, '').trim() === '';

function checkEnum(fm: Record<string, unknown>, field: string, allowed: readonly string[]): LintIssue[] {
  const value = fm[field];
  if (typeof value === 'string' && allowed.includes(value)) return [];
  return [error('frontmatter', `字段 ${field} 必须是 ${allowed.join(' / ')} 之一，当前为 ${JSON.stringify(value)}`)];
}

function checkServices(value: unknown): LintIssue[] {
  const list = asStringList(value);
  if (!list || list.length === 0) {
    return [error('frontmatter', '字段 services 必须是非空列表')];
  }
  const unknown = list.filter(s => !(SERVICES as readonly string[]).includes(s));
  return unknown.length === 0 ? [] : [error('frontmatter', `services 里有未知服务：${unknown.join(', ')}；按服务键填写，如 voiceAgent.backend`)];
}

function checkRequires(value: unknown): LintIssue[] {
  if (value === undefined) return [];
  const list = asStringList(value);
  if (!list) {
    return [error('frontmatter', '字段 requires 必须是列表，如 [gray:gpt-live, model:gpt-realtime]')];
  }
  const bad = list.filter(r => !REQUIRES_ENTRY.test(r));
  return bad.length === 0 ? [] : [error('frontmatter', `requires 里有无法识别的项：${bad.join(', ')}；写成 gray:<灰度键>、model:<模型名>、service:<工作负载> 或 outbound（STANDARD.md 1.15）`)];
}

const frontmatterRule: Rule = ({ frontmatter: fm }) => {
  const missingText = ['source_branch', 'author']
    .filter(f => typeof fm[f] !== 'string' || (fm[f] as string).trim() === '')
    .map(f => error('frontmatter', `缺少字段 ${f}`));
  // regression 可省略，省略即 false
  const regression = fm.regression === undefined || typeof fm.regression === 'boolean'
    ? [] : [error('frontmatter', '字段 regression 必须是 true 或 false（可省略，默认 false）')];
  const tools = asStringList(fm.tools)
    ? [] : [error('frontmatter', '字段 tools 必须是工具名列表（见 _shared/tools.md）')];
  const requires = checkRequires(fm.requires);
  return [
    ...checkEnum(fm, 'type', GUIDE_TYPES),
    ...missingText,
    ...checkServices(fm.services),
    ...checkEnum(fm, 'safety', SAFETY_LEVELS),
    ...checkEnum(fm, 'risk', RISK_LEVELS),
    ...regression,
    ...tools,
    ...requires,
  ];
};

const sectionsRule: Rule = ({ frontmatter, sections }) => {
  const type = frontmatter.type as GuideType;
  const required = REQUIRED_SECTIONS[type];
  if (!required) return [];
  return required
    .filter(id => isBlank(sections.get(id) ?? ''))
    .map(id => error('sections', `缺少章节或章节为空：## ${headingOf(id)}`));
};

const vaguePhraseRule: Rule = ({ sections }) =>
  VERIFY_SECTIONS.flatMap(id => {
    const content = sections.get(id) ?? '';
    return VAGUE_PHRASES
      .filter(re => re.test(content))
      .map(re => error('vague-phrase', `「${headingOf(id)}」里有空话 ${re.source}：写出具体能看到的信号（字段值、状态码、日志关键字、页面文案）`));
  });

// These two scan the whole body so text in unknown sections or before the first heading is not exempt.
const notSelfContainedRule: Rule = ({ body }) =>
  NOT_SELF_CONTAINED
    .filter(re => re.test(body))
    .map(re => error('not-self-contained', `依赖指导以外的信息（${re.source}）：把需要的内容直接写进来`));

const hardcodedEnvRule: Rule = ({ body }) =>
  HARDCODED_ENV
    .filter(re => re.test(body))
    .map(re => error('hardcoded-env', `写死了地址或密码（${re.source}）：用例里不写地址、账号、口令和密钥`));

const unknownHeadingRule: Rule = ({ unknownHeadings }) =>
  unknownHeadings.map(h => warning('unknown-heading', `无法识别的章节标题「${h}」：标题须与模板完全一致，否则其内容不计入对应章节`));

const unregisteredToolRule: Rule = ({ frontmatter }, ctx) =>
  (asStringList(frontmatter.tools) ?? [])
    .filter(t => !ctx.toolRegistry.has(t))
    .map(t => error('unregistered-tool', `工具 ${t} 未在 _shared/tools.md 登记`));

const costEstimateRule: Rule = ({ frontmatter }) =>
  frontmatter.safety === 'costly' && !frontmatter.cost_estimate
    ? [error('cost-estimate', 'safety 为 costly 时必须填写 cost_estimate（预计电话/LLM 调用次数）')]
    : [];

const supersedesRule: Rule = ({ frontmatter }, ctx) => {
  const target = frontmatter.supersedes;
  if (target === undefined) return [];
  if (typeof target !== 'string' || !ctx.guideExists(target)) {
    return [error('supersedes', `supersedes 指向的指导不存在：${JSON.stringify(target)}（路径相对 Release-Check/）`)];
  }
  return [];
};

const priorityTagRule: Rule = ({ sections }) => {
  const items = extractCheckItems(sections.get('verify') ?? '');
  if (items.length === 0) {
    return [error('priority-tag', `「${headingOf('verify')}」里的检查项必须写成编号或无序列表，每条开头标 [P0] / [P1] / [P2]`)];
  }
  const untagged = items
    .filter(item => item.priority === null)
    .map(item => error('priority-tag', `「${headingOf('verify')}」第 ${item.index} 条没有标级别或级别不合法：开头写 [P0] / [P1] / [P2]`));
  const noSmoke = untagged.length === 0 && !items.some(item => item.priority === 'P0')
    ? [warning('priority-tag', '没有 [P0] 检查项：没有写基本功能有没有实现的检查，确认是有意的')]
    : [];
  return [...untagged, ...noSmoke];
};

const p0DirectRule: Rule = ({ sections }) =>
  extractCheckItems(sections.get('verify') ?? '')
    .filter(item => item.priority === 'P0')
    .flatMap(item => {
      const hit = P0_NOT_DIRECT
        .filter(({ why }) => !(why.startsWith('要动其他企业') && SECOND_QA_ORG.test(item.text)))
        .find(({ re }) => re.test(item.text));
      return hit ? [error('p0-direct', `「${headingOf('verify')}」第 ${item.index} 条 [P0] ${hit.why}，不能拿来直接跑：降成 [P1]，或改为研发在 MR 里附自测证据（STANDARD.md 1.5）`)] : [];
    });

const judgedText = (sections: ParsedGuide['sections']) =>
  JUDGED_SECTIONS.map(id => ({ id, content: sections.get(id) ?? '' }));

const verdictOverrideRule: Rule = ({ sections }) =>
  judgedText(sections).flatMap(({ id, content }) =>
    NOT_APPLICABLE
      .filter(re => re.test(content))
      .map(re => error('verdict-override', `「${headingOf(id)}」里写了「不适用」（${re.source}）：「不适用」由验证方按 services 和 requires 对照环境判；环境可能没有的依赖写进文件头 requires，能在 Autotest 里造出的前提写清怎么造（STANDARD.md 1.15）`)));

const reproduceOldRule: Rule = ({ sections }) =>
  judgedText(sections).flatMap(({ id, content }) =>
    REPRODUCE_OLD
      .filter(re => re.test(content))
      .map(re => warning('reproduce-old', `「${headingOf(id)}」要求复现旧版本的问题（${re.source}）：验证只在新版本上做，不复现历史 bug；改成在新版本上能正向观察的信号`)));

const costMismatchRule: Rule = ({ frontmatter, body }) => {
  const estimate = frontmatter.cost_estimate;
  if (typeof estimate !== 'string' || !NO_CALL_ESTIMATE.test(estimate)) return [];
  const usesCallTool = (asStringList(frontmatter.tools) ?? []).includes('ai-simulation-call');
  const hit = PLACES_CALL.find(re => re.test(body));
  if (!usesCallTool && !hit) return [];
  const why = usesCallTool ? 'tools 里有 ai-simulation-call' : `正文要求打电话（${hit!.source}）`;
  return [warning('cost-mismatch', `cost_estimate 写了不打电话，但${why}：按整份跑一遍实际要打的电话数填写`)];
};

const RULES: Rule[] = [
  frontmatterRule, sectionsRule, vaguePhraseRule, notSelfContainedRule,
  hardcodedEnvRule, unregisteredToolRule, costEstimateRule, supersedesRule,
  unknownHeadingRule, priorityTagRule, verdictOverrideRule, reproduceOldRule,
  costMismatchRule, p0DirectRule,
];

export function lintGuide(guide: ParsedGuide, ctx: LintContext): LintIssue[] {
  return RULES.flatMap(rule => rule(guide, ctx));
}
