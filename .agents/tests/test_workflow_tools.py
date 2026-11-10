from __future__ import annotations

import importlib.util
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


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class AllocateIdsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module(
            "allocate_ids",
            ROOT / ".agents/skills/vj-epic-story/scripts/allocate_ids.py",
        )

    def test_derives_epic_and_local_story_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            epics = Path(raw)
            (epics / "epic-2-auth").mkdir()
            (epics / "epic-7-files.md").write_text("# Epic", encoding="utf-8")
            self.assertEqual(self.module.next_epic(epics), 8)

            epic = epics / "epic-2-auth"
            stories = epic / "stories"
            stories.mkdir()
            (epic / "epic.md").write_text("### Story 2.1: Login\n", encoding="utf-8")
            (stories / "us099-legacy.md").write_text(
                "### Story 2.4: Logout\n", encoding="utf-8"
            )
            self.assertEqual(self.module.next_story(2, epic), 5)


class WorkflowStateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.script = ROOT / ".agents/skills/_shared/scripts/workflow_state.py"

    def run_state(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(self.script), *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

    def test_valid_transition_and_user_commit_policy(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            state = Path(raw) / "run-state.json"
            created = self.run_state(
                "init",
                "--name",
                "test",
                "--source",
                "unit",
                "--track",
                "Story",
                "--policy",
                "fast",
                "--commit-policy",
                "disabled-by-user",
                "--output",
                str(state),
            )
            self.assertEqual(created.returncode, 0, created.stderr)
            moved = self.run_state(
                "transition", str(state), "--to", "planned", "--reason", "test"
            )
            self.assertEqual(moved.returncode, 0, moved.stderr)
            payload = json.loads(state.read_text(encoding="utf-8"))
            self.assertEqual(payload["commit_policy"], "disabled-by-user")
            self.assertEqual(payload["status"], "planned")

    def test_rejects_invalid_transition(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            state = Path(raw) / "run-state.json"
            self.run_state(
                "init",
                "--name",
                "test",
                "--source",
                "unit",
                "--track",
                "Patch",
                "--policy",
                "fast",
                "--output",
                str(state),
            )
            result = self.run_state(
                "transition", str(state), "--to", "completed", "--reason", "skip"
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("invalid transition", result.stdout)

    def test_rejects_corrupt_state_before_transition(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            state = Path(raw) / "run-state.json"
            state.write_text('{"status":"running"}\n', encoding="utf-8")
            result = self.run_state(
                "transition", str(state), "--to", "verifying", "--reason", "test"
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("missing fields", result.stdout)

    def test_full_lifecycle_with_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            state = Path(raw) / "run-state.json"
            created = self.run_state(
                "init",
                "--name",
                "lifecycle",
                "--source",
                "unit",
                "--track",
                "Story",
                "--policy",
                "fast",
                "--output",
                str(state),
            )
            self.assertEqual(created.returncode, 0, created.stderr)
            for target in ("planned", "running", "verifying"):
                moved = self.run_state(
                    "transition", str(state), "--to", target, "--reason", "test"
                )
                self.assertEqual(moved.returncode, 0, moved.stdout)
            evidence = self.run_state(
                "evidence",
                str(state),
                "--kind",
                "test",
                "--result",
                "pass",
                "--command",
                "python3 -m unittest",
            )
            self.assertEqual(evidence.returncode, 0, evidence.stdout)
            completed = self.run_state(
                "transition", str(state), "--to", "completed", "--reason", "verified"
            )
            self.assertEqual(completed.returncode, 0, completed.stdout)
            validated = self.run_state("validate", str(state))
            self.assertEqual(validated.returncode, 0, validated.stdout)


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
            planned_paths=set(),
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
            planned_paths={ROOT / "frontend/src/features/example"},
            reporters={"default", "minimal", "verbose"},
            report=report,
        )
        self.assertEqual(report.invalid_command_count, 0)
        self.assertFalse(report.errors)

    def test_collects_only_declared_write_and_test_paths(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            work = Path(raw)
            (work / "T001-example.md").write_text(
                "### Read first\n- `backend/`\n"
                "### Write scope\n- `backend/new_module/service.py`\n"
                "### 测试新增（test-first）\n- `backend/tests/test_new_module.py`\n",
                encoding="utf-8",
            )
            planned = self.module.collect_planned_paths(work, ROOT)
            self.assertNotIn((ROOT / "backend", True), planned)
            self.assertIn((ROOT / "backend/new_module/service.py", False), planned)
            self.assertIn((ROOT / "backend/tests/test_new_module.py", False), planned)

    def test_collect_planned_paths_excludes_do_not_modify(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            work = Path(raw)
            (work / "T001-example.md").write_text(
                "### Write scope\n- May modify:\n"
                "  - `.vj/spikes/example/`\n"
                "- Do not modify: `backend/` / `frontend/`\n",
                encoding="utf-8",
            )
            planned = self.module.collect_planned_paths(work, ROOT)
            self.assertIn((ROOT / ".vj/spikes/example", True), planned)
            self.assertNotIn((ROOT / "backend", True), planned)
            self.assertNotIn((ROOT / "frontend", True), planned)

    def test_research_scope_rejects_production_write(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            task = Path(raw) / "T000-example.md"
            task.write_text(
                "### Write scope\n- May modify:\n  - `backend/spike.py`\n",
                encoding="utf-8",
            )
            report = self.module.Report()
            self.module.check_research_scope([task], ROOT, report)
            self.assertTrue(
                any(item.code == "RESEARCH_SCOPE" for item in report.errors)
            )

    def test_open_decision_statuses_are_detected(self) -> None:
        for status in ("pending-approval", "evidence-required", "assumed"):
            self.assertTrue(
                self.module.has_open_decisions(
                    f"| D1 | {status} | question | stance | impact | rejected |"
                )
            )

    def test_pending_ac_deviation_is_open(self) -> None:
        self.assertTrue(
            self.module.has_open_decisions(
                "| ACD1 | Story AC | original | stance | partial | pending approval |"
            )
        )

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

    def test_pytest_target_after_flags_is_validated(self) -> None:
        report = self.module.Report()
        self.module.check_command(
            "cd backend && uv run pytest -q tests/definitely_missing.py",
            repo=ROOT,
            planned_paths=set(),
            reporters=set(),
            report=report,
        )
        self.assertTrue(any(item.code == "PYTEST_TARGET" for item in report.errors))

    def test_rejects_working_directory_outside_repo(self) -> None:
        report = self.module.Report()
        self.module.check_command(
            "cd /tmp && python3 -m unittest",
            repo=ROOT,
            planned_paths=set(),
            reporters=set(),
            report=report,
        )
        self.assertTrue(any(item.code == "CMD_CWD" for item in report.errors))

    def test_status_is_read_only_from_frontmatter(self) -> None:
        self.assertIsNone(self.module.frontmatter_status("# Body\nstatus: ready\n"))
        self.assertEqual(
            self.module.frontmatter_status("---\nstatus: ready\n---\n# Body\n"),
            "ready",
        )

    def test_epic_id_is_read_only_from_frontmatter(self) -> None:
        self.assertEqual(
            self.module.frontmatter_epic_id(
                '---\nepic_id: "12"\n---\n# Body\nepic_id: wrong\n'
            ),
            "12",
        )

    def test_finds_planned_catalog_marker_for_epic(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            catalog = root / "docs/project/api"
            catalog.mkdir(parents=True)
            (catalog / "feature.md").write_text(
                "introduced by Epic 3, status: planned\n", encoding="utf-8"
            )
            self.assertEqual(
                self.module.planned_catalog_markers(root, "3"),
                ["docs/project/api/feature.md:1"],
            )

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
