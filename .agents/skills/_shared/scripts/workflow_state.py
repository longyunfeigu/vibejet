#!/usr/bin/env python3
# input: init/transition/evidence/validate/show commands for a VJ run-state JSON file
# output: updated state path or validated JSON + exit code
# pos: runtime-only workflow state under .vj/runs; product status remains in Epic/Story frontmatter.
"""Create and validate the runtime state machine used by vj delivery tracks."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


TRANSITIONS: dict[str, set[str]] = {
    "initialized": {"planned", "blocked"},
    "planned": {"awaiting_approval", "approved", "running", "blocked"},
    "awaiting_approval": {"approved", "blocked"},
    "approved": {"running", "blocked"},
    "running": {"verifying", "blocked"},
    "verifying": {"running", "completed", "blocked"},
    "blocked": {"planned", "approved", "running"},
    "completed": set(),
}


def now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9一-鿿]+", "-", value).strip("-").lower()
    return value[:48] or "run"


def repo_root() -> Path:
    probe = Path.cwd().resolve()
    while probe != probe.parent:
        if (probe / ".git").exists():
            return probe
        probe = probe.parent
    raise ValueError("not inside a git repository")


def read_state(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read state {path}: {exc}") from exc


def write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = now()
    handle, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(state, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def validate_state(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "version",
        "run_id",
        "source",
        "track",
        "policy",
        "status",
        "commit_policy",
        "created_at",
        "updated_at",
        "history",
        "evidence",
    }
    missing = sorted(required - state.keys())
    if missing:
        errors.append(f"missing fields: {', '.join(missing)}")
    if state.get("version") != 1:
        errors.append(f"unsupported version: {state.get('version')!r}")
    if not isinstance(state.get("run_id"), str) or not state.get("run_id"):
        errors.append("run_id must be a non-empty string")
    if not isinstance(state.get("source"), str) or not state.get("source"):
        errors.append("source must be a non-empty string")
    if state.get("track") not in {"Patch", "Story", "Epic"}:
        errors.append(f"invalid track: {state.get('track')!r}")
    if state.get("policy") not in {"fast", "strict"}:
        errors.append(f"invalid policy: {state.get('policy')!r}")
    if state.get("status") not in TRANSITIONS:
        errors.append(f"invalid status: {state.get('status')!r}")
    if state.get("commit_policy") not in {"enabled", "disabled-by-user"}:
        errors.append(f"invalid commit_policy: {state.get('commit_policy')!r}")
    history = state.get("history")
    if not isinstance(history, list):
        errors.append("history must be an array")
    elif not history:
        errors.append("history must not be empty")
    else:
        for index, item in enumerate(history):
            if (
                not isinstance(item, dict)
                or not {"at", "from", "to", "reason"} <= item.keys()
            ):
                errors.append(f"history[{index}] is malformed")
        last = history[-1] if isinstance(history[-1], dict) else {}
        if last.get("to") != state.get("status"):
            errors.append("status must match the final history transition")
    evidence = state.get("evidence")
    if not isinstance(evidence, list):
        errors.append("evidence must be an array")
    else:
        for index, item in enumerate(evidence):
            if (
                not isinstance(item, dict)
                or not {"at", "kind", "result"} <= item.keys()
            ):
                errors.append(f"evidence[{index}] is malformed")
            elif item.get("result") not in {"pass", "fail", "skipped"}:
                errors.append(f"evidence[{index}] has invalid result")
    return errors


def print_validation_errors(errors: list[str]) -> None:
    for error in errors:
        print(f"ERROR: {error}")


def command_init(args: argparse.Namespace) -> int:
    root = repo_root()
    run_id = f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{slugify(args.name)}-{uuid.uuid4().hex[:6]}"
    path = args.output or root / ".vj/runs" / run_id / "run-state.json"
    created = now()
    state = {
        "version": 1,
        "run_id": run_id,
        "source": args.source,
        "track": args.track,
        "policy": args.policy,
        "status": "initialized",
        "commit_policy": args.commit_policy,
        "created_at": created,
        "updated_at": created,
        "history": [
            {"at": created, "from": None, "to": "initialized", "reason": "run created"}
        ],
        "evidence": [],
    }
    write_state(path.resolve(), state)
    print(path.resolve())
    return 0


def command_transition(args: argparse.Namespace) -> int:
    path = args.state.resolve()
    try:
        state = read_state(path)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2
    errors = validate_state(state)
    if errors:
        print_validation_errors(errors)
        return 2
    current = state.get("status")
    if args.to not in TRANSITIONS.get(current, set()):
        print(f"ERROR: invalid transition {current!r} -> {args.to!r}")
        return 1
    changed = now()
    state["status"] = args.to
    state["history"].append(
        {"at": changed, "from": current, "to": args.to, "reason": args.reason}
    )
    write_state(path, state)
    print(path)
    return 0


def command_evidence(args: argparse.Namespace) -> int:
    path = args.state.resolve()
    try:
        state = read_state(path)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2
    errors = validate_state(state)
    if errors:
        print_validation_errors(errors)
        return 2
    state["evidence"].append(
        {
            "at": now(),
            "kind": args.kind,
            "path": args.path,
            "result": args.result,
            "command": args.command,
        }
    )
    write_state(path, state)
    print(path)
    return 0


def command_validate(args: argparse.Namespace) -> int:
    try:
        state = read_state(args.state.resolve())
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2
    errors = validate_state(state)
    if errors:
        print_validation_errors(errors)
        return 1
    print("RESULT: PASS")
    return 0


def command_show(args: argparse.Namespace) -> int:
    try:
        state = read_state(args.state.resolve())
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init")
    init.add_argument("--name", required=True)
    init.add_argument("--source", required=True)
    init.add_argument("--track", choices=("Patch", "Story", "Epic"), required=True)
    init.add_argument("--policy", choices=("fast", "strict"), required=True)
    init.add_argument(
        "--commit-policy",
        choices=("enabled", "disabled-by-user"),
        default="enabled",
    )
    init.add_argument("--output", type=Path)
    init.set_defaults(func=command_init)

    transition = sub.add_parser("transition")
    transition.add_argument("state", type=Path)
    transition.add_argument("--to", choices=tuple(TRANSITIONS), required=True)
    transition.add_argument("--reason", required=True)
    transition.set_defaults(func=command_transition)

    evidence = sub.add_parser("evidence")
    evidence.add_argument("state", type=Path)
    evidence.add_argument("--kind", required=True)
    evidence.add_argument("--path", default=None)
    evidence.add_argument(
        "--result", choices=("pass", "fail", "skipped"), required=True
    )
    evidence.add_argument("--command", default=None)
    evidence.set_defaults(func=command_evidence)

    validate = sub.add_parser("validate")
    validate.add_argument("state", type=Path)
    validate.set_defaults(func=command_validate)

    show = sub.add_parser("show")
    show.add_argument("state", type=Path)
    show.set_defaults(func=command_show)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
