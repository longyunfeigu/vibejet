/**
 * priority.ts — per-item priority tags in the "How to verify" section.
 *
 * Every top-level list item starts with [P0], [P1] or [P2]:
 *   P0  basic function of the change works / the bug is fixed; a failure fails the guide
 *   P1  main scenarios; a failure fails the guide
 *   P2  minor issue that does not block the main flow; recorded, does not fail the guide
 * Nested items and non-list lines (group headings, tables, prose) are not check items.
 */

import { PRIORITIES, Priority } from './schema';

export interface CheckItem {
  index: number;            // 1-based position among top-level items
  priority: Priority | null; // null when the tag is missing or invalid
  text: string;             // item text with the tag removed
}

const TOP_LEVEL_ITEM_RE = /^(?:\d+[.)]|[-*+])\s+(.*)$/;
const TAG_RE = /^\[(P\d)\]\s*/;

export function extractCheckItems(section: string): CheckItem[] {
  return section
    .split('\n')
    .map(line => TOP_LEVEL_ITEM_RE.exec(line))
    .filter((m): m is RegExpExecArray => m !== null)
    .map((m, i) => {
      const tag = TAG_RE.exec(m[1]);
      const valid = tag !== null && (PRIORITIES as readonly string[]).includes(tag[1]);
      return {
        index: i + 1,
        priority: valid ? tag[1] as Priority : null,
        text: tag ? m[1].slice(tag[0].length) : m[1],
      };
    });
}
