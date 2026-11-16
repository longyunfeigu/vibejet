/** Detect direct page.request.* usage (data ops must live in core/api). */
export function findApiCallViolations(relPath, content) {
  const out = [];
  const lines = content.split('\n');
  lines.forEach((line, i) => {
    const trimmed = line.trim();
    if (trimmed.startsWith('//') || trimmed.startsWith('*')) return;
    if (line.includes('api-lint-exempt')) return;
    if (/(?<![.\w])page\.request\.(get|post|put|delete|patch|head)\b/.test(line)) {
      out.push(`${relPath}:${i + 1}: page.request.* in step/page — data ops belong in core/api`);
    }
  });
  return out;
}

/** Count controlledWait/workaroundSleep call sites (legacy fixed-delay debt). */
export function countControlledWaits(content) {
  let n = 0;
  for (const line of content.split('\n')) {
    const t = line.trim();
    if (t.startsWith('//') || t.startsWith('*')) continue;
    if (/(?<![.\w])(controlledWait|workaroundSleep)\s*\(/.test(line)) n++;
  }
  return n;
}

/** Canonical Execution Type vocabulary for the Chinese case file (Check G). */
export const EXEC_TYPES_CN = ['自动化测试', '手工测试-产线高危', '手工测试-故障注入', '后端单测'];
export const BACKEND_UNIT_CN = '后端单测';

// Notes of a 后端单测 row must point at the backend test: the phrase itself, or a
// concrete test file name (test_x.py / x_test.py).
const BACKEND_TEST_POINTER = /后端单测|\btest_\w+\.py\b|\b\w+_test\.py\b/;

/** Collect every case-ID tag (e.g. @DIET-PRF-001 -> DIET-PRF-001) in a .feature source. */
export function collectFeatureCaseIds(content) {
  const ids = new Set();
  for (const m of content.matchAll(/@([A-Z]{2,5}-[A-Z0-9]+-\d{3,4})\b/g)) ids.add(m[1]);
  return ids;
}

/**
 * Backend-Unit row rules: a 后端单测 row has no browser scenario (its case ID must not
 * be tagged in any .feature) and its Notes must name the backend test covering it.
 * `row` = { where, caseId, exec, notes }; returns violation strings (empty when fine
 * or when the row is not 后端单测).
 */
export function findBackendUnitViolations(row, featureCaseIds) {
  if (row.exec !== BACKEND_UNIT_CN) return [];
  const out = [];
  if (featureCaseIds.has(row.caseId)) {
    out.push(`${row.where}: ${row.caseId} is 后端单测 but is tagged in a .feature — Backend-Unit rows get no browser scenario`);
  }
  if (!BACKEND_TEST_POINTER.test(row.notes)) {
    out.push(`${row.where}: ${row.caseId} is 后端单测 but Notes do not name the backend test — write "由后端单测覆盖：<测试文件>::<测试名>"`);
  }
  return out;
}
