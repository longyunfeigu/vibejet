#!/usr/bin/env node
/**
 * Shared case index: parse every case CSV and scan .feature tags.
 * Exported buildCaseIndex(root) returns:
 *   { total, automated, cases: [{ caseId, module, title, executionType, notes, automated, csvPath }] }
 * `root` defaults to the AutoTest project root (three levels up from this file's dir).
 */
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const AUTOTEST_ROOT = path.resolve(__dirname, '../../..');

const CASE_ID_TAG_RE = /@([A-Z][A-Z0-9]*-[A-Z0-9]+-\d+)/g;

/** Minimal RFC4180-ish single-line CSV parser (handles quotes + escaped ""). */
export function parseCsvLine(line) {
  const out = [];
  let cur = '';
  let inQ = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (inQ) {
      if (ch === '"' && line[i + 1] === '"') { cur += '"'; i++; }
      else if (ch === '"') { inQ = false; }
      else { cur += ch; }
    } else if (ch === '"') { inQ = true; }
    else if (ch === ',') { out.push(cur); cur = ''; }
    else { cur += ch; }
  }
  out.push(cur);
  return out;
}

/** Split CSV text into records, respecting quoted newlines. */
export function splitRecords(text) {
  const records = [];
  let cur = '';
  let inQ = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (ch === '"') inQ = !inQ;
    if ((ch === '\n' || ch === '\r') && !inQ) {
      if (cur.length) records.push(cur);
      cur = '';
      if (ch === '\r' && text[i + 1] === '\n') i++;
    } else cur += ch;
  }
  if (cur.length) records.push(cur);
  return records;
}

function walk(dir, predicate, acc = []) {
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, ent.name);
    if (ent.isDirectory()) walk(p, predicate, acc);
    else if (predicate(p)) acc.push(p);
  }
  return acc;
}

export function collectAutomatedIds(modulesDir) {
  const ids = new Set();
  if (!fs.existsSync(modulesDir)) return ids;
  // Mirror playwright.config.ts: *.cn.feature and *.pending.feature are never run, so they don't count.
  const featureFiles = walk(
    modulesDir,
    (p) => p.endsWith('.feature') && !p.endsWith('.cn.feature') && !p.endsWith('.pending.feature'),
  );
  for (const f of featureFiles) {
    const txt = fs.readFileSync(f, 'utf8');
    let m;
    while ((m = CASE_ID_TAG_RE.exec(txt)) !== null) ids.add(m[1]);
  }
  return ids;
}

export function buildCaseIndex(root = AUTOTEST_ROOT) {
  const modulesDir = path.join(root, 'modules');
  const automatedIds = collectAutomatedIds(modulesDir);
  const csvFiles = fs.existsSync(modulesDir)
    ? walk(modulesDir, (p) => p.endsWith('manual-test-cases-cn.csv') && !p.includes('/test-data/'))
    : [];
  const cases = [];
  for (const f of csvFiles) {
    const records = splitRecords(fs.readFileSync(f, 'utf8'));
    if (!records.length) continue;
    const header = parseCsvLine(records[0]).map((h) => h.trim());
    // The case file is Chinese (manual-test-cases-cn.csv); English headers are still accepted.
    const col = (...names) => names.map((n) => header.indexOf(n)).find((i) => i !== -1) ?? -1;
    const idIdx = col('用例编号', 'Case ID');
    const titleIdx = col('场景标题', 'Scenario Title');
    const execIdx = col('执行方式', 'Execution Type');
    const notesIdx = col('备注', 'Notes');
    if (idIdx === -1 || titleIdx === -1) {
      console.warn(`[case-index] Skipping ${f}: expected headers (用例编号 / 场景标题) not found`);
      continue;
    }
    const rel = path.relative(modulesDir, f).split(path.sep);
    const module = rel[0];
    for (const rec of records.slice(1)) {
      const cols = parseCsvLine(rec);
      const caseId = (cols[idIdx] || '').trim();
      if (!caseId) continue;
      cases.push({
        caseId,
        module,
        title: (cols[titleIdx] || '').trim(),
        executionType: (cols[execIdx] || '').trim(),
        notes: notesIdx >= 0 ? (cols[notesIdx] || '').trim() : '',
        automated: automatedIds.has(caseId),
        csvPath: f,
      });
    }
  }
  const automated = cases.filter((c) => c.automated).length;
  return { total: cases.length, automated, cases };
}
