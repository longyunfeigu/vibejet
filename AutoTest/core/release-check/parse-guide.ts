/**
 * parse-guide.ts — split a Release-Check guide into YAML frontmatter and
 * level-2 sections keyed by canonical section id.
 */

import { parse as parseYaml } from 'yaml';
import { SECTION_HEADINGS, SectionId } from './schema';

export interface ParsedGuide {
  frontmatter: Record<string, unknown>;
  // Everything after the frontmatter, including text outside recognized sections.
  body: string;
  sections: Map<SectionId, string>;
  unknownHeadings: string[];
}

export class GuideParseError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'GuideParseError';
  }
}

const FRONTMATTER_RE = /^---\n([\s\S]*?)\n---(?:\n|$)/;

const HEADING_LOOKUP: Map<string, SectionId> = new Map(
  (Object.entries(SECTION_HEADINGS) as [SectionId, string[]][])
    .flatMap(([id, labels]) => labels.map(label => [label.toLowerCase(), id] as [string, SectionId])),
);

function normalize(text: string): string {
  return text.replace(/^﻿/, '').replace(/\r\n/g, '\n');
}

function parseFrontmatter(raw: string): Record<string, unknown> {
  let data: unknown;
  try {
    data = parseYaml(raw);
  } catch (e) {
    throw new GuideParseError(`文件头 YAML 解析失败（yaml error）: ${(e as Error).message}`);
  }
  if (data === null || typeof data !== 'object' || Array.isArray(data)) {
    throw new GuideParseError('文件头 YAML 必须是键值对');
  }
  return data as Record<string, unknown>;
}

function splitSections(body: string): Pick<ParsedGuide, 'sections' | 'unknownHeadings'> {
  const sections = new Map<SectionId, string>();
  const unknownHeadings: string[] = [];
  const chunks = body.split(/^## /m).slice(1);
  for (const chunk of chunks) {
    const newline = chunk.indexOf('\n');
    const heading = (newline === -1 ? chunk : chunk.slice(0, newline)).trim();
    const content = newline === -1 ? '' : chunk.slice(newline + 1).trim();
    const id = HEADING_LOOKUP.get(heading.toLowerCase());
    if (id) {
      sections.set(id, content);
    } else {
      unknownHeadings.push(heading);
    }
  }
  return { sections, unknownHeadings };
}

export function parseGuide(text: string): ParsedGuide {
  const normalized = normalize(text);
  const match = FRONTMATTER_RE.exec(normalized);
  if (!match) {
    throw new GuideParseError('缺少文件头：文件必须以 --- 开头的 YAML 块开始');
  }
  const frontmatter = parseFrontmatter(match[1]);
  const body = normalized.slice(match[0].length);
  return { frontmatter, body, ...splitSections(body) };
}
