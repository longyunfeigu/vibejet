#!/usr/bin/env python3
# input: `plan <计划文件> [--for-execution]` or `runtime [repo-root] [--strict]`
# output: semantic preflight findings + exit code (0=ready, 1=errors, 2=usage/path error)
# pos: vj-plan 交付前、vj-work 写完"验收对应的测试"后跑。先调 plan_lint 查结构；计划里有"验收对应的测试"
#      表时再查表里每条检查命令能不能跑（工具在不在、工作目录对不对、Vitest reporter 是否支持）。测试文件此时
#      还没写（先写测试），所以不查测试目标存在与否。runtime 子命令查 vj skill 里有没有写死厂商工具名。
#      Once updated, update this header and the tests.
"""Semantic preflight checks for vj plans and runtime contracts."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from plan_lint import parse_plan  # noqa: E402

REPORTER = re.compile(r"--reporter(?:=|\s+)([^\s\"']+)")
VENDOR_TERMS = {
    "AskUserQuestion": "ask_user",
    "Agent tool": "spawn_agent",
    "`Agent` tool": "spawn_agent",
    "`Agent` 工具": "spawn_agent",
    "Skill tool": "invoke_skill",
    "`Skill` 工具": "invoke_skill",
    "`Write` tool": "write_file",
    "`Write` 工具": "write_file",
    "multi_agent_v1.spawn_agent": "spawn_agent",
}


@dataclass
class Finding:
    level: str
    code: str
    message: str


class Report:
    def __init__(self) -> None:
        self.findings: list[Finding] = []
        self.command_count = 0
        self.invalid_command_count = 0

    def error(self, code: str, message: str) -> None:
        self.findings.append(Finding("ERROR", code, message))

    def warn(self, code: str, message: str) -> None:
        self.findings.append(Finding("WARNING", code, message))

    def note(self, code: str, message: str) -> None:
        self.findings.append(Finding("NOTE", code, message))

    def invalid(self, code: str, message: str) -> None:
        self.invalid_command_count += 1
        self.error(code, message)

    @property
    def errors(self) -> list[Finding]:
        return [item for item in self.findings if item.level == "ERROR"]

    def render(self, as_json: bool) -> int:
        payload = {
            "errors": len(self.errors),
            "warnings": sum(item.level == "WARNING" for item in self.findings),
            "commands": self.command_count,
            "invalid_commands": self.invalid_command_count,
            "invalid_command_rate": (
                self.invalid_command_count / self.command_count
                if self.command_count
                else 0.0
            ),
            "findings": [asdict(item) for item in self.findings],
        }
        if as_json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            for item in self.findings:
                print(f"{item.level:<7} [{item.code}] {item.message}")
            print(
                "RESULT: "
                f"{'FAIL' if self.errors else 'PASS'} - {payload['errors']} error(s), "
                f"{payload['warnings']} warning(s), {self.invalid_command_count}/"
                f"{self.command_count} invalid command(s)"
            )
        return 1 if self.errors else 0


def find_repo_root(start: Path) -> Path:
    probe = start.resolve()
    if probe.is_file():
        probe = probe.parent
    while probe != probe.parent:
        if (probe / ".git").exists():
            return probe
        probe = probe.parent
    raise ValueError(f"cannot find repository root from {start}")


def run_capture(
    command: list[str], cwd: Path, timeout: int = 30
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def command_context(command: str, repo: Path) -> tuple[Path, str]:
    match = re.match(r"^cd\s+([^&;]+?)\s*&&\s*(.+)$", command)
    if not match:
        return repo, command
    raw_dir = shlex.split(match.group(1).strip())[0]
    return (repo / raw_dir).resolve(), match.group(2).strip()


def is_within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def vitest_reporters(frontend: Path, report: Report) -> set[str]:
    if not frontend.is_dir() or not shutil.which("pnpm"):
        return set()
    proc = run_capture(["pnpm", "exec", "vitest", "run", "--help"], frontend)
    if proc.returncode != 0:
        report.warn(
            "VITEST_HELP",
            f"cannot inspect Vitest reporters: {proc.stderr.strip()[:200]}",
        )
        return set()
    match = re.search(r"--reporter <name>\s+Specify reporters \(([^)]+)\)", proc.stdout)
    if not match:
        report.warn("VITEST_HELP", "Vitest help did not expose the reporter list")
        return set()
    text = match.group(1)
    return {item.strip() for item in text.split(",") if item.strip()}


def check_command(
    command: str,
    *,
    repo: Path,
    reporters: set[str],
    report: Report,
) -> None:
    cwd, inner = command_context(command, repo)
    if not is_within(cwd, repo):
        report.invalid("CMD_CWD", f"working directory escapes repository: {cwd}")
        return
    if not cwd.is_dir():
        report.invalid(
            "CMD_CWD", f"working directory does not exist: {cwd.relative_to(repo)}"
        )
        return

    try:
        tokens = shlex.split(inner)
    except ValueError as exc:
        report.invalid("CMD_PARSE", f"cannot parse {command!r}: {exc}")
        return
    if not tokens:
        report.invalid("CMD_EMPTY", "empty verification command")
        return
    executable = tokens[0]
    if shutil.which(executable) is None and not (cwd / executable).exists():
        report.invalid("CMD_TOOL", f"tool not found for {command!r}: {executable}")
        return

    if "vitest" in tokens:
        reporter_match = REPORTER.search(inner)
        if reporter_match and reporters and reporter_match.group(1) not in reporters:
            report.invalid(
                "VITEST_REPORTER",
                f"unsupported Vitest reporter {reporter_match.group(1)!r}; available: "
                f"{', '.join(sorted(reporters))}",
            )


def check_plan(path: Path, *, as_json: bool, for_execution: bool) -> int:
    report = Report()
    if not path.is_file():
        print(f"ERROR: plan not found: {path}")
        return 2
    try:
        repo = find_repo_root(path)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    lint = repo / ".agents/skills/_shared/scripts/plan_lint.py"
    if lint.is_file():
        cmd = [sys.executable, str(lint), str(path)] + (["--for-execution"] if for_execution else [])
        proc = run_capture(cmd, repo)
        if proc.returncode != 0:
            report.error("PLAN_LINT", proc.stdout.strip().replace("\n", " | ")[:800])
    else:
        report.error("PLAN_LINT", f"missing structural linter: {lint.relative_to(repo)}")

    plan = parse_plan(path.read_text(encoding="utf-8"))
    commands = [
        raw.strip()
        for cells in plan.test_map or []
        for cell in cells[2:]
        for raw in re.findall(r"`([^`]+)`", cell)
    ]
    reporters = vitest_reporters(repo / "frontend", report) if commands else set()
    for command in commands:
        report.command_count += 1
        check_command(command, repo=repo, reporters=reporters, report=report)
    return report.render(as_json)


def check_runtime(root: Path, *, as_json: bool, strict: bool) -> int:
    report = Report()
    skills = root / ".agents/skills"
    if not skills.is_dir():
        print(f"ERROR: skills directory not found: {skills}")
        return 2
    contract = skills / "_shared/runtime-contract.md"
    if not contract.is_file():
        report.error("RUNTIME_CONTRACT", "missing _shared/runtime-contract.md")
    paths = set(skills.glob("vj/**/*.md")) | set(skills.glob("vj-*/**/*.md"))
    for path in sorted(paths):
        content = path.read_text(encoding="utf-8")
        for term, capability in VENDOR_TERMS.items():
            if term not in content:
                continue
            message = (
                f"{path.relative_to(root)} names vendor primitive {term!r}; "
                f"use capability {capability!r}"
            )
            if strict:
                report.error("VENDOR_PRIMITIVE", message)
            else:
                report.warn("VENDOR_PRIMITIVE", message)
    return report.render(as_json)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan")
    plan.add_argument("plan", type=Path)
    plan.add_argument("--for-execution", action="store_true")
    runtime = sub.add_parser("runtime")
    runtime.add_argument("root", type=Path, nargs="?", default=Path.cwd())
    runtime.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    if args.command == "plan":
        return check_plan(args.plan.resolve(), as_json=args.json, for_execution=args.for_execution)
    return check_runtime(args.root.resolve(), as_json=args.json, strict=args.strict)


if __name__ == "__main__":
    sys.exit(main())
