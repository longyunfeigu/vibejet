/**
 * guide-name.ts — derive and check Release-Check guide file names and paths.
 * Path layout: <YYYY-MM>/<feature|bugfix>/<author>-<slug>.md
 */

import { ParsedGuide } from './parse-guide';
import { LintIssue } from './rules';

const BRANCH_PREFIX_RE = /^(?:feature|feat|fix|bugfix|hotfix|change)[/-]/i;
const DATE_SUFFIX_RE = /[_-]\d{8}(?:-\d+)?$/;
// Team convention `<slug>_<Person>_<date>`: an underscore-joined last word before the date is a person name.
const UNDERSCORE_PERSON_RE = /_[^_-]+$/;
const RELEASE_DIR_RE = /^\d{4}-(?:0[1-9]|1[0-2])$/;
const GUIDE_DIRS = ['feature', 'bugfix'];

const escapeRe = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

// A GitLab username like `yosia.deshilkia` usually appears in branch names as its first part only.
const authorNameForms = (author: string): string[] =>
  [...new Set([author, author.split(/[._]/)[0]])].filter(Boolean);

function stripPerson(slug: string, author: string, hadDate: boolean): string {
  for (const name of authorNameForms(author)) {
    const authorRe = new RegExp(`[_-]${escapeRe(name)}$`, 'i');
    if (authorRe.test(slug)) return slug.replace(authorRe, '');
  }
  return hadDate ? slug.replace(UNDERSCORE_PERSON_RE, '') : slug;
}

export function suggestGuideFileName(sourceBranch: string, author: string): string {
  // Any namespace segment (codex/, docs/, team/feature/...) is not part of the slug.
  const lastSegment = sourceBranch.slice(sourceBranch.lastIndexOf('/') + 1);
  const withoutPrefix = lastSegment.replace(BRANCH_PREFIX_RE, '');
  const hadDate = DATE_SUFFIX_RE.test(withoutPrefix);
  const withoutDate = withoutPrefix.replace(DATE_SUFFIX_RE, '');
  const slug = stripPerson(withoutDate, author, hadDate).replace(/_/g, '-').toLowerCase();
  return `${author}-${slug}.md`;
}

const pathError = (message: string): LintIssue => ({ rule: 'path', severity: 'error', message });

export function checkGuidePath(relPath: string, guide: ParsedGuide): LintIssue[] {
  const parts = relPath.split('/');
  if (parts.length !== 3 || !parts[2].endsWith('.md')) {
    return [pathError(`路径应为 <YYYY-MM>/<feature|bugfix>/<作者>-<短名>.md，当前为 ${relPath}`)];
  }
  const [release, dir, file] = parts;
  const { type, author } = guide.frontmatter;
  return [
    RELEASE_DIR_RE.test(release) ? null : pathError(`月份目录 ${release} 必须是 YYYY-MM`),
    GUIDE_DIRS.includes(dir) ? null : pathError(`二级目录必须是 feature 或 bugfix，当前为 ${dir}`),
    GUIDE_DIRS.includes(dir) && dir !== type ? pathError(`type 为 ${String(type)}，却放在 ${dir}/ 下`) : null,
    typeof author === 'string' && file.startsWith(`${author}-`) ? null : pathError(`文件名必须以作者 ${String(author)}- 开头，当前为 ${file}`),
  ].filter((i): i is LintIssue => i !== null);
}
