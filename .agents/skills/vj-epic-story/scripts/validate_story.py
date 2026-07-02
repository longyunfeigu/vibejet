#!/usr/bin/env python3
# input: docs/tasks/epics/ 下的 epic markdown（平铺单文件 / epic 目录含 stories/*.md）路径参数
# output: Story 结构机检报告（stdout）+ exit code（0=全过，1=有 ERROR）
# pos: vj-epic-story skill 校验脚本 - AC 上限/验证三要素/Assumptions/Feature Bundling/前向依赖机检；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Validate epic/story markdown against vj-epic-story hard rules.

机检规则（对应 vj-epic-story SKILL.md）：
  R1  行为 AC 总数 ≤7（Happy/Edge/Error/Integration 合计）；FE AC >4 报 WARNING
  R2  每条 AC 必须带 `验证: <kind> <target> → <assert>` 三要素，kind ∈ pytest|API|DB|Browser
  R3  每个 Story 必须有 #### Assumptions；条目为 "无" 或
      "[FEASIBILITY|DEPENDENCY|DATA|SCOPE] 描述 — Confidence: H/M/L — 失效影响: ..."
  R4  Story 标题禁止 Feature Bundling（和/&/+/,/、/，连接两个能力）；
      单一原子能力的例外在标题行尾加 <!-- bundling-ok --> 豁免
  R5  依赖无前向：Story X.N 只能依赖 X.M (M<N) 或更小序号 Epic 的 Story

Usage:
    python3 validate_story.py <epic.md | epic-dir | story.md> [more paths...]

Exit codes:
    0 — 无 ERROR（WARNING 不阻塞）
    1 — 存在 ERROR，禁止写盘/交付
    2 — 用法或文件读取错误
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

STORY_HEAD = re.compile(r"^###\s+Story\s+(\d+)\.(\d+)\s*[:：]\s*(.+?)\s*$")
VERIFY_RE = re.compile(
    r"`验证:\s*(pytest|API|DB|Browser)\s+(.+?)(?:→|->)\s*(.+?)`"
)
AC_LINE = re.compile(r"^\s*-\s*\[[ xX]\]\s*(.+)$")
ASSUMPTION_RE = re.compile(
    r"^\s*-\s*\[(FEASIBILITY|DEPENDENCY|DATA|SCOPE)\]\s*.+?—\s*Confidence:\s*[HML]\s*—\s*失效影响\s*[:：]\s*\S+"
)
DEP_LINE = re.compile(r"^\*\*依赖\*\*\s*[:：]\s*(.+?)\s*$")
DEP_STORY = re.compile(r"Story\s+(\d+)\.(\d+)")
BUNDLING = re.compile(r"(\s和\s|和|&|\+|,|，|、)")
BUNDLING_OK = "<!-- bundling-ok -->"

BEHAVIOR_SECTIONS = ("Happy Path", "Edge Cases", "Error Paths", "Integration")


@dataclass
class Finding:
    level: str  # ERROR | WARNING
    story: str
    rule: str
    message: str


@dataclass
class StoryBlock:
    epic_no: int
    story_no: int
    title: str
    title_line: str
    lines: list[str] = field(default_factory=list)

    @property
    def sid(self) -> str:
        return f"Story {self.epic_no}.{self.story_no}"


def collect_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        path = Path(p)
        if not path.exists():
            print(f"✗ 路径不存在: {p}", file=sys.stderr)
            sys.exit(2)
        if path.is_dir():
            epic_md = path / "epic.md"
            if epic_md.exists():
                files.append(epic_md)
            files.extend(sorted((path / "stories").glob("*.md")) if (path / "stories").is_dir() else [])
            if not epic_md.exists() and not (path / "stories").is_dir():
                files.extend(sorted(path.glob("*.md")))
        else:
            files.append(path)
    return files


def split_stories(text: str) -> list[StoryBlock]:
    blocks: list[StoryBlock] = []
    current: StoryBlock | None = None
    for line in text.splitlines():
        m = STORY_HEAD.match(line)
        if m:
            current = StoryBlock(int(m.group(1)), int(m.group(2)), m.group(3), line)
            blocks.append(current)
        elif current is not None:
            current.lines.append(line)
    return blocks


def section_of(lines: list[str]) -> list[tuple[str, str]]:
    """Return (section, line) pairs; section tracks the nearest **Header** / #### header."""
    out: list[tuple[str, str]] = []
    section = ""
    for line in lines:
        h4 = re.match(r"^####\s+(.+?)\s*$", line)
        bold = re.match(r"^\*\*(.+?)\*\*（?", line)
        if h4:
            section = h4.group(1)
        elif bold and bold.group(1) in BEHAVIOR_SECTIONS:
            section = bold.group(1)
        out.append((section, line))
    return out


def check_story(block: StoryBlock) -> list[Finding]:
    findings: list[Finding] = []
    sid = block.sid

    # R4 Feature Bundling（标题）
    if BUNDLING_OK not in block.title_line and BUNDLING.search(block.title):
        findings.append(Finding(
            "ERROR", sid, "R4",
            f"标题疑似 Feature Bundling：「{block.title}」。拆成独立 Story；"
            f"若确为单一原子能力，在标题行尾加 {BUNDLING_OK} 豁免",
        ))

    behavior_ac: list[str] = []
    fe_ac: list[str] = []
    assumptions_lines: list[str] = []
    has_assumptions_section = False
    dep_raw: str | None = None

    for section, line in section_of(block.lines):
        if section == "Assumptions":
            has_assumptions_section = True
            if re.match(r"^\s*-\s*\S", line):
                assumptions_lines.append(line)
        dep_m = DEP_LINE.match(line.strip())
        if dep_m:
            dep_raw = dep_m.group(1)
        ac_m = AC_LINE.match(line)
        if not ac_m:
            continue
        if section in BEHAVIOR_SECTIONS or section == "验收标准":
            behavior_ac.append(line)
        elif section.startswith("前端验收标准"):
            fe_ac.append(line)

    # R1 AC 上限
    if len(behavior_ac) > 7:
        findings.append(Finding(
            "ERROR", sid, "R1",
            f"行为 AC 总数 {len(behavior_ac)} > 7：按覆盖空间拆分触发器拆 Story，不要删类别压缩",
        ))
    if len(fe_ac) > 4:
        findings.append(Finding(
            "WARNING", sid, "R1",
            f"前端 AC {len(fe_ac)} 条超过建议上限 4；若承载新增业务行为应回流行为 AC 或拆 Story",
        ))
    if not behavior_ac:
        findings.append(Finding("ERROR", sid, "R1", "未找到任何行为 AC（至少需要 1 条 Happy Path）"))

    # R2 验证三要素
    for line in behavior_ac + fe_ac:
        m = VERIFY_RE.search(line)
        if not m:
            findings.append(Finding(
                "ERROR", sid, "R2",
                f"AC 缺少合法的 `验证: <kind> <target> → <assert>`（kind ∈ pytest|API|DB|Browser）："
                f"{line.strip()[:80]}",
            ))
        elif not m.group(3).strip():
            findings.append(Finding("ERROR", sid, "R2", f"`验证:` 缺少断言部分：{line.strip()[:80]}"))

    # R3 Assumptions
    if not has_assumptions_section:
        findings.append(Finding("ERROR", sid, "R3", "缺少 #### Assumptions section（无假设也必须填「无」）"))
    else:
        for line in assumptions_lines:
            stripped = re.sub(r"^\s*-\s*", "", line).strip()
            if stripped in ("无", "无。"):
                continue
            if not ASSUMPTION_RE.match(line):
                findings.append(Finding(
                    "ERROR", sid, "R3",
                    f"Assumption 不符合三要素「[类别] 描述 — Confidence: H/M/L — 失效影响: ...」："
                    f"{stripped[:80]}",
                ))

    # R5 前向依赖
    if dep_raw is not None and dep_raw not in ("无", "无。"):
        for dm in DEP_STORY.finditer(dep_raw):
            dep_epic, dep_story = int(dm.group(1)), int(dm.group(2))
            if dep_epic > block.epic_no or (
                dep_epic == block.epic_no and dep_story >= block.story_no
            ):
                findings.append(Finding(
                    "ERROR", sid, "R5",
                    f"前向/自身依赖：依赖 Story {dep_epic}.{dep_story}，"
                    f"只允许同 Epic 更小序号或更小序号 Epic 的 Story",
                ))
    return findings


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2

    files = collect_files(argv[1:])
    all_findings: list[tuple[Path, Finding]] = []
    story_count = 0

    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except OSError as e:
            print(f"✗ 读取失败 {f}: {e}", file=sys.stderr)
            return 2
        blocks = split_stories(text)
        story_count += len(blocks)
        for b in blocks:
            for finding in check_story(b):
                all_findings.append((f, finding))

    errors = [x for x in all_findings if x[1].level == "ERROR"]
    warnings = [x for x in all_findings if x[1].level == "WARNING"]

    for f, x in all_findings:
        mark = "✗" if x.level == "ERROR" else "⚠"
        print(f"{mark} [{x.level}][{x.rule}] {f}:{x.story} — {x.message}")

    print(
        f"\n校验完成：{story_count} 个 Story，{len(errors)} ERROR，{len(warnings)} WARNING"
        + ("（存在 ERROR，禁止写盘）" if errors else " ✓")
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
