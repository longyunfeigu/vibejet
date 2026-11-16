#!/usr/bin/env node
/**
 * Classify a test case into one of four execution types:
 *   BACKEND = Backend-Unit (only observable inside the backend; proven by a backend
 *             unit / integration test — never rewritten, never a browser scenario)
 *   AUTO    = Automated target (everything not BACKEND, PROD or FAULT)
 *   PROD    = Manual-Prod-Unsafe (writes to shared cross-env template registry)
 *   FAULT   = Manual-Fault-Injection (forces failures, kills pods, tampers infra)
 *
 * Precedence: BACKEND (column / notes pin) > FAULT pin > PROD pin > PROD (title) > FAULT (notes) > AUTO.
 *
 * Voice, log-grep, DB-inspect, cross-service cases are all AUTO targets —
 * they get redesigned to assert observable UI/API/transcript outcomes.
 */

export const RULES = {
  // Production-unsafe: writes to the shared cross-env TEMPLATE registry / marketplace.
  // Scoped to template context so generic KB "upload files" / incidental "re-publish"
  // wording in unrelated titles is NOT flagged (those are safe, test-env-local).
  P: /\b(?:upload|publish|re-?publish)\b.*\btemplate\b|\btemplate\b.*\b(?:upload|publish|re-?publish)\b|reverse-sync|as a template|as template|cross-region import|taxonomy.*(?:delete|hard-delete)|hard-delete.*tax/i,
};

// Fault-injection: detected in Notes (not title) to avoid false positives on
// scenario titles that merely describe fallback/resilience behaviour.
const FAULT_NOTES = /fault inject|inject(?:s|ed|ing)?\s+(?:a |an )?(?:error|failure|fault)|force[sd]?\s+.{0,25}(?:fail|error|crash|outage)|simulate[sd]?\s+.{0,25}(?:fail|outage|error|crash)|controlled network outage|network outage|patch\s+.{0,30}to raise|stub\s+.{0,30}(?:500|error|fail)|\bGRANT\b|revoke[sd]?\s+.{0,20}(?:permission|grant)|raise\s+\w*Error|kill\s+.{0,15}(?:pod|process|worker)|\btamper/i;

export const EXEC_TYPE = {
  BACKEND: 'Backend-Unit',
  AUTO: 'Automated',
  PROD: 'Manual-Prod-Unsafe',
  FAULT: 'Manual-Fault-Injection',
};

export const EXEC_TYPE_CN = {
  BACKEND: '后端单测',
  AUTO: '自动化测试',
  PROD: '手工测试-产线高危',
  FAULT: '手工测试-故障注入',
};

// Explicit manual pins — an auditor writes one of these markers into a case's
// Notes column to force its classification regardless of title/notes wording.
// Highest precedence. Used for audit-flagged dangerous cases the title/notes
// regexes do not catch (e.g. tenant-wide /admin config resets, shared-registry
// writes). See report/automation-classification.md and the 2026-06-13 safety audit.
const PIN_PROD = /Manual-Prod-Unsafe/i;
const PIN_FAULT = /Manual-Fault-Injection/i;
// Backend-Unit preservation: the column already says so, or Notes carry the
// `Backend-Unit` marker or the canonical "由后端单测覆盖：<测试文件>" pointer. The colon
// is required on purpose — automated rows say "另由后端单测覆盖" / "由后端单测覆盖（页面看不到）；
// E2E 在接口层自动化" (backend tests cover it *in addition*), and must stay AUTO.
const BACKEND_EXEC = new Set([EXEC_TYPE.BACKEND, EXEC_TYPE_CN.BACKEND]);
const PIN_BACKEND = /Backend-Unit|由后端单测覆盖[：:]/i;

/**
 * Classify a case by its scenario title, optional notes and optional current
 * Execution Type column value.
 * Returns { code: 'BACKEND'|'AUTO'|'PROD'|'FAULT', execType: string }.
 */
export function classify(title, notes = '', executionType = '') {
  const t = String(title || '');
  const n = String(notes || '');
  // Backend-Unit rows are preserved before any other rule can rewrite them.
  if (BACKEND_EXEC.has(String(executionType || '').trim()) || PIN_BACKEND.test(n)) {
    return { code: 'BACKEND', execType: EXEC_TYPE.BACKEND };
  }
  // Explicit Notes pins win over everything else.
  if (PIN_FAULT.test(n)) return { code: 'FAULT', execType: EXEC_TYPE.FAULT };
  if (PIN_PROD.test(n)) return { code: 'PROD', execType: EXEC_TYPE.PROD };
  if (RULES.P.test(t)) return { code: 'PROD', execType: EXEC_TYPE.PROD };
  if (FAULT_NOTES.test(n)) return { code: 'FAULT', execType: EXEC_TYPE.FAULT };
  return { code: 'AUTO', execType: EXEC_TYPE.AUTO };
}
