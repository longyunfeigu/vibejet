#!/usr/bin/env python3
# input: vj-product-requirements 产出的 PRD markdown（默认 docs/project/requirements.md）路径参数
# output: PRD 结构机检报告（stdout）+ exit code（0=全过，1=有 ERROR）
# pos: vj-product-requirements skill 校验脚本 - Phase 4 机械检查的真相源（rubric 不复述规则清单）；
#      一旦我被更新，务必更新我的开头注释以及所属文件夹的 README.md
"""Validate PRD markdown against vj-product-requirements hard rules.

机检规则（Phase 4 机械检查的唯一真相源；语义检查仍在 quality_rubric.md）：
  P1  头部元数据齐全：工作模式 / 项目阶段 / 范围模式 / 调研模式
  P2  章节完整性：§1/§1.5/§3/§4/§5/§6/§9/§10/§11 必须存在；
      调研模式 light|deep 时 §2/§7 必须存在（下游按节号消费，节号不可漂移）
  P3  EARS 需求块合法：类型 ∈ When|If|While|Where|Ubiquitous|Scenario；
      块内含响应词"应"；块内含 ≥1 来源标注 [用户]/[调研]/[推断]/[未验证假设]
  P4  R 编号在 Epic 内唯一（重复=ERROR；跳号=WARNING）
  P5  占位符扫描：[填写] / <待定> / 句尾"未定" = ERROR；TBD / TODO 可能是正文 = WARNING
  P6  §1.5 mermaid 用户旅程不得保留方括号模板占位节点（如 ["[角色进入入口/页面]"]）
  P7  文中存在 [推断] 时，§8 待验证假设必须存在且含 ≥1 数据行
  P8  §3 角色定义与 §9 非目标各含 ≥1 条目
  P9  启发式（WARNING，不阻塞）：(If) 块含"期间"疑似状态冒充；
      (While) 块不含"期间"疑似写法不符；§4 出现 友好/智能/易用 等无度量模糊词

Usage:
    python3 validate_prd.py <requirements.md> [more files...]

Exit codes:
    0 — 无 ERROR（WARNING 不阻塞）
    1 — 存在 ERROR，不得进入评分，不得放行 vj-architecture
    2 — 用法或文件读取错误
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

REQ_START = re.compile(r"^[*-]\s{1,3}\*\*(R\d+)\s*\(([^)]+)\)\*\*")
EPIC_HEAD = re.compile(r"^###\s+Epic\s+(\d+)")
H2 = re.compile(r"^##\s+(\d+)\.")
H15 = re.compile(r"^###\s+1\.5\.")
META_FIELDS = ("工作模式", "项目阶段", "范围模式", "调研模式")
RESEARCH_MODE = re.compile(r"^\*\*调研模式\*\*[:：]\s*(\w+)")
SRC_LABEL = re.compile(r"\[(用户|调研|推断|未验证假设)\]")
VALID_TYPES = {"When", "If", "While", "Where", "Ubiquitous", "Scenario"}
# P5 分两档：无歧义占位符 = ERROR；TBD/TODO 可能是正文内容（如"TODO 列表"产品）= WARNING
PLACEHOLDER_ERROR_RES = (
    re.compile(r"\[填写\]"),
    re.compile(r"<待定>"),
    # "未定"仅在句尾/标点前算占位；放过"未定义/未定期/未定向"等合法词
    re.compile(r"未定(?=[\s。；，、|）)】\]]|$)"),
)
PLACEHOLDER_WARN_RES = (
    re.compile(r"(?<![\w/])TBD(?![\w/-])"),
    re.compile(r"(?<![\w/])TODO(?![\w/-])"),
)
VAGUE = re.compile(r"(友好|智能|易用)")
BULLET = re.compile(r"^[*-]\s+\S")
REQUIRED_SECTIONS = {1: "产品概览", 3: "角色定义", 4: "功能需求", 5: "非功能性需求",
                     6: "假设、依赖与约束", 9: "非目标", 10: "Architecture Handoff",
                     11: "Epic Decomposition Notes"}


@dataclass
class Finding:
    level: str  # ERROR | WARNING
    rule: str
    where: str
    message: str


def section_ranges(lines: list[str]) -> dict[int, tuple[int, int]]:
    """按 `## N.` 标题切出各节的 [start, end) 行号区间。"""
    starts: list[tuple[int, int]] = []  # (section_no, line_idx)
    for i, line in enumerate(lines):
        m = H2.match(line)
        if m:
            starts.append((int(m.group(1)), i))
    ranges: dict[int, tuple[int, int]] = {}
    for idx, (no, start) in enumerate(starts):
        end = starts[idx + 1][1] if idx + 1 < len(starts) else len(lines)
        ranges[no] = (start, end)
    return ranges


def check(path: Path) -> list[Finding]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    findings: list[Finding] = []
    ranges = section_ranges(lines)

    # P1 头部元数据
    for field_name in META_FIELDS:
        if not any(line.startswith(f"**{field_name}**") for line in lines[:20]):
            findings.append(Finding("ERROR", "P1", "头部", f"缺少元数据字段 **{field_name}**"))
    research = "none"
    for line in lines[:20]:
        m = RESEARCH_MODE.match(line)
        if m:
            research = m.group(1)

    # P2 章节完整性
    for no, name in REQUIRED_SECTIONS.items():
        if no not in ranges:
            findings.append(Finding("ERROR", "P2", "章节", f"缺少 §{no} {name}（下游按节号消费）"))
    if research in ("light", "deep"):
        for no, name in ((2, "市场与替代方案"), (7, "证据与来源")):
            if no not in ranges:
                findings.append(Finding("ERROR", "P2", "章节", f"调研模式={research} 但缺少 §{no} {name}"))
    if not any(H15.match(line) for line in lines):
        findings.append(Finding("ERROR", "P2", "章节", "缺少 §1.5 核心用户旅程"))

    # P3/P4/P9 —— §4 内的 EARS 需求块
    if 4 in ranges:
        s4_start, s4_end = ranges[4]
        epic = "?"
        epic_rids: dict[str, list[int]] = {}
        blocks: list[tuple[str, str, str, int, list[str]]] = []  # (epic, rid, rtype, line, block_lines)
        current: tuple[str, str, str, int, list[str]] | None = None
        for i in range(s4_start, s4_end):
            line = lines[i]
            em = EPIC_HEAD.match(line)
            rm = REQ_START.match(line)
            if em or rm:
                if current:
                    blocks.append(current)
                    current = None
            if em:
                epic = f"Epic {em.group(1)}"
                epic_rids.setdefault(epic, [])
                continue
            if rm:
                rid = rm.group(1)
                rtype = re.split(r"[:：]", rm.group(2))[0].strip()
                epic_rids.setdefault(epic, []).append(int(rid[1:]))
                current = (epic, rid, rtype, i + 1, [line])
            elif current:
                current[4].append(line)
        if current:
            blocks.append(current)

        for epic_name, rid, rtype, lineno, block_lines in blocks:
            where = f"{epic_name}/{rid}(L{lineno})"
            block = "\n".join(block_lines)
            if rtype not in VALID_TYPES:
                findings.append(Finding("ERROR", "P3", where, f"非法 EARS 类型 ({rtype})"))
            if "应" not in block:
                findings.append(Finding("ERROR", "P3", where, "需求块缺少响应词\"应\""))
            if not SRC_LABEL.search(block):
                findings.append(Finding("ERROR", "P3", where, "需求块缺少来源标注 [用户]/[调研]/[推断]"))
            if rtype == "If" and "期间" in block:
                findings.append(Finding("WARNING", "P9", where, "If 块含\"期间\"，疑似持续状态冒充不期望事件（应改 While）"))
            if rtype == "While" and "期间" not in block:
                findings.append(Finding("WARNING", "P9", where, "While 块不含\"期间\"，检查是否为状态驱动写法"))

        for epic_name, rids in epic_rids.items():
            dupes = sorted({r for r in rids if rids.count(r) > 1})
            for d in dupes:
                findings.append(Finding("ERROR", "P4", epic_name, f"R{d} 编号重复"))
            uniq = sorted(set(rids))
            if uniq and uniq != list(range(uniq[0], uniq[0] + len(uniq))):
                findings.append(Finding("WARNING", "P4", epic_name, f"R 编号跳号：{uniq}"))

        s4_text = "\n".join(lines[s4_start:s4_end])
        vm = VAGUE.search(s4_text)
        if vm:
            findings.append(Finding("WARNING", "P9", "§4", f"出现无度量模糊词\"{vm.group(1)}\"，需可测试化或删除"))

    # P5 占位符
    for i, line in enumerate(lines):
        for pat in PLACEHOLDER_ERROR_RES:
            if pat.search(line):
                findings.append(Finding("ERROR", "P5", f"L{i + 1}", f"占位符 {pat.pattern!r}: {line.strip()[:60]}"))
        for pat in PLACEHOLDER_WARN_RES:
            if pat.search(line):
                findings.append(Finding("WARNING", "P5", f"L{i + 1}", f"疑似占位符 {pat.pattern!r}（若为正文内容可忽略）: {line.strip()[:60]}"))

    # P6 §1.5 mermaid 模板占位
    if 1 in ranges:
        in_fence = False
        for i in range(*ranges[1]):
            if lines[i].strip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence and '"[' in lines[i]:
                findings.append(Finding("ERROR", "P6", f"L{i + 1}", "§1.5 mermaid 节点保留了方括号模板占位"))

    # P7 有 [推断] 时 §8 必须存在且非空
    if "[推断]" in text:
        if 8 not in ranges:
            findings.append(Finding("ERROR", "P7", "章节", "存在 [推断] 标注但缺少 §8 待验证假设"))
        else:
            rows = [lines[i] for i in range(*ranges[8]) if lines[i].lstrip().startswith("|")]
            if len(rows) < 3:  # 表头 + 分隔行 + ≥1 数据行
                findings.append(Finding("ERROR", "P7", "§8", "待验证假设表没有数据行"))

    # P8 §3 / §9 至少一条
    for no, label in ((3, "角色定义"), (9, "非目标")):
        if no in ranges:
            bullets = [lines[i] for i in range(*ranges[no]) if BULLET.match(lines[i])]
            if not bullets:
                findings.append(Finding("ERROR", "P8", f"§{no}", f"{label}没有任何条目"))

    return findings


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    total_errors = 0
    total_warnings = 0
    for arg in argv[1:]:
        path = Path(arg)
        try:
            findings = check(path)
        except OSError as e:
            print(f"✗ 读取失败 {path}: {e}", file=sys.stderr)
            return 2
        for x in findings:
            mark = "✗" if x.level == "ERROR" else "⚠"
            print(f"{mark} [{x.level}][{x.rule}] {path}:{x.where} — {x.message}")
        total_errors += sum(1 for x in findings if x.level == "ERROR")
        total_warnings += sum(1 for x in findings if x.level == "WARNING")
    print(
        f"\n校验完成：{len(argv) - 1} 个文件，{total_errors} ERROR，{total_warnings} WARNING"
        + ("（存在 ERROR，不得放行 vj-architecture）" if total_errors else " ✓")
    )
    return 1 if total_errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
