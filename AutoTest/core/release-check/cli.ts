/**
 * cli.ts — lint Release-Check guides.
 *
 *   npx tsx core/release-check/cli.ts            scan every release folder
 *   npx tsx core/release-check/cli.ts <file...>  check the given files only
 *
 * Exit 1 when any error (including parse failures); warnings alone exit 0.
 */

import * as fs from 'fs';
import * as path from 'path';
import { parseGuide, GuideParseError } from './parse-guide';
import { lintGuide, LintContext, LintIssue } from './rules';
import { checkGuidePath } from './guide-name';
import { loadToolRegistry } from './tool-registry';

const ROOT = path.resolve(__dirname, '../../Release-Check');
const TOOLS_FILE = path.join(ROOT, '_shared', 'tools.md');
const GUIDE_DIRS = ['feature', 'bugfix'];

function listGuideFiles(): string[] {
  if (!fs.existsSync(ROOT)) return [];
  return fs.readdirSync(ROOT, { withFileTypes: true })
    .filter(e => e.isDirectory() && !e.name.startsWith('_'))
    .flatMap(release => GUIDE_DIRS.map(dir => path.join(ROOT, release.name, dir)))
    .filter(dir => fs.existsSync(dir))
    .flatMap(dir => fs.readdirSync(dir).filter(f => f.endsWith('.md')).map(f => path.join(dir, f)));
}

function buildContext(): LintContext {
  const registry = fs.existsSync(TOOLS_FILE) ? loadToolRegistry(fs.readFileSync(TOOLS_FILE, 'utf-8')) : new Set<string>();
  return {
    toolRegistry: registry,
    guideExists: rel => fs.existsSync(path.join(ROOT, rel)),
  };
}

function lintFile(file: string, ctx: LintContext): LintIssue[] {
  const relPath = path.relative(ROOT, file).split(path.sep).join('/');
  try {
    const guide = parseGuide(fs.readFileSync(file, 'utf-8'));
    return [...checkGuidePath(relPath, guide), ...lintGuide(guide, ctx)];
  } catch (e) {
    const message = e instanceof GuideParseError ? e.message : `读取失败：${(e as Error).message}`;
    return [{ rule: 'frontmatter', severity: 'error', message }];
  }
}

function main(args: string[]): number {
  const files = args.length > 0 ? args.map(a => path.resolve(a)) : listGuideFiles();
  const ctx = buildContext();
  let errorCount = 0;
  let warningCount = 0;
  for (const file of files) {
    const issues = lintFile(file, ctx);
    errorCount += issues.filter(i => i.severity === 'error').length;
    warningCount += issues.filter(i => i.severity === 'warning').length;
    const hasError = issues.some(i => i.severity === 'error');
    const label = hasError ? 'FAIL' : issues.length > 0 ? 'WARN' : 'OK  ';
    console.log(`${label} ${path.relative(process.cwd(), file)}`);
    issues.forEach(i => console.log(`  [${i.severity}] ${i.rule}: ${i.message}`));
  }
  console.log(`\n${files.length} 份指导，${errorCount} 个错误，${warningCount} 个警告`);
  return errorCount > 0 ? 1 : 0;
}

process.exit(main(process.argv.slice(2)));
