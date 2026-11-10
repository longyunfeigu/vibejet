#!/usr/bin/env python3
# input: `next-epic [epics-dir]` or `next-story <epic-number> <epic-path>`
# output: the next filesystem-derived numeric ID
# pos: vj-feature/vj-epic-story ID allocator; replaces the unused kanban counter/index.
"""Derive the next Epic or Epic-local Story number from existing artifacts."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


EPIC_PATH = re.compile(r"^epic-(\d+)(?:-|\.|$)")


def next_epic(path: Path) -> int:
    numbers: list[int] = []
    if not path.exists():
        return 1
    for child in path.iterdir():
        match = EPIC_PATH.match(child.name)
        if match:
            numbers.append(int(match.group(1)))
    return max(numbers, default=0) + 1


def story_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    files: list[Path] = []
    epic = path / "epic.md"
    if epic.is_file():
        files.append(epic)
    stories = path / "stories"
    if stories.is_dir():
        files.extend(sorted(stories.glob("*.md")))
    return files


def next_story(epic_number: int, path: Path) -> int:
    pattern = re.compile(rf"^###\s+Story\s+{epic_number}\.(\d+)\s*:", re.MULTILINE)
    numbers: list[int] = []
    for file in story_files(path):
        content = file.read_text(encoding="utf-8")
        numbers.extend(int(value) for value in pattern.findall(content))
    return max(numbers, default=0) + 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    epic = sub.add_parser("next-epic")
    epic.add_argument("path", type=Path, nargs="?", default=Path("docs/work/epics"))
    story = sub.add_parser("next-story")
    story.add_argument("epic_number", type=int)
    story.add_argument("path", type=Path)
    args = parser.parse_args()

    if args.command == "next-epic":
        print(next_epic(args.path))
    else:
        print(next_story(args.epic_number, args.path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
