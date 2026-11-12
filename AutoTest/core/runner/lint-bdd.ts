/**
 * lint-bdd.ts — BDD convention checks
 *
 * Check B: Tag compliance (every Scenario in .feature must have at least one required tag)
 * Check C: Step locator prohibition (no direct page.locator / page.getBy etc. in steps)
 * Check D: Test data naming (e2e- strings must be ASCII only)
 * Check E: Stability rules (no raw waitForTimeout, no bare CSS selector in steps)
 * Check F: Case ID tag coverage (every Scenario has exactly one valid case-ID tag, e.g. @AUTH-LGN-001)
 * Check G: CSV structure (every case row has 16 columns; Execution Type is one of
 *          the canonical Chinese values; vibejet keeps one Chinese case file)
 * Check H: API-first — no page.request.* in steps/pages (report-only during the
 *          framework refactor migration; data ops belong in core/api).
 * Check I: controlledWait budget — global controlledWait/workaroundSleep count
 *          may only decrease (ratchet baseline).
 *
 * NOTE: Feature files are English-only. There is no .feature/.cn.feature
 * bilingual-sync check — the runner only executes plain English *.feature files,
 * and keeping a Chinese feature companion in lockstep proved more churn than
 * value. (Case documentation lives in cases/manual-test-cases-cn.csv — see Check G.)
 *
 * Exit 0 only when all checks pass.
 */

import * as fs from 'fs';
import * as path from 'path';
import { findApiCallViolations, countControlledWaits } from './lib/guardrails.mjs';

// ── helpers ───────────────────────────────────────────────────────────────

function readLines(filePath: string): string[] {
  return fs.readFileSync(filePath, 'utf-8').split('\n');
}

const MODULES_DIR = path.resolve(__dirname, '../../modules');

function listModuleDirs(): string[] {
  return fs.readdirSync(MODULES_DIR, { withFileTypes: true })
    .filter(e => e.isDirectory() && e.name !== 'common')
    .map(e => e.name);
}

// Feature directories nest one level down: modules/<module>/<feature>/{features,steps,pages}.
// Looking only at modules/<module>/<name> (as the source did) silently skipped every nested
// feature, so find every directory with the given name under each module instead.
function findModuleSubdirs(name: string): string[] {
  const out: string[] = [];
  function walk(dir: string): void {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      if (!e.isDirectory()) continue;
      const full = path.join(dir, e.name);
      if (e.name === name) out.push(full);
      else walk(full);
    }
  }
  for (const mod of listModuleDirs()) walk(path.join(MODULES_DIR, mod));
  return out;
}

// ── ANSI colours ──────────────────────────────────────────────────────────

const ESC = '';
const R = `${ESC}[0m`;
const green  = (s: string) => `${ESC}[32m${s}${R}`;
const red    = (s: string) => `${ESC}[31m${s}${R}`;
const yellow = (s: string) => `${ESC}[33m${s}${R}`;
const bold   = (s: string) => `${ESC}[1m${s}${R}`;
const dim    = (s: string) => `${ESC}[2m${s}${R}`;

// ── Check B: tag compliance ───────────────────────────────────────────────

interface TagComplianceResult {
  passed: boolean;
  violations: string[];
}

const REQUIRED_TAGS = new Set(['@smoke', '@regression', '@slow', '@negative']);

function checkTagCompliance(): TagComplianceResult {
  const violations: string[] = [];

  for (const featDir of findModuleSubdirs('features')) {

    const enFiles = fs.readdirSync(featDir).filter(f => f.endsWith('.feature') && !f.endsWith('.cn.feature'));
    for (const enFile of enFiles) {
      const enPath = path.join(featDir, enFile);
      const lines = readLines(enPath);

      for (let i = 0; i < lines.length; i++) {
        if (/^\s*Scenario( Outline)?:/.test(lines[i])) {
          // Collect tag lines immediately before this Scenario/Scenario Outline line
          let j = i - 1;
          const tagLines: string[] = [];
          while (j >= 0 && /^\s*@/.test(lines[j])) {
            tagLines.push(lines[j]);
            j--;
          }

          const allTags = tagLines.join(' ');
          const hasRequired = [...REQUIRED_TAGS].some(t => allTags.includes(t));
          if (!hasRequired) {
            const scenarioText = lines[i].trim();
            violations.push(`${enFile} line ${i + 1}: ${scenarioText} — missing required tag (@smoke/@regression/@slow/@negative)`);
          }
        }
      }
    }
  }

  return { passed: violations.length === 0, violations };
}

// ── Check C: step locator prohibition ────────────────────────────────────

interface LocatorResult {
  passed: boolean;
  violations: string[];
}

// Patterns that indicate direct locator usage inside step definitions.
// These match when page/frame is used directly (not via a POM property access).
// Exempt lines that contain the comment `step-lint-exempt`.
//
// Note: patterns use a negative lookbehind to avoid matching POM property access
// like `kb.frame.getBy` or `this.frame.locator` — those go through the POM and are allowed.
// Only bare `page.` and `frame.` (i.e., preceded by whitespace, `(`, `{` or start-of-expr) are flagged.
const FORBIDDEN_PATTERNS = [
  // Direct page usage
  /(?<![.\w])page\.locator\(/,
  /(?<![.\w])page\.getBy/,
  /(?<![.\w])page\.fill\(/,
  /(?<![.\w])page\.click\(/,
  // Bare frame.locator / frame.getBy — standalone local variable `frame`, not a POM property
  /(?<![.\w])frame\.locator\(/,
  /(?<![.\w])frame\.getBy/,
];

function checkStepLocators(): LocatorResult {
  const violations: string[] = [];

  const allStepFiles: string[] = [];
  for (const stepsDir of findModuleSubdirs('steps')) {
    const files = fs.readdirSync(stepsDir).filter(f => f.endsWith('.steps.ts'));
    for (const f of files) {
      allStepFiles.push(path.join(stepsDir, f));
    }
  }
  // Also check the cross-module common steps (findModuleSubdirs skips modules/common).
  const commonStepsPath = path.join(MODULES_DIR, 'common', 'steps', 'common.steps.ts');
  if (fs.existsSync(commonStepsPath)) {
    allStepFiles.push(commonStepsPath);
  }

  for (const filePath of allStepFiles) {
    const lines = readLines(filePath);
    const fileName = path.basename(filePath);

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      // Skip exempt lines
      if (line.includes('step-lint-exempt')) continue;

      // common.steps.ts: allow the cross-context iframe-detection pattern (page.getByRole + frameLocator)
      // but still flag anything that isn't part of that known pattern
      for (const pattern of FORBIDDEN_PATTERNS) {
        if (pattern.test(line)) {
          violations.push(`${fileName}:${i + 1}: direct ${pattern.source.replace(/\\/g, '')} call — move to POM`);
          break; // one violation per line is enough
        }
      }
    }
  }

  return { passed: violations.length === 0, violations };
}

// ── Check D: test data naming ─────────────────────────────────────────────

interface TestDataResult {
  passed: boolean;
  violations: string[];
}

// Match string literals starting with "e2e-" that contain non-ASCII characters
// Non-ASCII: any character outside the printable ASCII range (0x20–0x7E)
const E2E_LITERAL = /"(e2e-[^"]*)"/g;
// eslint-disable-next-line no-control-regex
const NON_ASCII = /[^\x00-\x7F]/;

function checkTestDataNaming(): TestDataResult {
  const violations: string[] = [];

  function scanFile(filePath: string): void {
    const content = fs.readFileSync(filePath, 'utf-8');
    const lines = content.split('\n');
    for (let i = 0; i < lines.length; i++) {
      let match: RegExpExecArray | null;
      E2E_LITERAL.lastIndex = 0;
      while ((match = E2E_LITERAL.exec(lines[i])) !== null) {
        const value = match[1];
        if (NON_ASCII.test(value)) {
          violations.push(`${path.relative(MODULES_DIR, filePath)}:${i + 1}: test data "${match[0]}" contains non-ASCII — use e2e-{ascii-slug} format`);
        }
      }
    }
  }

  function walkDir(dir: string): void {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        walkDir(full);
      } else if (entry.name.endsWith('.ts') || entry.name.endsWith('.feature')) {
        scanFile(full);
      }
    }
  }

  walkDir(MODULES_DIR);

  return { passed: violations.length === 0, violations };
}

// ── Check F: Case ID tag coverage ────────────────────────────────────────────
// Every Scenario / Scenario Outline in an EN .feature file must have exactly one case-ID tag
// of the form @{MODULE}-{FEATURE}-{NNN} (uppercase, digits), e.g. @AUTH-LGN-001.
// No duplicate case-ID tags across all modules.

interface TcTagResult {
  passed: boolean;
  violations: string[];
}

// Format: @{MODULE}-{FEATURE}-{NNN}, MODULE 2-5 uppercase letters, matching the CSV 用例编号
// e.g. @AUTH-LGN-001, @HOME-DSH-002
const TC_TAG_RE = /^@[A-Z]{2,5}-[A-Z0-9]+-\d{3,4}$/;

function checkTcTagCoverage(): TcTagResult {
  const violations: string[] = [];
  const seenTags = new Map<string, string>(); // tag value → first file

  for (const featDir of findModuleSubdirs('features')) {

    const enFiles = fs.readdirSync(featDir)
      .filter(f => f.endsWith('.feature') && !f.endsWith('.cn.feature'));

    for (const enFile of enFiles) {
      const enPath = path.join(featDir, enFile);
      const lines = readLines(enPath);

      for (let i = 0; i < lines.length; i++) {
        if (!/^\s*Scenario( Outline)?:/.test(lines[i])) continue;

        // Collect tag lines immediately before this Scenario/Scenario Outline line
        let j = i - 1;
        const tagLines: string[] = [];
        while (j >= 0 && /^\s*@/.test(lines[j])) {
          tagLines.push(lines[j]);
          j--;
        }
        const allTagsStr = tagLines.join(' ');
        const tcTags = allTagsStr.match(/@[A-Z]{2,5}-[A-Z0-9]+-\d{3,4}\b/g) ?? [];

        if (tcTags.length === 0) {
          violations.push(`${enFile} line ${i + 1}: missing case-ID tag (e.g. @AUTH-LGN-001)`);
          continue;
        }
        if (tcTags.length > 1) {
          violations.push(`${enFile} line ${i + 1}: multiple case-ID tags: ${tcTags.join(', ')}`);
          continue;
        }

        const tc = tcTags[0];
        if (!tc) {
          violations.push(`${enFile} line ${i + 1}: missing case-ID tag (e.g. @AUTH-LGN-001)`);
          continue;
        }
        if (!TC_TAG_RE.test(tc)) {
          violations.push(`${enFile} line ${i + 1}: invalid case-ID tag "${tc}" — expected @MODULE-FEATURE-NNN`);
        }

        const key = tc;
        if (seenTags.has(key)) {
          violations.push(`${enFile} line ${i + 1}: duplicate case-ID tag ${tc} (first seen in ${seenTags.get(key)})`);
        } else {
          seenTags.set(key, enFile);
        }
      }
    }
  }

  return { passed: violations.length === 0, violations };
}

// ── Check E: Stability — no raw waitForTimeout, no bare locator in steps ──

function checkStability(): { passed: boolean; violations: string[] } {
  const violations: string[] = [];
  for (const stepsDir of findModuleSubdirs('steps')) {

    const stepFiles = fs.readdirSync(stepsDir).filter(f => f.endsWith('.steps.ts'));

    for (const file of stepFiles) {
      const filePath = path.join(stepsDir, file);
      const lines = readLines(filePath);
      const rel = path.relative(MODULES_DIR, filePath);

      lines.forEach((line, i) => {
        const lineNum = i + 1;
        const trimmed = line.trim();
        // Skip comments
        if (trimmed.startsWith('//')) return;

        // Rule 1: no waitForTimeout in step files
        if (/page\.waitForTimeout\(/.test(line)) {
          violations.push(`${rel}:${lineNum}: waitForTimeout in step — move to POM or use wait-utils`);
        }

        // Rule 2: no bare CSS class selector in step files (div.xxx, span.xxx)
        if (/(?<![.\w])page\.locator\(\s*['"`][a-z]+(\.[\w-]+)+/.test(line)) {
          violations.push(`${rel}:${lineNum}: CSS class selector in step — move to POM`);
        }
      });
    }
  }

  const rawWaitRoots = [
    MODULES_DIR,
    path.resolve(__dirname, '../helpers'),
  ];

  function scanRawWaits(dir: string): void {
    if (!fs.existsSync(dir)) return;
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        scanRawWaits(fullPath);
        continue;
      }
      if (!entry.name.endsWith('.ts')) continue;
      if (fullPath.endsWith(path.join('core', 'helpers', 'wait-utils.ts'))) continue;

      const lines = readLines(fullPath);
      const rel = path.relative(path.resolve(__dirname, '../..'), fullPath);
      lines.forEach((line, i) => {
        const trimmed = line.trim();
        if (trimmed.startsWith('//') || trimmed.startsWith('*')) return;
        if (/\.waitForTimeout\(/.test(line)) {
          violations.push(`${rel}:${i + 1}: raw waitForTimeout is forbidden — use a business-state wait or controlledWait with a reason`);
        }
      });
    }
  }

  rawWaitRoots.forEach(scanRawWaits);

  return { passed: violations.length === 0, violations };
}

// ── Check G: CSV structure & Execution Type ───────────────────────────────
// Every data row in cases/manual-test-cases-cn.csv must have exactly 16 columns,
// and the 执行方式 column (index 7) must be one of the canonical values. This guards
// against column shifts (串列) and value drift (e.g. 手动测试 / 手工 / 自动化).

const CSV_COLUMN_COUNT = 16;
const EXEC_COL = 7;
// Canonical 3-type vocabulary for the Chinese case file.
const EXEC_CN = new Set(['自动化测试', '手工测试-产线高危', '手工测试-故障注入']);

/** RFC4180 quote-aware CSV parser (handles embedded commas/newlines, "" escapes, BOM). */
function parseCsv(content: string): string[][] {
  if (content.charCodeAt(0) === 0xfeff) content = content.slice(1);
  const rows: string[][] = [];
  let field = '';
  let row: string[] = [];
  let inQuotes = false;
  for (let i = 0; i < content.length; i++) {
    const c = content[i];
    if (inQuotes) {
      if (c === '"') {
        if (content[i + 1] === '"') { field += '"'; i++; } else inQuotes = false;
      } else field += c;
    } else if (c === '"') {
      inQuotes = true;
    } else if (c === ',') {
      row.push(field); field = '';
    } else if (c === '\n') {
      row.push(field); rows.push(row); row = []; field = '';
    } else if (c !== '\r') {
      field += c;
    }
  }
  if (field !== '' || row.length > 0) { row.push(field); rows.push(row); }
  return rows;
}

function findCaseCsvs(): string[] {
  const out: string[] = [];
  function walk(dir: string): void {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      if (e.isDirectory()) {
        if (e.name !== 'test-data') walk(path.join(dir, e.name));
      } else if (e.name === 'manual-test-cases-cn.csv') {
        out.push(path.join(dir, e.name));
      }
    }
  }
  walk(MODULES_DIR);
  return out;
}

function isBlankRow(r: string[]): boolean {
  return r.every(c => c.trim() === '');
}

function checkCsvStructure(): { passed: boolean; violations: string[] } {
  const violations: string[] = [];

  function validateFile(filePath: string, allowed: Set<string>): void {
    const rel = path.relative(MODULES_DIR, filePath);
    const rows = parseCsv(fs.readFileSync(filePath, 'utf-8'));
    rows.slice(1).forEach((r, idx) => {
      const lineNo = idx + 2; // header is row 1
      if (isBlankRow(r)) return;
      const caseId = (r[0] ?? '').trim();
      if (caseId === '' || caseId === 'Case ID' || caseId === '用例编号') return;
      if (r.length !== CSV_COLUMN_COUNT) {
        violations.push(`${rel}:${lineNo}: ${caseId} has ${r.length} columns (expected ${CSV_COLUMN_COUNT}) — likely 串列/column shift`);
      }
      const exec = (r[EXEC_COL] ?? '').trim();
      if (!allowed.has(exec)) {
        violations.push(`${rel}:${lineNo}: ${caseId} Execution Type "${exec}" invalid — must be ${[...allowed].join(' / ')}`);
      }
    });
  }

  // vibejet keeps one case file per feature, in Chinese (the source also kept an en companion).
  for (const cnPath of findCaseCsvs()) validateFile(cnPath, EXEC_CN);

  return { passed: violations.length === 0, violations };
}

// ── Check H: API-first — no page.request.* in steps/pages (report-only) ──────

function checkApiInSteps(): { passed: boolean; violations: string[] } {
  const violations: string[] = [];
  for (const dir of [...findModuleSubdirs('steps'), ...findModuleSubdirs('pages')]) {
    for (const f of fs.readdirSync(dir).filter(n => n.endsWith('.ts'))) {
      const full = path.join(dir, f);
      violations.push(...findApiCallViolations(path.relative(MODULES_DIR, full), fs.readFileSync(full, 'utf-8')));
    }
  }
  return { passed: violations.length === 0, violations };
}

// ── Check I: controlledWait budget — count may only decrease (ratchet) ───────

function checkControlledWaitBudget(): { passed: boolean; violations: string[] } {
  const baselinePath = path.resolve(__dirname, 'controlledwait-baseline.json');
  let total = 0;
  function walk(dir: string): void {
    if (!fs.existsSync(dir)) return;
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, e.name);
      if (e.isDirectory()) { walk(full); continue; }
      if (!e.name.endsWith('.ts')) continue;
      if (full.endsWith(path.join('core', 'helpers', 'wait-utils.ts'))) continue;
      total += countControlledWaits(fs.readFileSync(full, 'utf-8'));
    }
  }
  walk(MODULES_DIR);
  walk(path.resolve(__dirname, '../helpers'));

  if (!fs.existsSync(baselinePath)) {
    fs.writeFileSync(baselinePath, JSON.stringify({ count: total }, null, 2) + '\n');
    return { passed: true, violations: [`baseline created at ${total}`] };
  }
  const baseline = (JSON.parse(fs.readFileSync(baselinePath, 'utf-8')).count as number);
  if (total > baseline) {
    return { passed: false, violations: [`controlledWait count rose ${baseline} -> ${total}; only decreases allowed`] };
  }
  // Ratchet down: if reduced, lower the baseline so it can't creep back up.
  if (total < baseline) fs.writeFileSync(baselinePath, JSON.stringify({ count: total }, null, 2) + '\n');
  return { passed: true, violations: [] };
}

// ── main ──────────────────────────────────────────────────────────────────

function printResult(label: string, result: { passed: boolean; violations: string[] }): void {
  if (result.passed) {
    console.log(green(`[PASS] ${label}`));
  } else {
    console.log(red(`[FAIL] ${label}: ${result.violations.length} violation(s)`));
    for (const v of result.violations) {
      console.log(yellow(`  ${v}`));
    }
  }
}

function main(): void {
  console.log(bold('\n=== BDD Lint ===\n'));

  const tagResult         = checkTagCompliance();
  const locatorResult     = checkStepLocators();
  const testDataResult    = checkTestDataNaming();
  const stabilityResult   = checkStability();
  const tcTagResult       = checkTcTagCoverage();
  const csvStructResult   = checkCsvStructure();
  const apiInStepsResult  = checkApiInSteps();
  const cwBudgetResult    = checkControlledWaitBudget();

  printResult('Tag compliance',   tagResult);
  printResult('Step locator',     locatorResult);
  printResult('Test data naming', testDataResult);
  printResult('Stability rules',  stabilityResult);
  printResult('Case ID tag coverage', tcTagResult);
  printResult('CSV structure',    csvStructResult);
  // Check H is report-only during the refactor migration (data-CRUD vs
  // assertion-reads are disambiguated as each module migrates to core/api).
  printResult('No page.request in steps/pages (report-only until migration done)', apiInStepsResult);
  printResult('controlledWait budget (no increase)', cwBudgetResult);

  const failCount = [tagResult, locatorResult, testDataResult, stabilityResult, tcTagResult, csvStructResult, cwBudgetResult]
    .filter(r => !r.passed).length;

  console.log('');
  if (failCount === 0) {
    console.log(bold(green('=== All checks passed ===')));
  } else {
    console.log(bold(red(`=== ${failCount} check(s) failed ===`)));
  }
  console.log('');

  process.exit(failCount > 0 ? 1 : 0);
}

main();
