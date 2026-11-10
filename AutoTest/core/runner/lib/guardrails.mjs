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
