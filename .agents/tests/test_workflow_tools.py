from __future__ import annotations

import importlib.util
import csv
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import ModuleType
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]

PLAN_FIXTURE = """---
type: plan
status: ready
policy: fast
source: "test"
date: 2026-11-13
---

# 一句话记一餐

> 一句话：测试用的计划。

## 做什么、为什么

小林说一句话就能记一餐。

## 卡片怎么确认

卡片确认后才写入记录。

## 要你拍板的决定

| 编号 | 状态 | 问题 | 不定会怎样 | 推荐 | 挡哪一步 |
|------|------|------|------------|------|----------|
| D1 | 待证据 | AI 能不能听懂口语 | 白做 | 先测 | 第 2 步 |

## 验收清单

### 记一餐

| 编号 | 要保证什么 | 怎么查 | 对应 PRD |
|------|------------|--------|----------|
| A1 | 确认后才计入 | 自动测试 | R2 |
| A2 | 改一下份量 | 自动测试 | — |
| A3 | 真实模型超时给出搜索 | 人工 | R1 |

## 执行顺序

1. 证据步骤：100 句真实说法，食物正确率 ≥85%。
2. 卡片确认写入，等第 1 步过线。

## 执行记录
"""

TEST_MAP = """
## 验收对应的测试

| 验收 | 测试 | 检查命令 |
|------|------|----------|
| A1 | test_only_confirmed_counts | `cd backend && uv run pytest tests/test_card.py -q` |
| A2 | test_edit_portion | `cd backend && uv run pytest tests/test_card.py -q` |
"""


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class WorkflowDoctorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module(
            "workflow_doctor",
            ROOT / ".agents/skills/_shared/scripts/workflow_doctor.py",
        )

    def test_rejects_unsupported_vitest_reporter(self) -> None:
        report = self.module.Report()
        self.module.check_command(
            "cd frontend && pnpm vitest run src/features/example --reporter=basic",
            repo=ROOT,
            reporters={"default", "minimal", "verbose"},
            report=report,
        )
        self.assertEqual(report.invalid_command_count, 1)
        self.assertTrue(any(item.code == "VITEST_REPORTER" for item in report.errors))

    def test_accepts_supported_vitest_reporter(self) -> None:
        report = self.module.Report()
        self.module.check_command(
            "cd frontend && pnpm vitest run src/features/example --reporter=minimal",
            repo=ROOT,
            reporters={"default", "minimal", "verbose"},
            report=report,
        )
        self.assertEqual(report.invalid_command_count, 0)
        self.assertFalse(report.errors)

    def test_vitest_reporters_preserves_default(self) -> None:
        output = "--reporter <name>  Specify reporters (default, minimal, verbose)"
        proc = subprocess.CompletedProcess([], 0, stdout=output, stderr="")
        with (
            mock.patch.object(self.module, "run_capture", return_value=proc),
            mock.patch.object(
                self.module.shutil, "which", return_value="/usr/bin/pnpm"
            ),
        ):
            report = self.module.Report()
            reporters = self.module.vitest_reporters(ROOT / "frontend", report)
        self.assertEqual(reporters, {"default", "minimal", "verbose"})

    def test_rejects_working_directory_outside_repo(self) -> None:
        report = self.module.Report()
        self.module.check_command(
            "cd /tmp && python3 -m unittest",
            repo=ROOT,
            reporters=set(),
            report=report,
        )
        self.assertTrue(any(item.code == "CMD_CWD" for item in report.errors))

    def test_plan_checks_commands_from_test_map(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".vj") as raw:
            plan = Path(raw) / "plan.md"
            plan.write_text(
                PLAN_FIXTURE + TEST_MAP.replace("cd backend", "cd no_such_dir"),
                encoding="utf-8",
            )
            with redirect_stdout(io.StringIO()) as out:
                result = self.module.check_plan(plan, as_json=True, for_execution=False)
            payload = json.loads(out.getvalue())
        self.assertEqual(result, 1)
        self.assertEqual(payload["commands"], 2)
        self.assertTrue(any(f["code"] == "CMD_CWD" for f in payload["findings"]))

    def test_runtime_scan_includes_top_level_vj_router(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            skills = root / ".agents/skills"
            (skills / "_shared").mkdir(parents=True)
            (skills / "_shared/runtime-contract.md").write_text(
                "# Contract\n", encoding="utf-8"
            )
            (skills / "vj").mkdir()
            (skills / "vj/SKILL.md").write_text(
                "Use AskUserQuestion.\n", encoding="utf-8"
            )
            with redirect_stdout(io.StringIO()):
                result = self.module.check_runtime(root, as_json=True, strict=True)
            self.assertEqual(result, 1)


class PlanLintTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module(
            "plan_lint", ROOT / ".agents/skills/_shared/scripts/plan_lint.py"
        )

    def test_table_split_preserves_pipe_inside_code_span(self) -> None:
        row = "| C01 | blocking | T001 | use catalog | `docs/project/api|data|ui/` |"
        self.assertEqual(len(self.module.split_markdown_table_row(row)), 5)

    def lint(self, text: str, for_execution: bool = False) -> list[str]:
        report = self.module.Report()
        self.module.lint(self.module.parse_plan(text), ROOT, for_execution, report)
        return report.errors

    def test_fixture_plan_passes(self) -> None:
        self.assertEqual(self.lint(PLAN_FIXTURE), [])

    def test_free_sections_are_not_required(self) -> None:
        text = PLAN_FIXTURE.replace("## 卡片怎么确认\n\n卡片确认后才写入记录。\n\n", "")
        self.assertEqual(self.lint(text), [])

    def test_missing_fixed_section_is_an_error(self) -> None:
        text = PLAN_FIXTURE.replace("## 执行顺序", "## 先后")
        self.assertTrue(any("[L2]" in e for e in self.lint(text)))

    def test_blocking_step_must_exist(self) -> None:
        text = PLAN_FIXTURE.replace("| 第 2 步 |", "| 第 5 步 |")
        self.assertTrue(any("[L3]" in e and "第 5 步" in e for e in self.lint(text)))

    def test_invalid_block_value_is_an_error(self) -> None:
        text = PLAN_FIXTURE.replace("| 第 2 步 |", "| 看情况 |")
        self.assertTrue(any("[L3]" in e for e in self.lint(text)))

    def test_open_decision_blocking_start_forbids_ready(self) -> None:
        text = PLAN_FIXTURE.replace("| 第 2 步 |", "| 开工 |")
        self.assertTrue(any("[L11]" in e for e in self.lint(text)))
        waiting = text.replace("status: ready", "status: awaiting-approval")
        self.assertEqual(self.lint(waiting), [])

    def test_blocking_first_step_counts_as_blocking_start(self) -> None:
        text = PLAN_FIXTURE.replace("| 第 2 步 |", "| 第 1 步 |")
        self.assertTrue(any("[L11]" in e for e in self.lint(text)))

    def test_settled_decision_cannot_block(self) -> None:
        text = PLAN_FIXTURE.replace("| D1 | 待证据 |", "| D1 | 已定 |")
        self.assertTrue(any("[L3]" in e and "不挡" in e for e in self.lint(text)))
        self.assertEqual(self.lint(text.replace("| 第 2 步 |", "| 不挡 |")), [])

    def test_execution_requires_test_map_covering_auto_checks(self) -> None:
        self.assertTrue(any("[L13]" in e for e in self.lint(PLAN_FIXTURE, for_execution=True)))
        self.assertEqual(self.lint(PLAN_FIXTURE + TEST_MAP, for_execution=True), [])
        missing_a2 = (PLAN_FIXTURE + TEST_MAP).replace(
            "| A2 | test_edit_portion | `cd backend && uv run pytest tests/test_card.py -q` |\n", ""
        )
        self.assertTrue(any("A2" in e and "[L13]" in e for e in self.lint(missing_a2, for_execution=True)))

    def test_execution_requires_ready_status(self) -> None:
        text = PLAN_FIXTURE.replace("status: ready", "status: awaiting-approval") + TEST_MAP
        self.assertTrue(any("[L11]" in e for e in self.lint(text, for_execution=True)))

    def test_cases_dir_must_exist(self) -> None:
        text = PLAN_FIXTURE.replace("date: 2026-11-13", "date: 2026-11-13\ncases: AutoTest/modules/no-such-dir")
        self.assertTrue(any("[L14]" in e for e in self.lint(text)))

    def test_overview_only_checks_hygiene(self) -> None:
        self.assertEqual(self.lint("---\ntype: plan-overview\n---\n\n# 总览\n"), [])

    def lint_with_upstream(self, text: str, upstream_status: str, for_execution: bool = False) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            plans = Path(tmp)
            (plans / "2026-11-13-epic-1.md").write_text(f"---\ntype: plan\nstatus: {upstream_status}\n---\n")
            report = self.module.Report()
            self.module.lint(self.module.parse_plan(text), ROOT, for_execution, report, plans)
            return report.errors

    def test_execution_waits_for_upstream_plan(self) -> None:
        text = PLAN_FIXTURE.replace("status: ready", "status: ready\nafter: 2026-11-13-epic-1") + TEST_MAP
        self.assertTrue(any("[L12]" in e for e in self.lint_with_upstream(text, "in-progress", True)))
        self.assertEqual(self.lint_with_upstream(text, "done", True), [])
        missing = text.replace("epic-1", "epic-9")
        self.assertTrue(any("[L12]" in e for e in self.lint_with_upstream(missing, "done")))


class PlanCaseTraceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module(
            "plan_case_trace", ROOT / ".agents/skills/_shared/scripts/plan_case_trace.py"
        )

    HEADER = ["用例编号", "需求/缺陷编号", "模块", "功能点", "场景标题", "用例类型", "优先级", "执行方式",
              "前置条件", "测试数据", "测试步骤", "预期结果", "后置清理", "BDD 标签", "负责人", "备注"]

    def run_trace(self, notes: list[tuple[str, str]]) -> tuple[list[str], list[str], int]:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            (repo / ".git").mkdir()
            cases = repo / "AutoTest/modules/demo/feat/cases"
            cases.mkdir(parents=True)
            with (cases / "manual-test-cases-cn.csv").open("w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(self.HEADER)
                for i, (req, note) in enumerate(notes, 1):
                    writer.writerow([f"DEMO-FT-{i:03d}", req] + [""] * 2 + [f"场景{i}"] + [""] * 10 + [note])
            plan = repo / "docs/work/plans/2026-11-13-epic-1.md"
            plan.parent.mkdir(parents=True)
            plan.write_text(
                PLAN_FIXTURE.replace("date: 2026-11-13", "date: 2026-11-13\ncases: AutoTest/modules/demo"),
                encoding="utf-8",
            )
            return self.module.check(plan, repo)

    def test_every_acceptance_item_traced(self) -> None:
        missing, extras, total = self.run_trace([
            ("2026-11-13-epic-1", "对应验收：A1、A2"),
            ("2026-11-13-epic-1", "对应验收：A3"),
        ])
        self.assertEqual((missing, extras, total), ([], [], 2))

    def test_missing_item_and_backfill_candidate_reported(self) -> None:
        missing, extras, total = self.run_trace([
            ("2026-11-13-epic-1", "对应验收：A1"),
            ("2026-11-13-epic-1", "PRD 兜底：访客跳登录"),
            ("other-plan", "对应验收：A2、A3"),
        ])
        self.assertEqual(missing, ["A2", "A3"])
        self.assertEqual(len(extras), 1)
        self.assertEqual(total, 2)


class EvalParserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module(
            "vj_eval",
            ROOT / ".agents/evals/vj-workflow/scripts/vj_eval.py",
        )

    def test_parses_claude_event_array(self) -> None:
        payload = [
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "Patch selected"}]},
            },
            {
                "type": "result",
                "usage": {"input_tokens": 10, "output_tokens": 2},
            },
        ]
        final, parsed = self.module.extract_final_message("claude", json.dumps(payload))
        self.assertEqual(final, "Patch selected")
        self.assertEqual(self.module.extract_tokens("claude", parsed), 12)

    def test_codex_tokens_do_not_double_count_cached_or_reasoning(self) -> None:
        payload = {
            "events": [
                {
                    "type": "turn.completed",
                    "usage": {
                        "input_tokens": 100,
                        "cached_input_tokens": 80,
                        "output_tokens": 20,
                        "reasoning_output_tokens": 10,
                    },
                }
            ]
        }
        self.assertEqual(self.module.extract_tokens("codex", payload), 120)

    def test_route_regex_does_not_accept_negated_substring(self) -> None:
        assertion = {
            "type": "final_regex",
            "pattern": r"^VJ_EVAL_ROUTE:\s*Story\s*$",
        }
        result = self.module.grade_assertion(
            assertion,
            ROOT,
            "Epic selected; cannot downgrade to Story.",
        )
        self.assertFalse(result["passed"])

    def test_runner_capacity_error_is_detected(self) -> None:
        self.assertIsNotNone(
            self.module.RUNNER_INFRA_FAILURE.search("You've hit your usage limit")
        )

    def test_workflow_fingerprint_changes_with_skill_content(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            skill = root / ".agents/skills/vj/SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text("first\n", encoding="utf-8")
            first = self.module.workflow_fingerprint(root)
            skill.write_text("second\n", encoding="utf-8")
            second = self.module.workflow_fingerprint(root)
            self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
