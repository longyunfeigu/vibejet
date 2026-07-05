#!/usr/bin/env python3
# input: vj-epic-plan 产出的 review pack 目录路径（docs/tasks/plans/{date}-epic-{N}-{slug}/），
#        可选 --work-dir 覆盖默认推导（docs/tasks/work/epic-{N}-{slug}/）
# output: 机检报告（stdout）+ exit code（0=全过，1=有 ERROR，2=用法/路径错误）
# pos: vj-epic-plan Phase 5 写盘后必跑（exit!=0 不得 handoff）；vj-work Phase 1 装载前必跑。
#      把 review pack / task packets 的确定性一致约束从模型自查清单换成机检；
#      一旦我被更新，务必更新我的开头注释
"""Lint a vj-epic-plan review pack + its task packets for mechanical consistency.

机检规则（对应 vj-epic-plan SKILL.md Phase 5 / 各模板契约）：
  R1  review pack 三件套存在且非空：README.md / design.md / decisions.md
  R2  README.md 有 Known Conflicts 段且非空壳（表格有行或明确写"无"）
  R3  work_dir/task-index.md 存在；其中引用的每个 T{NNN} 都有对应 T{NNN}-*.md 文件
  R4  work_dir 下每个 T*.md 都被 task-index.md 引用（孤儿 task → WARNING）
  R5  task docs / design.md 引用的 D-ID / ACD-ID 在 decisions.md 中存在
  R6  task docs 引用的 design.md#anchor 能解析到 design.md 标题（ERROR）；
      锚到叙事区（非合同区块）标题 → WARNING（叙事区标题自由、不承载锚点）
  R7  task docs 的 Read first 路径存在（ERROR）；
      Write scope 路径不存在且其父目录也不存在 → WARNING（新文件正常，目录都没有才可疑）
  R8  task-index 的 Unit→Task 映射引用的 Story 在 epics 目录能找到（找不到 → WARNING）
  R9  模板占位残留（{N}/{slug}/YYYY-MM-DD/{U-ID}/T{NNN} 等字面残留）→ ERROR
  R10 work_dir/verify.sh 存在、非空、含 all 入口；Unit→Task 映射中的每个 U-ID 有 case 分支
      （缺 → WARNING，浏览器类验证可为 MANUAL）
  R11 design.md 叙事区（合同区之前）每个 h2 小节开头必须是 `> 一句话：…` 导读行
      （可跳读的人读主线；缺 → ERROR）
  R12 pipe 表格表头行后必须紧跟 GFM 分隔行（|---|），否则整块渲染成纯文本 → ERROR
      （检查 pack 三件套 + task-index + task docs，跳过 code fence）

Usage:
    python3 plan_lint.py <review-pack-dir> [--work-dir <dir>] [--repo-root <dir>]

Exit codes:
    0 — 无 ERROR（WARNING 不阻塞）
    1 — 存在 ERROR，禁止 handoff / 装载执行
    2 — 用法或路径错误
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

TASK_REF = re.compile(r"\bT(\d{3})\b")
DECISION_REF = re.compile(r"\b(ACD\d+|D\d+)\b")
DESIGN_ANCHOR = re.compile(r"design\.md#([A-Za-z0-9%_.\-]+)")
PLACEHOLDER = re.compile(
    r"\{date\}|\{N\}\b|\{slug\}|\{name\}|\{U-ID\}|\{story-id\}|\{epic-file\}"
    r"|T\{NNN\}|YYYY-MM-DD|\{review-pack-path\}"
)
PATH_LINE = re.compile(r"^\s*-\s*(?:[^`]{0,40})`([^`]+)`")
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)
UNIT_ID = re.compile(r"\bU(\d+)\b")
STORY_REF = re.compile(r"\b(\d+)\.(\d+)\b")


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, rule: str, msg: str) -> None:
        self.errors.append(f"[{rule}] {msg}")

    def warn(self, rule: str, msg: str) -> None:
        self.warnings.append(f"[{rule}] {msg}")

    def dump(self) -> int:
        for w in self.warnings:
            print(f"WARNING {w}")
        for e in self.errors:
            print(f"ERROR   {e}")
        total = f"{len(self.errors)} error(s), {len(self.warnings)} warning(s)"
        if self.errors:
            print(f"RESULT: FAIL — {total}")
            return 1
        print(f"RESULT: PASS — {total}")
        return 0


def github_slug(heading: str) -> str:
    """Approximate GitHub-style heading anchor."""
    text = unicodedata.normalize("NFKC", heading).strip().lower()
    text = re.sub(r"[^\w\s一-鿿-]", "", text)
    return re.sub(r"\s+", "-", text)


def section_body(content: str, title_pattern: str) -> str | None:
    """Return the body of the first section whose heading matches pattern."""
    match = re.search(rf"^#{{1,6}}\s+.*{title_pattern}.*$", content, re.MULTILINE)
    if not match:
        return None
    start = match.end()
    nxt = re.search(r"^#{1,6}\s+", content[start:], re.MULTILINE)
    return content[start : start + nxt.start()] if nxt else content[start:]


def malformed_table_heads(content: str) -> list[str]:
    """返回缺 GFM 分隔行的表头行（"L{行号}: 内容"），跳过 code fence。"""
    sep = re.compile(r"\|[\s:|-]+\|?")
    lines = content.splitlines()
    in_fence = False
    bad: list[str] = []
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith("```") or s.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence or not s.startswith("|"):
            continue
        prev = lines[i - 1].strip() if i else ""
        if prev.startswith("|"):
            continue  # 表体行，只查表头
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if not sep.fullmatch(nxt):
            bad.append(f"L{i + 1}: {s[:50]}")
    return bad


def is_effectively_empty(body: str) -> bool:
    """A section is an empty shell if it has no prose and no filled table row."""
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(">"):
            continue
        if re.fullmatch(r"\|[\s|:-]*\|?", stripped):  # header/separator/empty row
            continue
        if stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if any(cells) and not all(re.fullmatch(r":?-+:?", c) for c in cells if c):
                return False
            continue
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pack", help="review pack directory")
    parser.add_argument("--work-dir", default=None)
    parser.add_argument("--repo-root", default=None)
    args = parser.parse_args()

    pack = Path(args.pack).resolve()
    if not pack.is_dir():
        print(f"ERROR   review pack 目录不存在: {pack}")
        return 2

    repo_root = Path(args.repo_root).resolve() if args.repo_root else None
    if repo_root is None:
        probe = pack
        while probe != probe.parent:
            if (probe / ".git").exists():
                repo_root = probe
                break
            probe = probe.parent
        else:
            repo_root = Path.cwd()

    # derive work_dir from pack name {date}-epic-{N}-{slug}
    if args.work_dir:
        work_dir = Path(args.work_dir).resolve()
    else:
        m = re.match(r"\d{4}-\d{2}-\d{2}-(epic-.+)$", pack.name)
        work_dir = repo_root / "docs" / "tasks" / "work" / (m.group(1) if m else pack.name)

    rep = Report()

    # R1 review pack completeness
    docs: dict[str, str] = {}
    for name in ("README.md", "design.md", "decisions.md"):
        f = pack / name
        if not f.is_file() or not f.read_text(encoding="utf-8").strip():
            rep.error("R1", f"review pack 缺失或为空: {f.relative_to(repo_root)}")
        else:
            docs[name] = f.read_text(encoding="utf-8")

    # R2 Known Conflicts present and not an empty shell
    if "README.md" in docs:
        body = section_body(docs["README.md"], r"Known Conflicts")
        if body is None:
            rep.error("R2", "README.md 缺 Known Conflicts 段")
        elif is_effectively_empty(body) and "无" not in body:
            rep.error("R2", "README.md Known Conflicts 是空壳：要么列冲突，要么明确写\"无\"")

    # R9 placeholder residue in pack docs
    for name, content in docs.items():
        for ph in sorted(set(PLACEHOLDER.findall(content))):
            rep.error("R9", f"{name} 有模板占位残留: {ph!r}")

    # R12 malformed pipe tables in pack docs
    for name, content in docs.items():
        for bad in malformed_table_heads(content):
            rep.error("R12", f"{name} 表格缺 GFM 分隔行（渲染成纯文本）: {bad}")

    # task packets
    index_file = work_dir / "task-index.md"
    task_files = {p.name: p for p in work_dir.glob("T*.md")} if work_dir.is_dir() else {}
    index_content = ""
    if not index_file.is_file():
        rep.error("R3", f"缺 task-index.md: {index_file}")
    else:
        index_content = index_file.read_text(encoding="utf-8")
        for ph in sorted(set(PLACEHOLDER.findall(index_content))):
            rep.error("R9", f"task-index.md 有模板占位残留: {ph!r}")
        for bad in malformed_table_heads(index_content):
            rep.error("R12", f"task-index.md 表格缺 GFM 分隔行（渲染成纯文本）: {bad}")
        referenced = {f"T{n}" for n in TASK_REF.findall(index_content)}
        for tid in sorted(referenced):
            if not any(name.startswith(f"{tid}-") or name == f"{tid}.md" for name in task_files):
                rep.error("R3", f"task-index 引用 {tid} 但 {work_dir.name}/ 下无对应 T 文档")
        # R4 orphan task docs
        for name in sorted(task_files):
            tid = name.split("-")[0].removesuffix(".md")
            if tid not in referenced:
                rep.warn("R4", f"孤儿 task 文档未被 task-index 引用: {name}")

    decisions_ids: set[str] = set()
    if "decisions.md" in docs:
        decisions_ids = set(DECISION_REF.findall(docs["decisions.md"]))

    design_slugs: set[str] = set()
    if "design.md" in docs:
        design_slugs = {github_slug(h) for h in HEADING.findall(docs["design.md"])}

    for name, tf in sorted(task_files.items()):
        content = tf.read_text(encoding="utf-8")

        # R9 placeholders
        for ph in sorted(set(PLACEHOLDER.findall(content))):
            rep.error("R9", f"{name} 有模板占位残留: {ph!r}")

        # R12 malformed pipe tables
        for bad in malformed_table_heads(content):
            rep.error("R12", f"{name} 表格缺 GFM 分隔行（渲染成纯文本）: {bad}")

        # R5 decision anchors resolve
        if decisions_ids:
            for did in sorted(set(DECISION_REF.findall(content))):
                if did not in decisions_ids:
                    rep.error("R5", f"{name} 引用 {did}，但 decisions.md 中不存在")

        # R6 design anchors resolve；且只允许锚合同区块（叙事区标题自由、不稳定）
        contract_slugs = ("api-delta", "data-delta", "ui-surface-delta", "must-hold",
                          "risks", "reviewer-checklist", "术语表", "contracts")
        for anchor in sorted(set(DESIGN_ANCHOR.findall(content))):
            slug = anchor.lower()
            if design_slugs and slug not in design_slugs and not any(
                slug in s or s in slug for s in design_slugs
            ):
                rep.error("R6", f"{name} 引用 design.md#{anchor} 解析不到 design.md 标题")
            elif not any(c in slug for c in contract_slugs):
                rep.warn("R6", f"{name} 锚了 design.md 叙事区标题 #{anchor}（不稳定，应改锚合同区块或 decisions D/ACD）")

        # R7 path existence for Read first / Write scope
        for section in ("Read first", "Write scope"):
            body = section_body(content, section)
            if body is None:
                continue
            for line in body.splitlines():
                # 一行多路径守卫：R7 每行只检查首个路径，塞多个 = 后面的全是盲区
                if "Do not modify" not in line:
                    slashed = [t for t in re.findall(r"`([^`]+)`", line) if "/" in t]
                    if len(slashed) >= 2:
                        rep.warn(
                            "R7",
                            f"{name} {section} 一行含 {len(slashed)} 个路径（只有首个被检查），应一行一路径",
                        )
                pm = PATH_LINE.match(line)
                if not pm:
                    continue
                raw = pm.group(1).split("#")[0].strip()
                if not raw or raw.startswith(("http", "{", "docs/tasks")):
                    continue
                p = repo_root / raw
                if section == "Write scope":
                    # 新文件/新模块目录正常；父目录和祖父目录都不存在才可疑
                    if not p.exists() and not p.parent.exists() and not p.parent.parent.exists():
                        rep.warn("R7", f"{name} write scope 路径及其上两级目录均不存在: {raw}")
                elif not p.exists():
                    rep.error("R7", f"{name} {section} 路径不存在: {raw}")

    # R8 Unit→Story mapping stories exist
    if index_content:
        mapping = section_body(index_content, r"Unit to Task Mapping|Unit → Task|Unit→Task")
        epics_dir = repo_root / "docs" / "tasks" / "epics"
        if mapping and epics_dir.is_dir():
            for line in mapping.splitlines():
                if not line.strip().startswith("|") or "---" in line:
                    continue
                cells = [c.strip() for c in line.strip("|").split("|")]
                if len(cells) >= 2 and re.fullmatch(r"\d+\.\d+", cells[1]):
                    n, m = cells[1].split(".")
                    # 平铺模式文件名 story-N.M*.md，展开模式 us{NNN}-*.md 内含 "### Story N.M"
                    hits = list(epics_dir.rglob(f"story-{n}.{m}*.md"))
                    if not hits and not any(
                        f"Story {n}.{m}" in f.read_text(encoding="utf-8")
                        for f in epics_dir.rglob("*.md")
                    ):
                        rep.warn("R8", f"task-index 引用 Story {n}.{m}，epics 目录未找到")

    # R11 design.md 叙事区每个 h2 小节开头有导读行（> 一句话：…）
    if "design.md" in docs:
        d = docs["design.md"]
        contract_pos = re.search(r"^##\s+合同区", d, re.MULTILINE)
        narrative = d[: contract_pos.start()] if contract_pos else d
        for hm in re.finditer(r"^##\s+(.+?)\s*$", narrative, re.MULTILINE):
            first_line = ""
            in_comment = False
            for ln in narrative[hm.end():].splitlines():
                s = ln.strip()
                if not s:
                    continue
                if in_comment:
                    if "-->" in s:
                        in_comment = False
                    continue
                if s.startswith("<!--"):
                    if "-->" not in s:
                        in_comment = True
                    continue
                first_line = s
                break
            if not first_line.startswith("> 一句话："):
                rep.error(
                    "R11",
                    f"design.md 叙事小节「{hm.group(1)}」缺导读行"
                    "（h2 后第一行应为 `> 一句话：…`）",
                )

    # R10 verify.sh：每个 Unit 有函数且接进 ALL_UNITS（all 入口靠遍历 ALL_UNITS，漏加=静默漏跑）
    verify = work_dir / "verify.sh"
    if not verify.is_file() or not verify.read_text(encoding="utf-8").strip():
        rep.warn("R10", f"缺 verify.sh（Unit verification 可执行入口）: {verify}")
    else:
        vs = verify.read_text(encoding="utf-8")
        all_units_match = re.search(r'^ALL_UNITS="([^"]*)"', vs, re.MULTILINE)
        if "all" not in vs or not all_units_match:
            rep.warn("R10", "verify.sh 缺 all 入口或 ALL_UNITS 清单")
        wired = set(all_units_match.group(1).split()) if all_units_match else set()
        if index_content:
            units = set(UNIT_ID.findall(index_content))
            for u in sorted(units, key=int):
                if not re.search(rf"\bunit_U{u}\b", vs):
                    rep.warn("R10", f"verify.sh 缺 unit_U{u} 函数")
                elif f"U{u}" not in wired:
                    rep.error("R10", f"verify.sh 定义了 unit_U{u} 但未接进 ALL_UNITS（all 会静默漏跑）")

    return rep.dump()


if __name__ == "__main__":
    sys.exit(main())
