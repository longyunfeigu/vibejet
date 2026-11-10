#!/usr/bin/env python3
# input: `plan <review-pack-dir> [--for-execution [--research-only]]` or `runtime [repo-root]`
# output: semantic preflight findings + exit code (0=ready, 1=errors, 2=usage/path error)
# pos: vj-epic-plan handoff and vj-work load gate, after plan_lint. Unlike plan_lint's structural
#      checks, this validates shell syntax, tool/version-sensitive flags, planned paths, approval
#      state, and runtime capability vocabulary. Once updated, update this header and the evals.
"""Semantic preflight checks for vj workflow artifacts and runtime contracts."""

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


RUN_LINE = re.compile(r"^\s*run\s+(.+?)\s*$")
BACKTICK_PATH = re.compile(r"`([^`]+)`")
STATUS = re.compile(r"^status:\s*[\"']?([^\"'\s]+)", re.MULTILINE)
EPIC_ID = re.compile(r"^epic_id:\s*[\"']?([^\"'\s#]+)", re.MULTILINE)
OPEN_DECISION = re.compile(
    r"^\|\s*D\d+\s*\|\s*"
    r"(?:assumed|pending[- ]approval|evidence-required)"
    r"(?:\s+\(Confidence:.*?\))?\s*\|",
    re.MULTILINE | re.IGNORECASE,
)
OPEN_AC_DEVIATION = re.compile(
    r"^\|\s*ACD\d+\s*\|.*\|\s*pending[- ]approval\s*\|\s*$",
    re.MULTILINE | re.IGNORECASE,
)
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


def derive_work_dir(repo: Path, pack: Path) -> Path:
    match = re.match(r"\d{4}-\d{2}-\d{2}-(epic-.+)$", pack.name)
    name = match.group(1) if match else pack.name
    return repo / "docs/work/tasks" / name


def frontmatter_status(content: str) -> str | None:
    if not content.startswith("---\n"):
        return None
    end = content.find("\n---", 4)
    if end == -1:
        return None
    match = STATUS.search(content[4:end])
    return match.group(1) if match else None


def frontmatter_epic_id(content: str) -> str | None:
    if not content.startswith("---\n"):
        return None
    end = content.find("\n---", 4)
    if end == -1:
        return None
    match = EPIC_ID.search(content[4:end])
    return match.group(1) if match else None


def planned_catalog_markers(repo: Path, epic_id: str) -> list[str]:
    markers: list[str] = []
    epic = re.compile(rf"\bepic\s+{re.escape(epic_id)}\b", re.IGNORECASE)
    for area in ("api", "data", "ui"):
        root = repo / "docs/project" / area
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.md")):
            for line_no, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if "planned" in line.lower() and epic.search(line):
                    markers.append(f"{path.relative_to(repo)}:{line_no}")
    return markers


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


def scoped_section_lines(content: str, prefixes: tuple[str, ...]) -> list[str]:
    """Return only task sections that declare writable or newly tested paths."""
    selected: list[str] = []
    active_level: int | None = None
    for line in content.splitlines():
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if heading:
            level = len(heading.group(1))
            title = heading.group(2)
            if active_level is not None and level <= active_level:
                active_level = None
            if any(title.startswith(prefix) for prefix in prefixes):
                active_level = level
                continue
        if active_level is not None:
            selected.append(line)
    return selected


def collect_planned_paths(work_dir: Path, repo: Path) -> set[tuple[Path, bool]]:
    paths: set[tuple[Path, bool]] = set()
    for task in work_dir.glob("T*.md"):
        content = task.read_text(encoding="utf-8")
        write_lines = scoped_section_lines(content, ("Write scope",))
        has_may_modify = any("May modify" in line for line in write_lines)
        writable = not has_may_modify
        selected: list[str] = []
        for line in write_lines:
            if "May modify" in line:
                writable = True
                continue
            if "Do not modify" in line:
                writable = False
                continue
            if writable:
                selected.append(line)
        selected.extend(scoped_section_lines(content, ("测试新增",)))
        scoped = "\n".join(selected)
        for raw in BACKTICK_PATH.findall(scoped):
            if raw.startswith(("http://", "https://")) or any(
                char in raw for char in "{}*|"
            ):
                continue
            cleaned = raw.split("#", 1)[0].strip()
            directory_hint = cleaned.endswith("/")
            candidate = cleaned.rstrip("/")
            if not candidate or candidate.startswith(("D", "ACD", "U", "T")):
                continue
            path = (repo / candidate).resolve()
            paths.add((path, directory_hint or path.is_dir()))
    return paths


def extract_commands(verify: Path, report: Report) -> list[str]:
    commands: list[str] = []
    for line_no, line in enumerate(
        verify.read_text(encoding="utf-8").splitlines(), start=1
    ):
        match = RUN_LINE.match(line)
        if not match or line.lstrip().startswith("#"):
            continue
        try:
            tokens = shlex.split(match.group(1))
        except ValueError as exc:
            report.invalid("CMD_PARSE", f"verify.sh:{line_no}: {exc}")
            continue
        if tokens[:2] == ["bash", "-c"] and len(tokens) >= 3:
            commands.append(tokens[2])
        else:
            commands.append(shlex.join(tokens))
    report.command_count = len(commands)
    return commands


def command_context(command: str, repo: Path) -> tuple[Path, str]:
    match = re.match(r"^cd\s+([^&;]+?)\s*&&\s*(.+)$", command)
    if not match:
        return repo, command
    raw_dir = shlex.split(match.group(1).strip())[0]
    return (repo / raw_dir).resolve(), match.group(2).strip()


def is_within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def pytest_target(tokens: list[str]) -> str | None:
    try:
        start = tokens.index("pytest") + 1
    except ValueError:
        return None
    options_with_value = {
        "-c",
        "-k",
        "-m",
        "--confcutdir",
        "--durations",
        "--ignore",
        "--maxfail",
        "--rootdir",
        "--tb",
    }
    skip_next = False
    for token in tokens[start:]:
        if skip_next:
            skip_next = False
            continue
        if token in {"&&", ";", "||"}:
            break
        if token == "--":
            continue
        if token.startswith("-"):
            if token in options_with_value:
                skip_next = True
            continue
        return token
    return None


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


def path_is_planned(
    path: Path,
    planned: set[Path] | set[tuple[Path, bool]],
) -> bool:
    for entry in planned:
        if isinstance(entry, tuple):
            item, is_directory = entry
        else:
            item, is_directory = entry, entry.is_dir()
        if path == item or (is_directory and item in path.parents):
            return True
    return False


def check_command(
    command: str,
    *,
    repo: Path,
    planned_paths: set[Path] | set[tuple[Path, bool]],
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

    raw_target = pytest_target(tokens)
    if raw_target:
        raw = raw_target.split("::", 1)[0]
        if raw.endswith(".py") or "/" in raw:
            target = (cwd / raw).resolve()
            if not is_within(target, repo):
                report.invalid(
                    "PYTEST_TARGET", f"pytest target escapes repository: {target}"
                )
            elif not target.exists() and not path_is_planned(target, planned_paths):
                report.invalid(
                    "PYTEST_TARGET",
                    f"pytest target neither exists nor appears in task write scope: "
                    f"{target.relative_to(repo)}",
                )


def research_tasks(work_dir: Path) -> list[Path]:
    return [
        task
        for task in sorted(work_dir.glob("T*.md"))
        if re.search(
            r"^\s*-\s*Risk class:\s*research-only\b",
            task.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
    ]


def has_open_decisions(content: str) -> bool:
    return bool(OPEN_DECISION.search(content) or OPEN_AC_DEVIATION.search(content))


def research_write_paths(task: Path, repo: Path) -> set[Path]:
    content = task.read_text(encoding="utf-8")
    lines = scoped_section_lines(content, ("Write scope",))
    paths: set[Path] = set()
    writable = False
    for line in lines:
        if "May modify" in line:
            writable = True
            continue
        if "Do not modify" in line:
            writable = False
            continue
        if not writable:
            continue
        for raw in BACKTICK_PATH.findall(line):
            cleaned = raw.split("#", 1)[0].strip().rstrip("/")
            if cleaned:
                paths.add((repo / cleaned).resolve())
    return paths


def check_research_scope(tasks: list[Path], repo: Path, report: Report) -> None:
    allowed_roots = [
        (repo / ".vj").resolve(),
        (repo / "docs/reference/research").resolve(),
    ]
    for task in tasks:
        paths = research_write_paths(task, repo)
        if not paths:
            report.error(
                "RESEARCH_SCOPE", f"{task.name} has no explicit May modify path"
            )
        for path in paths:
            if not any(is_within(path, root) for root in allowed_roots):
                display = (
                    str(path.relative_to(repo)) if is_within(path, repo) else str(path)
                )
                report.error(
                    "RESEARCH_SCOPE",
                    f"{task.name} may write production path: {display}",
                )


def check_plan(
    pack: Path, *, as_json: bool, for_execution: bool, research_only: bool = False
) -> int:
    report = Report()
    if not pack.is_dir():
        print(f"ERROR: review pack not found: {pack}")
        return 2
    try:
        repo = find_repo_root(pack)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2
    work_dir = derive_work_dir(repo, pack)
    verify = work_dir / "verify.sh"

    lint = repo / ".agents/skills/_shared/scripts/plan_lint.py"
    if lint.is_file():
        proc = run_capture([sys.executable, str(lint), str(pack)], repo)
        if proc.returncode != 0:
            report.error("PLAN_LINT", proc.stdout.strip().replace("\n", " | ")[:800])
    else:
        report.error(
            "PLAN_LINT", f"missing structural linter: {lint.relative_to(repo)}"
        )

    if not verify.is_file():
        report.error("VERIFY_MISSING", f"missing {verify.relative_to(repo)}")
        return report.render(as_json)
    syntax = run_capture(["bash", "-n", str(verify)], repo)
    if syntax.returncode != 0:
        report.error("VERIFY_SYNTAX", syntax.stderr.strip())

    readme = pack / "README.md"
    if readme.is_file():
        content = readme.read_text(encoding="utf-8")
        status = frontmatter_status(content)
        epic_id = frontmatter_epic_id(content)
        if research_only:
            if status != "research-ready":
                report.error(
                    "PLAN_STATUS",
                    f"research-only execution requires status 'research-ready', got {status!r}",
                )
        elif for_execution:
            if status != "ready":
                report.error(
                    "PLAN_STATUS",
                    f"production execution requires status 'ready', got {status!r}",
                )
        elif status in {
            "active",
            "draft-unattended",
            "draft",
            "awaiting-approval",
            "research-ready",
        }:
            report.warn(
                "PLAN_STATUS", f"plan status is {status!r}; not production-ready"
            )
        if status == "completed" and epic_id:
            planned = planned_catalog_markers(repo, epic_id)
            if planned:
                report.error(
                    "CATALOG_NOT_ACTIVE",
                    "completed plan still has planned catalog markers: "
                    + ", ".join(planned[:8]),
                )

    decisions = pack / "decisions.md"
    if decisions.is_file() and has_open_decisions(
        decisions.read_text(encoding="utf-8")
    ):
        message = "decisions.md contains open or evidence-required decisions"
        if for_execution and not research_only:
            report.error("PENDING_DECISIONS", message)
        elif research_only:
            report.note(
                "PENDING_DECISIONS", f"{message}; allowed for evidence collection"
            )
        else:
            report.warn("PENDING_DECISIONS", message)

    if research_only:
        tasks = research_tasks(work_dir)
        if not tasks:
            report.error("RESEARCH_TASK", "no task declares Risk class: research-only")
        else:
            check_research_scope(tasks, repo, report)
            report.note(
                "RESEARCH_TASK",
                "allowed research tasks: " + ", ".join(task.name for task in tasks),
            )

    planned_paths = collect_planned_paths(work_dir, repo)
    reporters = vitest_reporters(repo / "frontend", report)
    commands = extract_commands(verify, report)
    for command in commands:
        check_command(
            command,
            repo=repo,
            planned_paths=planned_paths,
            reporters=reporters,
            report=report,
        )
    if not commands:
        report.warn("NO_COMMANDS", "verify.sh has no executable run commands")
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
    plan.add_argument("pack", type=Path)
    plan.add_argument("--for-execution", action="store_true")
    plan.add_argument(
        "--research-only",
        action="store_true",
        help="allow only research-only tasks while plan status is research-ready",
    )
    runtime = sub.add_parser("runtime")
    runtime.add_argument("root", type=Path, nargs="?", default=Path.cwd())
    runtime.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    if args.command == "plan":
        if args.research_only and not args.for_execution:
            parser.error("--research-only requires --for-execution")
        return check_plan(
            args.pack.resolve(),
            as_json=args.json,
            for_execution=args.for_execution,
            research_only=args.research_only,
        )
    return check_runtime(args.root.resolve(), as_json=args.json, strict=args.strict)


if __name__ == "__main__":
    sys.exit(main())
