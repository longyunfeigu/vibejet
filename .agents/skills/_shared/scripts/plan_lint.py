#!/usr/bin/env python3
# input: vj-plan 产出的计划文件路径（docs/work/plans/{date}-{slug}.md）[--for-execution]；
#        frontmatter `after:` 里的前置计划按同目录的 {name}.md 找
# output: 机检报告（stdout）+ exit code（0=无 ERROR，1=有 ERROR，2=用法/路径错误）
# pos: vj-plan 交付前必跑；vj-work 写完"验收对应的测试"后带 --for-execution 跑。workflow_doctor.py 复用
#      parse_plan 检查那张表里的命令能不能跑。一旦我被更新，务必更新我的开头注释
"""Lint a vj-plan document: free-form body, three fixed sections that tools read.

计划只有三节是固定的（标题含关键词即可，编号可有可无）：要你拍板的决定 / 验收清单 / 执行顺序。
其余内容按这块工作的性质自由写，不检查。

机检规则（对应 vj-plan/assets/plan.template.md 头注释）：
  L1  frontmatter：type=plan；status ∈ awaiting-approval|ready|in-progress|done|blocked；policy ∈ fast|strict。
      type=plan-overview（整份 PRD 的拆分总览）只查 L9 / L10
  L2  三个固定节都在
  L3  决定：编号 D<n> 唯一；状态 ∈ 待你定|待证据|上线前定|已定；"挡哪一步" ∈ 不挡 / 开工 / 第 N 步，
      引用的步骤要在执行顺序里存在；已定 / 上线前定只能写不挡
  L4  验收清单：至少一项；编号 A<n> 唯一；"怎么查" ∈ 自动测试|浏览器|人工；"要保证什么"非空
  L5  执行顺序：至少一步（编号列表 1. 2. …）
  L9  表格表头后紧跟 GFM 分隔行
  L10 正文（代码块和注释之外）不残留模板占位 {…} / YYYY-MM-DD
  L11 状态：有"待你定 / 待证据"的决定挡开工（或挡第 1 步，等于挡开工）时，状态不能是 ready / in-progress；
      --for-execution 时状态必须是 ready 或 in-progress
  L12 前置计划：after 列出的计划文件要存在；--for-execution 时它们必须已是 done
  L14 frontmatter `cases:`（prd-to-bdd 生成用例的目录）写了就必须存在；用例和验收的逐条对应由 plan_case_trace.py 查
  L13 --for-execution：vj-work 开工时写的"验收对应的测试"一节存在，每个"自动测试""浏览器"验收项都对应了测试，
      表里引用的验收编号都存在

Usage:
    python3 plan_lint.py <plan.md> [--for-execution] [--repo-root DIR]
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

STATUSES = {"awaiting-approval", "ready", "in-progress", "done", "blocked"}
DECISION_STATUSES = {"待你定", "待证据", "上线前定", "已定"}
OPEN_DECISION = {"待你定", "待证据"}
CHECK_KINDS = {"自动测试", "浏览器", "人工"}
FIXED_SECTIONS = {"decisions": "要你拍板的决定", "checks": "验收清单", "order": "执行顺序"}
TEST_MAP_SECTION = "验收对应的测试"
STEP_ITEM = re.compile(r"^(\d+)\.\s+\S", re.M)
STEP_REF = re.compile(r"第\s*(\d+(?:\s*[、,，和]\s*\d+)*)\s*步")


@dataclass
class Plan:
    meta: dict[str, str]
    sections: dict[str, str]
    decisions: list[list[str]]
    checks: list[list[str]]
    steps: list[int]
    test_map: list[list[str]] | None
    body: str

    @property
    def after(self) -> list[str]:
        raw = self.meta.get("after", "").strip("[] ")
        return [x.strip().removesuffix(".md") for x in re.split(r"[,，\s]+", raw) if x.strip()]


def strip_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    meta = {}
    for line in text[4:end].splitlines():
        m = re.match(r"^([A-Za-z_]+):\s*[\"']?([^\"'#]*?)[\"']?\s*(?:#.*)?$", line)
        if m:
            meta[m.group(1)] = m.group(2).strip()
    return meta, text[end + 4 :]


def split_markdown_table_row(line: str) -> list[str]:
    """Split a simple GFM row without treating code-span or escaped pipes as cells."""
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|") and not text.endswith(r"\|"):
        text = text[:-1]
    cells: list[str] = []
    current: list[str] = []
    in_code = escaped = False
    for char in text:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            current.append(char)
            escaped = True
        elif char == "`":
            current.append(char)
            in_code = not in_code
        elif char == "|" and not in_code:
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    cells.append("".join(current).strip())
    return cells


def table_rows(text: str, id_pattern: str) -> list[list[str]]:
    rows = []
    for line in text.splitlines():
        if line.strip().startswith("|"):
            cells = split_markdown_table_row(line)
            if cells and re.fullmatch(id_pattern, cells[0]):
                rows.append(cells)
    return rows


def h2_sections(body: str) -> list[tuple[str, str]]:
    """[(标题, 正文)]，只切二级标题；代码块里的 ## 不算。"""
    masked = re.sub(r"```.*?```", lambda m: re.sub(r"[^\n]", " ", m.group(0)), body, flags=re.S)
    heads = list(re.finditer(r"^##\s+(.*)$", masked, re.M))
    out = []
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(body)
        out.append((h.group(1).strip(), body[h.end() : end]))
    return out


def parse_plan(text: str) -> Plan:
    meta, body = split_frontmatter(text)
    body = strip_comments(body)
    sections: dict[str, str] = {}
    test_map: list[list[str]] | None = None
    for title, content in h2_sections(body):
        for key, word in FIXED_SECTIONS.items():
            if word in title and key not in sections:
                sections[key] = content
        if TEST_MAP_SECTION in title:
            test_map = table_rows(content, r"A\d+")
    return Plan(
        meta=meta,
        sections=sections,
        decisions=table_rows(sections.get("decisions", ""), r"D\d+"),
        checks=table_rows(sections.get("checks", ""), r"A\d+"),
        steps=[int(n) for n in STEP_ITEM.findall(sections.get("order", ""))],
        test_map=test_map,
        body=body,
    )


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
            continue
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if not sep.fullmatch(nxt):
            bad.append(f"L{i + 1}: {s[:50]}")
    return bad


def blocked_steps(cell: str) -> tuple[str, list[int]] | None:
    """解析"挡哪一步"：返回 ("不挡"|"开工"|"步骤", [步骤号])；不合法返回 None。"""
    value = cell.strip()
    if value == "不挡":
        return "不挡", []
    if value == "开工":
        return "开工", []
    m = STEP_REF.search(value)
    if m:
        return "步骤", [int(n) for n in re.findall(r"\d+", m.group(1))]
    return None


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
        print(f"RESULT: {'FAIL' if self.errors else 'PASS'} — {total}")
        return 1 if self.errors else 0


def lint_text_hygiene(body: str, rep: Report) -> None:
    # L9 / L10
    for bad in malformed_table_heads(body):
        rep.error("L9", f"表格缺 GFM 分隔行: {bad}")
    prose = re.sub(r"```.*?```", "", body, flags=re.S)
    for ph in sorted(set(re.findall(r"\{[^{}\n]{1,40}\}|YYYY-MM-DD", prose)))[:5]:
        rep.error("L10", f"残留模板占位: {ph}")


def lint(plan: Plan, repo: Path, for_execution: bool, rep: Report, plans_dir: Path | None = None) -> None:
    if plan.meta.get("type") == "plan-overview":
        lint_text_hygiene(plan.body, rep)
        return
    # L1
    if plan.meta.get("type") != "plan":
        rep.error("L1", "frontmatter 缺 type: plan")
    status = plan.meta.get("status", "")
    if status not in STATUSES:
        rep.error("L1", f"status 非法: {status!r}（只用 {' / '.join(sorted(STATUSES))}）")
    if plan.meta.get("policy") not in {"fast", "strict"}:
        rep.error("L1", f"policy 非法: {plan.meta.get('policy')!r}")
    # L2
    for key, word in FIXED_SECTIONS.items():
        if key not in plan.sections:
            rep.error("L2", f"缺固定节（二级标题应含\"{word}\"）")
    # L5
    if "order" in plan.sections and not plan.steps:
        rep.error("L5", "执行顺序没有任何一步（写成编号列表 1. 2. …）")
    # L3
    decisions: dict[str, str] = {}
    blocks_start: list[str] = []
    for cells in plan.decisions:
        did = cells[0]
        if did in decisions:
            rep.error("L3", f"决定编号重复: {did}")
        state = cells[1] if len(cells) > 1 else ""
        if state not in DECISION_STATUSES:
            rep.error("L3", f"{did} 状态非法: {state!r}（只用 待你定 / 待证据 / 上线前定 / 已定）")
        decisions[did] = state
        if len(cells) < 6:
            rep.error("L3", f"{did} 列数不对，应为 编号 | 状态 | 问题 | 不定会怎样 | 推荐 | 挡哪一步")
            continue
        parsed = blocked_steps(cells[5])
        if parsed is None:
            rep.error("L3", f"{did} 挡哪一步非法: {cells[5]!r}（只用 不挡 / 开工 / 第 N 步）")
            continue
        kind, nums = parsed
        if state in {"已定", "上线前定"} and kind != "不挡":
            rep.error("L3", f"{did} 是{state}，不挡开发，挡哪一步应写\"不挡\"")
        for n in nums:
            if n not in plan.steps:
                rep.error("L3", f"{did} 挡第 {n} 步，但执行顺序里没有这一步")
        first = min(plan.steps) if plan.steps else 1
        if state in OPEN_DECISION and (kind == "开工" or first in nums):
            blocks_start.append(did)
    # L4
    checks: dict[str, str] = {}
    if not plan.checks:
        rep.error("L4", "验收清单没有任何一项（编号 A1、A2…）")
    for cells in plan.checks:
        aid = cells[0]
        if aid in checks:
            rep.error("L4", f"验收编号重复: {aid}")
        if len(cells) < 4:
            rep.error("L4", f"{aid} 列数不对，应为 编号 | 要保证什么 | 怎么查 | 对应 PRD")
            continue
        if not cells[1]:
            rep.error("L4", f"{aid} 没写要保证什么")
        if cells[2] not in CHECK_KINDS:
            rep.error("L4", f"{aid} 怎么查 非法: {cells[2]!r}（只用 自动测试 / 浏览器 / 人工）")
        checks[aid] = cells[2]
    lint_text_hygiene(plan.body, rep)
    # L11
    if blocks_start and status in {"ready", "in-progress"}:
        rep.error(
            "L11",
            f"{'、'.join(blocks_start)} 还没定且挡开工，状态应为 awaiting-approval",
        )
    if for_execution and status not in {"ready", "in-progress"}:
        rep.error("L11", f"开工要求状态为 ready 或 in-progress，当前是 {status!r}")
    # L12
    plans_dir = plans_dir or repo / "docs/work/plans"
    for name in plan.after:
        upstream = plans_dir / f"{name}.md"
        if not upstream.is_file():
            rep.error("L12", f"after 里的前置计划不存在: {name}.md")
            continue
        up_status = split_frontmatter(upstream.read_text(encoding="utf-8"))[0].get("status")
        if for_execution and up_status != "done":
            rep.error("L12", f"前置计划 {name} 还没做完（{up_status}），先做它")
    # L14
    cases = plan.meta.get("cases", "").strip()
    if cases and not (repo / cases).is_dir():
        rep.error("L14", f"cases 目录不存在: {cases}")
    # L13
    if for_execution:
        if plan.test_map is None:
            rep.error("L13", f"缺\"{TEST_MAP_SECTION}\"一节（vj-work 开工时先把验收项对应到测试）")
            return
        mapped = {cells[0] for cells in plan.test_map if len(cells) > 1 and cells[1].strip(" -—")}
        for cells in plan.test_map:
            if cells[0] not in checks:
                rep.error("L13", f"{TEST_MAP_SECTION}引用了不存在的验收项 {cells[0]}")
        for aid, kind in checks.items():
            if kind != "人工" and aid not in mapped:
                rep.error("L13", f"验收项 {aid}（{kind}）没有对应的测试")


def find_repo_root(start: Path) -> Path:
    for probe in [start, *start.parents]:
        if (probe / ".git").exists():
            return probe
    return Path.cwd()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--for-execution", action="store_true")
    parser.add_argument("--repo-root", type=Path, default=None)
    args = parser.parse_args()
    path = args.plan.resolve()
    if not path.is_file():
        print(f"ERROR   计划文件不存在: {path}")
        return 2
    repo = args.repo_root.resolve() if args.repo_root else find_repo_root(path.parent)
    rep = Report()
    lint(parse_plan(path.read_text(encoding="utf-8")), repo, args.for_execution, rep, path.parent)
    return rep.dump()


if __name__ == "__main__":
    sys.exit(main())
