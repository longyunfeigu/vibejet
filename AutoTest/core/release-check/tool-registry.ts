/**
 * tool-registry.ts — read registered tool names from Release-Check/_shared/tools.md.
 * A tool is registered when a table row's first cell is a backticked name.
 */

const ROW_FIRST_CELL_RE = /^\|\s*`([^`]+)`\s*\|/;

export function loadToolRegistry(markdown: string): Set<string> {
  const names = markdown
    .split(/\r?\n/)
    .map(line => ROW_FIRST_CELL_RE.exec(line.trim()))
    .filter((m): m is RegExpExecArray => m !== null)
    .map(m => m[1].trim());
  return new Set(names);
}
