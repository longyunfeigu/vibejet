#!/usr/bin/env python3
# input: vj-plan 计划文件路径；计划 frontmatter `cases:` 指向 prd-to-bdd 生成用例的目录（AutoTest/modules/<模块>）
# output: 核对报告（stdout）+ exit code（0=每条验收都对上了用例，1=有验收没对上，2=用法/路径错误）
# pos: vj-plan 调完 prd-to-bdd 后跑。只核对、不转换：用例由 prd-to-bdd 按它自己的写法生成（人读的就是它），
#      这里只保证"计划的验收一条不少地进了用例表"，并列出用例里有、计划里没有的（PRD 兜底补出来的，回填计划）。
#      一旦我被更新，务必更新我的开头注释和 .agents/tests/test_workflow_tools.py
"""Check that every acceptance item of a vj plan is traced by at least one prd-to-bdd case row.

约定（vj-plan 调用 prd-to-bdd 时传给它）：
  · 用例行的"需求/缺陷编号"列 = 计划文件名（不带 .md）
  · 用例行的"备注"列写"对应验收：A5、A6"
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from plan_lint import find_repo_root, parse_plan  # noqa: E402

REQ_COL, NOTE_COL, ID_COL, TITLE_COL = 1, 15, 0, 4
TRACE = re.compile(r"对应验收[:：]\s*([A\d、,，\s和]+)")


def case_rows(cases_dir: Path) -> list[list[str]]:
    rows: list[list[str]] = []
    for path in sorted(cases_dir.glob("**/cases/manual-test-cases-cn.csv")):
        with path.open(newline="", encoding="utf-8") as fh:
            rows.extend(r for r in list(csv.reader(fh))[1:] if r and r[0].strip())
    return rows


def traced_ids(row: list[str]) -> set[str]:
    note = row[NOTE_COL] if len(row) > NOTE_COL else ""
    found: set[str] = set()
    for m in TRACE.finditer(note):
        found.update(re.findall(r"A\d+", m.group(1)))
    return found


def check(plan_path: Path, repo: Path) -> tuple[list[str], list[str], int]:
    """返回 (没对上用例的验收编号, PRD 兜底补出来、没标验收的用例行, 本计划的用例行数)。"""
    plan = parse_plan(plan_path.read_text(encoding="utf-8"))
    raw = plan.meta.get("cases", "").strip()
    if not raw:
        raise ValueError("计划 frontmatter 没有 cases:（prd-to-bdd 生成用例的目录）")
    cases_dir = (repo / raw).resolve()
    if not cases_dir.is_dir():
        raise ValueError(f"cases 目录不存在: {raw}")
    stem = plan_path.stem
    mine = [r for r in case_rows(cases_dir) if len(r) > REQ_COL and r[REQ_COL].strip() == stem]
    covered: set[str] = set()
    extras: list[str] = []
    for row in mine:
        ids = traced_ids(row)
        covered |= ids
        if not ids:
            extras.append(f"{row[ID_COL]} {row[TITLE_COL] if len(row) > TITLE_COL else ''}".strip())
    missing = [cells[0] for cells in plan.checks if cells[0] not in covered]
    return missing, extras, len(mine)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    args = parser.parse_args()
    path = args.plan.resolve()
    if not path.is_file():
        print(f"ERROR   计划文件不存在: {path}")
        return 2
    try:
        missing, extras, total = check(path, find_repo_root(path.parent))
    except ValueError as exc:
        print(f"ERROR   {exc}")
        return 2
    for aid in missing:
        print(f"ERROR   验收项 {aid} 没有对上任何用例（用例备注应写\"对应验收：{aid}\"）")
    for row in extras:
        print(f"NOTE    用例 {row} 没标对应验收——多半是 PRD 兜底补出来的，看要不要回填进计划的验收清单")
    print(f"RESULT: {'FAIL' if missing else 'PASS'} — 本计划用例 {total} 行，{len(missing)} 条验收没对上，{len(extras)} 行用例待回填")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
