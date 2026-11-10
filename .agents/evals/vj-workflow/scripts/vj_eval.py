#!/usr/bin/env python3
"""Run isolated, repeatable evaluations for the vj workflow family."""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


EVAL_RESULT = re.compile(r"VJ_EVAL_RESULT:\s*(\{.*\})")
INTERVENTION_MARKERS = re.compile(
    r"(?:请(?:你|用户).{0,20}(?:确认|选择|提供)|需要用户确认|等待用户|STOP-and-ASK)",
    re.IGNORECASE,
)
RUNNER_INFRA_FAILURE = re.compile(
    r"(?:usage limit|rate limit|purchase more credits|not logged in|authentication failed|"
    r"model .* overloaded|connection (?:error|failed)|max(?:imum)? budget)",
    re.IGNORECASE,
)


def repo_root() -> Path:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(proc.stdout.strip()).resolve()


def load_suite(root: Path) -> dict[str, Any]:
    path = root / ".agents/evals/vj-workflow/evals.json"
    return json.loads(path.read_text(encoding="utf-8"))


def workflow_fingerprint(root: Path) -> str:
    files: set[Path] = set()
    for relative in (
        "AGENTS.md",
        "docs/reference/guides/ai-workflow.md",
        ".agents/skills/skill-rules.json",
    ):
        path = root / relative
        if path.is_file():
            files.add(path)
    skills = root / ".agents/skills"
    if skills.is_dir():
        for directory in skills.iterdir():
            if directory.name != "vj" and not directory.name.startswith("vj-"):
                continue
            for path in directory.rglob("*"):
                if (
                    path.is_file()
                    and "assets" not in path.parts
                    and path.suffix
                    in {
                        ".json",
                        ".md",
                        ".py",
                        ".sh",
                    }
                ):
                    files.add(path)
        shared = skills / "_shared"
        for name in (
            "runtime-contract.md",
            "vj-skill-conventions.md",
            "scripts/plan_lint.py",
            "scripts/workflow_doctor.py",
            "scripts/workflow_state.py",
        ):
            path = shared / name
            if path.is_file():
                files.add(path)
    digest = hashlib.sha256()
    for path in sorted(files):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()[:16]


def find_case(suite: dict[str, Any], case_id: str) -> dict[str, Any]:
    for case in suite["cases"]:
        if case["id"] == case_id:
            return case
    raise SystemExit(f"unknown case: {case_id}")


def run_command(
    args: list[str],
    *,
    cwd: Path,
    timeout: int | None = None,
    stdin: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        input=stdin,
        text=True,
        capture_output=True,
        timeout=timeout,
        env={**os.environ, "CI": "1", "NO_COLOR": "1"},
    )


def overlay_candidate(source: Path, target: Path) -> None:
    excludes = [
        ".git",
        ".vj",
        "backend/.venv",
        "frontend/node_modules",
        "frontend/dist",
        "__pycache__",
    ]
    if shutil.which("rsync"):
        cmd = ["rsync", "-a", "--delete"]
        for value in excludes:
            cmd.extend(["--exclude", value])
        cmd.extend([f"{source}/", f"{target}/"])
        subprocess.run(cmd, check=True)
        return

    def ignored(directory: str, names: list[str]) -> set[str]:
        rel = Path(directory).resolve().relative_to(source)
        blocked: set[str] = set()
        for name in names:
            candidate = str(rel / name) if str(rel) != "." else name
            if any(
                candidate == item or candidate.startswith(f"{item}/")
                for item in excludes
            ):
                blocked.add(name)
        return blocked

    shutil.copytree(source, target, dirs_exist_ok=True, ignore=ignored)


def prepare_worktree(
    root: Path,
    destination: Path,
    *,
    variant: str,
    baseline_root: Path | None,
) -> None:
    if destination.exists():
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(destination)],
            cwd=root,
            capture_output=True,
            text=True,
        )
        shutil.rmtree(destination, ignore_errors=True)
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "worktree", "add", "--detach", str(destination), "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )

    if variant == "candidate":
        overlay_candidate(root, destination)
        return

    if baseline_root is None:
        raise SystemExit("--baseline-root is required for baseline runs")
    skills = baseline_root / "skills"
    if not skills.is_dir():
        raise SystemExit(f"baseline skills not found: {skills}")
    shutil.rmtree(destination / ".agents/skills")
    shutil.copytree(skills, destination / ".agents/skills")
    for source_name, target_name in (
        ("AGENTS.md", "AGENTS.md"),
        ("ai-workflow.md", "docs/reference/guides/ai-workflow.md"),
    ):
        source = baseline_root / source_name
        if source.is_file():
            shutil.copy2(source, destination / target_name)


def apply_setup(worktree: Path, setup: dict[str, Any]) -> None:
    for pattern in setup.get("remove", []):
        matches = glob.glob(str(worktree / pattern))
        for raw in matches:
            path = Path(raw).resolve()
            if worktree.resolve() not in path.parents:
                raise RuntimeError(f"refusing to remove outside worktree: {path}")
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()


def agent_command(
    runner: str,
    prompt: str,
    *,
    worktree: Path,
    model: str | None,
    max_budget_usd: float,
) -> tuple[list[str], str | None]:
    if runner == "claude":
        command = [
            "claude",
            "-p",
            "--output-format",
            "json",
            "--permission-mode",
            "acceptEdits",
            "--no-session-persistence",
            "--max-budget-usd",
            str(max_budget_usd),
        ]
        if model:
            command.extend(["--model", model])
        command.append(prompt)
        return command, None

    command = [
        "codex",
        "exec",
        "--json",
        "--ephemeral",
        "--sandbox",
        "workspace-write",
        "--cd",
        str(worktree),
    ]
    if model:
        command.extend(["--model", model])
    command.append(prompt)
    return command, None


def extract_final_message(
    runner: str, stdout: str
) -> tuple[str, dict[str, Any] | None]:
    if runner == "claude":
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            return stdout, None
        if isinstance(payload, dict):
            result = payload.get("result")
            return str(result if result is not None else stdout), payload
        if isinstance(payload, list):
            messages: list[str] = []
            for event in payload:
                if not isinstance(event, dict) or event.get("type") != "assistant":
                    continue
                content = event.get("message", {}).get("content", [])
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        messages.append(str(block.get("text", "")))
            return (messages[-1] if messages else stdout), {"events": payload}
        return stdout, None

    final = ""
    events: list[dict[str, Any]] = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        events.append(event)
        if event.get("type") == "item.completed":
            item = event.get("item", {})
            if item.get("type") == "agent_message":
                final = str(item.get("text", final))
    return final or stdout, {"events": events}


def extract_tokens(runner: str, payload: dict[str, Any] | None) -> int | None:
    if not payload:
        return None
    if runner == "claude":
        if "events" in payload:
            result = next(
                (
                    event
                    for event in reversed(payload["events"])
                    if isinstance(event, dict) and event.get("type") == "result"
                ),
                {},
            )
            usage = result.get("usage", {})
        else:
            usage = payload.get("usage", {})
        values = [
            usage.get("input_tokens"),
            usage.get("output_tokens"),
            usage.get("cache_creation_input_tokens"),
            usage.get("cache_read_input_tokens"),
        ]
        ints = [value for value in values if isinstance(value, int)]
        return sum(ints) if ints else None

    for event in reversed(payload.get("events", [])):
        usage = event.get("usage") or event.get("turn", {}).get("usage")
        if isinstance(usage, dict):
            total = usage.get("total_tokens")
            if isinstance(total, int):
                return total
            input_tokens = usage.get("input_tokens")
            output_tokens = usage.get("output_tokens")
            if isinstance(input_tokens, int) or isinstance(output_tokens, int):
                # Codex reports cached/reasoning tokens as subsets of these totals.
                return (input_tokens or 0) + (output_tokens or 0)
    return None


def declared_metrics(final: str) -> dict[str, int | str | None]:
    matches = EVAL_RESULT.findall(final)
    if not matches:
        return {
            "status": None,
            "rework_rounds": None,
            "human_interventions": len(INTERVENTION_MARKERS.findall(final)),
        }
    try:
        value = json.loads(matches[-1])
    except json.JSONDecodeError:
        return {
            "status": None,
            "rework_rounds": None,
            "human_interventions": len(INTERVENTION_MARKERS.findall(final)),
        }
    return {
        "status": value.get("status"),
        "rework_rounds": value.get("rework_rounds"),
        "human_interventions": value.get("human_interventions"),
    }


def grade_assertion(
    assertion: dict[str, Any], worktree: Path, final: str
) -> dict[str, Any]:
    kind = assertion["type"]
    passed = False
    evidence = ""

    if kind == "final_contains":
        value = assertion["value"]
        passed = value.lower() in final.lower()
        evidence = f"final message {'contains' if passed else 'misses'} {value!r}"
    elif kind == "final_not_contains":
        value = assertion["value"]
        passed = value.lower() not in final.lower()
        evidence = f"final message {'omits' if passed else 'contains'} {value!r}"
    elif kind == "final_regex":
        pattern = assertion["pattern"]
        passed = re.search(pattern, final, re.MULTILINE) is not None
        evidence = f"final message {'matches' if passed else 'misses'} /{pattern}/"
    elif kind == "path_exists":
        path = worktree / assertion["path"]
        passed = path.exists()
        evidence = f"{path.relative_to(worktree)} exists={passed}"
    elif kind == "glob_count":
        matches = glob.glob(str(worktree / assertion["pattern"]))
        minimum = int(assertion.get("min", 0))
        maximum = assertion.get("max")
        passed = len(matches) >= minimum and (
            maximum is None or len(matches) <= int(maximum)
        )
        evidence = f"matched={len(matches)}, min={minimum}, max={maximum}"
    elif kind == "file_contains":
        path = worktree / assertion["path"]
        value = assertion["value"]
        content = path.read_text(encoding="utf-8") if path.is_file() else ""
        passed = value in content
        evidence = f"{assertion['path']} {'contains' if passed else 'misses'} {value!r}"
    elif kind == "command_exit":
        command = assertion["command"]
        proc = subprocess.run(
            ["bash", "-lc", command],
            cwd=worktree,
            capture_output=True,
            text=True,
            timeout=int(assertion.get("timeout_sec", 120)),
        )
        expected = int(assertion.get("exit", 0))
        passed = proc.returncode == expected
        output = (proc.stdout + proc.stderr).strip().replace("\n", " ")
        evidence = f"exit={proc.returncode}, expected={expected}, output={output[:500]}"
    else:
        evidence = f"unknown assertion type: {kind}"

    return {"type": kind, "passed": passed, "evidence": evidence}


def run_trial(
    root: Path,
    case: dict[str, Any],
    *,
    variant: str,
    trial: int,
    runner: str,
    model: str | None,
    baseline_root: Path | None,
    max_budget_usd: float,
) -> dict[str, Any]:
    runtime_label = f"{runner}-{model or 'default'}"
    run_root = (
        root / ".vj/evals" / case["id"] / variant / runtime_label / f"trial-{trial}"
    )
    repo_key = hashlib.sha256(str(root).encode()).hexdigest()[:10]
    worktree = (
        Path(tempfile.gettempdir())
        / "vj-workflow-evals"
        / f"{root.name}-{repo_key}"
        / case["id"]
        / variant
        / runtime_label
        / f"trial-{trial}"
    )
    run_root.mkdir(parents=True, exist_ok=True)
    prepare_worktree(root, worktree, variant=variant, baseline_root=baseline_root)
    apply_setup(worktree, case.get("setup", {}))

    prompt = (
        f"{case['prompt']}\n\n"
        "Eval hard boundary: work only in this disposable worktree; do not commit, push, "
        "or access the parent repository."
    )
    command, stdin = agent_command(
        runner,
        prompt,
        worktree=worktree,
        model=model,
        max_budget_usd=max_budget_usd,
    )
    started = time.monotonic()
    try:
        proc = run_command(
            command,
            cwd=worktree,
            timeout=int(case.get("timeout_sec", 1800)),
            stdin=stdin,
        )
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        proc = subprocess.CompletedProcess(
            command,
            124,
            stdout=exc.stdout or "",
            stderr=exc.stderr or "timeout",
        )
        timed_out = True
    duration_ms = int((time.monotonic() - started) * 1000)

    (run_root / "stdout.log").write_text(proc.stdout, encoding="utf-8")
    (run_root / "stderr.log").write_text(proc.stderr, encoding="utf-8")
    final, payload = extract_final_message(runner, proc.stdout)
    (run_root / "final.txt").write_text(final, encoding="utf-8")

    assertions = [
        grade_assertion(assertion, worktree, final)
        for assertion in case.get("assertions", [])
    ]
    metrics = declared_metrics(final)
    runner_error = proc.returncode != 0 and RUNNER_INFRA_FAILURE.search(
        f"{proc.stdout}\n{proc.stderr}"
    )
    result = {
        "case_id": case["id"],
        "case_revision": int(case.get("revision", 1)),
        "workflow_fingerprint": workflow_fingerprint(worktree),
        "stage": case.get("stage"),
        "variant": variant,
        "trial": trial,
        "runner": runner,
        "model": model,
        "max_budget_usd": max_budget_usd,
        "timeout_sec": int(case.get("timeout_sec", 1800)),
        "passed": proc.returncode == 0
        and not timed_out
        and all(x["passed"] for x in assertions),
        "valid_trial": not bool(runner_error),
        "runner_error": runner_error.group(0) if runner_error else None,
        "exit_code": proc.returncode,
        "timed_out": timed_out,
        "duration_ms": duration_ms,
        "tokens": extract_tokens(runner, payload),
        "human_interventions": metrics["human_interventions"],
        "rework_rounds": metrics["rework_rounds"],
        "agent_status": metrics["status"],
        "assertions": assertions,
        "worktree": str(worktree),
    }
    (run_root / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def summarize(root: Path) -> int:
    suite = load_suite(root)
    expected_revisions = {
        case["id"]: int(case.get("revision", 1)) for case in suite["cases"]
    }
    result_paths: list[Path] = []
    paths = list((root / ".vj/evals").glob("*/*/*/trial-*/result.json"))
    # Compatibility with results written by the first runner revision.
    paths.extend((root / ".vj/evals").glob("*/*/trial-*/result.json"))
    result_paths.extend(paths)
    latest: dict[tuple[Any, ...], tuple[int, dict[str, Any]]] = {}
    for path in result_paths:
        result = json.loads(path.read_text(encoding="utf-8"))
        if int(result.get("case_revision", 1)) != expected_revisions.get(
            result["case_id"]
        ):
            continue
        if result.get("valid_trial", True) is False:
            continue
        fingerprint = result.get("workflow_fingerprint")
        worktree = Path(result.get("worktree", ""))
        if not fingerprint and worktree.is_dir():
            fingerprint = workflow_fingerprint(worktree)
            result["workflow_fingerprint"] = fingerprint
        fingerprint = fingerprint or "legacy-unknown"
        stdout_path = path.with_name("stdout.log")
        if stdout_path.is_file():
            _, payload = extract_final_message(
                result["runner"], stdout_path.read_text(encoding="utf-8")
            )
            tokens = extract_tokens(result["runner"], payload)
            if tokens is not None:
                result["tokens"] = tokens
        key = (
            result["case_id"],
            result["variant"],
            result["runner"],
            result.get("model"),
            result.get("max_budget_usd", "legacy-unknown"),
            fingerprint,
            result["trial"],
        )
        timestamp = path.stat().st_mtime_ns
        if key not in latest or timestamp > latest[key][0]:
            latest[key] = (timestamp, result)
    results = [item[1] for item in latest.values()]
    if not results:
        print("no eval results found")
        return 1

    groups: dict[tuple[str, str, str, str, str, str], list[dict[str, Any]]] = {}
    for result in results:
        groups.setdefault(
            (
                result["variant"],
                result["runner"],
                result.get("model") or "default",
                str(result.get("max_budget_usd", "legacy-unknown")),
                result.get("workflow_fingerprint") or "legacy-unknown",
                result["case_id"],
            ),
            [],
        ).append(result)
    for values in groups.values():
        values.sort(key=lambda item: item["trial"])

    variants = sorted({key[:5] for key in groups})
    summary: dict[str, Any] = {}
    for variant, runner, model, budget, fingerprint in variants:
        case_runs = [
            values
            for (
                name,
                runtime,
                runtime_model,
                runtime_budget,
                revision_fingerprint,
                _,
            ), values in groups.items()
            if (name, runtime, runtime_model, runtime_budget, revision_fingerprint)
            == (variant, runner, model, budget, fingerprint)
        ]
        pass_at_1 = sum(bool(values[0]["passed"]) for values in case_runs) / len(
            case_runs
        )
        eligible = [values for values in case_runs if len(values) >= 3]
        pass_power_3 = (
            sum(all(item["passed"] for item in values[:3]) for values in eligible)
            / len(eligible)
            if eligible
            else None
        )
        flat = [item for values in case_runs for item in values]
        durations = [item["duration_ms"] for item in flat]
        tokens = [
            item["tokens"] for item in flat if isinstance(item.get("tokens"), int)
        ]
        summary[f"{variant}:{runner}:{model}:budget={budget}:{fingerprint}"] = {
            "cases": len(case_runs),
            "trials": len(flat),
            "pass@1": pass_at_1,
            "pass^3": pass_power_3,
            "avg_duration_ms": int(sum(durations) / len(durations)),
            "avg_tokens": int(sum(tokens) / len(tokens)) if tokens else None,
            "human_interventions": sum(
                item.get("human_interventions") or 0 for item in flat
            ),
            "rework_rounds": sum(item.get("rework_rounds") or 0 for item in flat),
        }

    output = root / ".vj/evals/benchmark.json"
    output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")

    run_parser = sub.add_parser("run")
    run_parser.add_argument("--case", required=True)
    run_parser.add_argument(
        "--variant", choices=("baseline", "candidate"), required=True
    )
    run_parser.add_argument("--runner", choices=("claude", "codex"), default="claude")
    run_parser.add_argument("--trials", type=int, default=1)
    run_parser.add_argument("--model", default=None)
    run_parser.add_argument("--baseline-root", type=Path, default=None)
    run_parser.add_argument("--max-budget-usd", type=float, default=5.0)
    sub.add_parser("summarize")
    args = parser.parse_args()

    root = repo_root()
    suite = load_suite(root)
    if args.command == "list":
        for case in suite["cases"]:
            print(f"{case['id']}: {case['stage']}")
        return 0
    if args.command == "summarize":
        return summarize(root)

    case = find_case(suite, args.case)
    for trial in range(1, args.trials + 1):
        result = run_trial(
            root,
            case,
            variant=args.variant,
            trial=trial,
            runner=args.runner,
            model=args.model,
            baseline_root=args.baseline_root.resolve() if args.baseline_root else None,
            max_budget_usd=args.max_budget_usd,
        )
        print(
            f"{result['case_id']} {result['variant']} trial={trial} "
            f"passed={result['passed']} duration_ms={result['duration_ms']} "
            f"tokens={result['tokens']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
