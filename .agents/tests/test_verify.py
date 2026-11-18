from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]


def load_verify() -> ModuleType:
    path = ROOT / ".agents/skills/verify/scripts/verify.py"
    spec = importlib.util.spec_from_file_location("verify", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["verify"] = module
    spec.loader.exec_module(module)
    return module


verify = load_verify()


def check_names(paths: list[str]) -> list[str]:
    return [name for name, _, _ in verify.cheap_checks(paths)]


class VerifyTest(unittest.TestCase):
    def test_level_follows_the_widest_runtime_change(self) -> None:
        pick = verify.pick_level
        self.assertEqual(
            pick(["docs/a.md", ".agents/skills/vj/SKILL.md", "frontend/src/lib/README.md"]), "none"
        )
        self.assertEqual(pick(["backend/api/routes/auth.py", "docs/a.md"]), "api")
        self.assertEqual(pick(["backend/main.py", "frontend/src/main.tsx"]), "ui")
        self.assertEqual(pick(["docker-compose.yml"]), "ui")
        self.assertEqual(pick([]), "ui")

    def test_cheap_checks_only_cover_touched_areas(self) -> None:
        self.assertEqual(check_names(["backend/main.py"]), ["后端依赖方向", "后端测试"])
        self.assertNotIn("后端测试", check_names(["frontend/vite.config.ts"]))
        self.assertIn("AutoTest BDD 规范", check_names(["AutoTest/modules/x.feature"]))
        self.assertEqual(check_names(["docs/a.md"]), [])
        self.assertEqual(check_names(["AutoTest/AGENTS.md", "backend/README.md"]), [])
        self.assertEqual(check_names([]), check_names(["backend/x.py", "frontend/x.ts"]))

    def test_trailer_reports_the_failed_step(self) -> None:
        report = verify.Report()
        report.steps.append(verify.Step("后端启动", True, 1.0))
        self.assertEqual(verify.trailer(report, "api"), "Verified: smoke-api")
        report.steps.append(verify.Step("登录", False, 1.0))
        self.assertEqual(verify.trailer(report, "api"), "Verified: none (verify 失败于：登录)")

    def test_broken_envelope_reads_as_empty_instead_of_crashing(self) -> None:
        self.assertEqual(verify.envelope_data({"data": None}), {})
        self.assertEqual(verify.envelope_data("<html>502</html>"), {})
        self.assertEqual(verify.envelope_data({"data": {"username": "a"}}), {"username": "a"})

    def test_tail_keeps_the_first_error_line(self) -> None:
        text = "Error: Executable doesn't exist\n" + "\n".join(f"line {i}" for i in range(30))
        self.assertTrue(verify.tail(text).startswith("Error: Executable doesn't exist"))
        self.assertEqual(verify.tail("a\nb"), "a\nb")


if __name__ == "__main__":
    unittest.main()
