#!/usr/bin/env node
/**
 * Backfill the Execution Type column in every case CSV (en + cn) and emit a
 * baseline classification report. Already-automated cases -> "Automated".
 * Un-automated cases -> classify(title): A->Automated-candidate(="Automated"),
 * P/B/C as Manual-*. (A-class un-automated cases are future work; they get
 * "Automated" only once a .feature exists, so for NOW they are also Manual-pending?
 *  NO — per design, A un-automated keeps execType from classify which is "Automated".
 *  That is intentional: the column records the TARGET execution mode; coverage % is
 *  computed separately by automation-coverage.mjs from .feature presence.)
 * Idempotent. Usage: node core/runner/classify-cases.mjs [--write]
 */
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';
import { buildCaseIndex, AUTOTEST_ROOT, parseCsvLine, splitRecords } from './lib/case-index.mjs';
import { classify, EXEC_TYPE, EXEC_TYPE_CN } from './lib/classify-rules.mjs';

/**
 * Replace ONLY the value at field index `fieldIdx` in a raw CSV record string,
 * preserving all other characters (quoting, spacing) exactly as they appear.
 * The new value is unquoted simple ASCII, so no quoting is needed.
 * Returns the patched record string.
 */
export function replaceFieldInRecord(rec, fieldIdx, newValue) {
  // Walk the raw string to find the byte-range of the target field.
  let field = 0;
  let i = 0;
  let fieldStart = 0;
  let fieldEnd = 0;
  while (i <= rec.length) {
    // At start of each field, skip opening quote if present.
    let inQ = false;
    const start = i;
    if (rec[i] === '"') { inQ = true; i++; }
    // Scan to end of field.
    while (i < rec.length) {
      const ch = rec[i];
      if (inQ) {
        if (ch === '"' && rec[i + 1] === '"') { i += 2; continue; }
        if (ch === '"') { inQ = false; i++; continue; }
      } else if (ch === ',') break;
      i++;
    }
    if (field === fieldIdx) {
      fieldStart = start;
      fieldEnd = i;
      break;
    }
    field++;
    if (i < rec.length) i++; // skip the comma
    else break;
  }
  return rec.slice(0, fieldStart) + newValue + rec.slice(fieldEnd);
}

/** Rewrite one CSV file's Execution Type column from a caseId->code map. */
function patchCsv(file, codeById, write) {
  const raw = fs.readFileSync(file, 'utf8');
  // Detect line ending used in this file (preserve it on output).
  const eol = raw.includes('\r\n') ? '\r\n' : '\n';
  const records = splitRecords(raw);
  if (!records.length) return 0;
  const header = parseCsvLine(records[0]).map((h) => h.trim());
  // Support English headers and various Chinese header variants
  const ID_HEADERS = ['Case ID', '用例编号', '用例 ID', '用例ID'];
  const EXEC_HEADERS = ['Execution Type', '执行方式', '执行类型'];
  const idIdx = ID_HEADERS.reduce((found, h) => found >= 0 ? found : header.indexOf(h), -1);
  const execIdx = EXEC_HEADERS.reduce((found, h) => found >= 0 ? found : header.indexOf(h), -1);
  // Detect by FILENAME, not header language — cn files must always get Chinese values.
  const isCn = file.endsWith('manual-test-cases-cn.csv');
  if (idIdx < 0 || execIdx < 0) return 0;
  let changed = 0;
  const out = [records[0]]; // keep header record verbatim
  for (const rec of records.slice(1)) {
    const cols = parseCsvLine(rec);
    const id = (cols[idIdx] || '').trim();
    const code = codeById.has(id) ? codeById.get(id) : undefined;
    const targetExec = code !== undefined ? (isCn ? EXEC_TYPE_CN[code] : EXEC_TYPE[code]) : undefined;
    if (id && targetExec !== undefined && cols[execIdx] !== targetExec) {
      // Patch only the Execution Type field in-place; preserve all other quoting exactly.
      out.push(replaceFieldInRecord(rec, execIdx, targetExec));
      changed++;
    } else {
      out.push(rec); // unchanged — preserve original quoting exactly
    }
  }
  if (write && changed) fs.writeFileSync(file, out.join(eol));
  return changed;
}

function main() {
  const WRITE = process.argv.includes('--write');

  const idx = buildCaseIndex();
  const codeById = new Map(); // caseId -> class code ('AUTO'|'PROD'|'FAULT')
  const tally = { AUTO: 0, PROD: 0, FAULT: 0, Automated: 0 };
  const reportRows = [];
  for (const c of idx.cases) {
    let code;
    let execType;
    if (c.automated) { code = 'AUTO'; execType = EXEC_TYPE.AUTO; tally.Automated++; }
    else { const r = classify(c.title, c.notes); code = r.code; execType = r.execType; tally[r.code]++; }
    codeById.set(c.caseId, code);
    if (!c.automated) reportRows.push({ ...c, code, execType });
  }

  let totalChanged = 0;
  const files = [...new Set(idx.cases.map((c) => c.csvPath))];
  for (const file of files) totalChanged += patchCsv(file, codeById, WRITE);

  const lines = ['# Automation Classification Baseline', '', `Generated from ${idx.total} cases; ${idx.automated} automated.`, '',
    `- Automated (with .feature): ${tally.Automated}`, `- AUTO (target, no .feature yet): ${tally.AUTO}`,
    `- PROD (prod-unsafe, manual): ${tally.PROD}`, `- FAULT (fault-injection, manual): ${tally.FAULT}`,
    '', '## Un-automated cases', '',
    '| Case ID | Module | Class | Execution Type | Title |', '|---|---|---|---|---|'];
  for (const r of reportRows.sort((a, b) => a.module.localeCompare(b.module) || a.caseId.localeCompare(b.caseId))) {
    lines.push(`| ${r.caseId} | ${r.module} | ${r.code} | ${r.execType} | ${r.title.replace(/\|/g, '\\|')} |`);
  }
  const reportPath = path.join(AUTOTEST_ROOT, 'report/automation-classification.md');
  if (WRITE) { fs.mkdirSync(path.dirname(reportPath), { recursive: true }); fs.writeFileSync(reportPath, lines.join('\n')); }

  console.log(`classify-cases: ${WRITE ? 'WROTE' : 'DRY-RUN'} — AUTO=${tally.AUTO} PROD=${tally.PROD} FAULT=${tally.FAULT} Automated=${tally.Automated}; CSV cells changed=${totalChanged}`);
  console.log(WRITE ? `Report: ${reportPath}` : 'Re-run with --write to apply.');
}

if (process.argv[1] === fileURLToPath(import.meta.url)) main();
