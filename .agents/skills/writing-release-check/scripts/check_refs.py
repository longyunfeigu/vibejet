#!/usr/bin/env python3
"""check_refs.py -- verify the `file:line` references in a Release-Check guide (STANDARD.md 1.13).

Usage (from the repo root, after the code change is committed):
    python3 .claude/skills/writing-release-check/scripts/check_refs.py <guide.md> [--rev <git rev>]

Checks, in "Entry points" / "How to verify" (and the -cn headings):
  * every distinct `METHOD /path` endpoint is followed, in the same list item, by a `file:line`
    somewhere in the guide;
  * every `file:line` resolves to exactly one tracked file and the line exists;
  * the line an endpoint points at really defines that endpoint (route decorator or path segment).
Every `file:line` anywhere in the guide is resolved too.

--rev reads code from a git revision instead of the working tree (default: working tree).
Exit 1 when any error is found; warnings alone exit 0. Standard library only.
"""

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field

CHECKED_SECTIONS = {"入口", "怎么算对", "entry points", "how to verify"}
ENDPOINT_RE = re.compile(r"`(GET|POST|PUT|PATCH|DELETE) (/[^`?]*)[^`]*`")
SERVICES_RE = re.compile(r"^services:\s*\[([^\]]*)\]", re.M)
SERVICE_DIRS = {
    "backend": "backend/", "frontend": "frontend/", "grpc": "backend/",
}
REF_RE = re.compile(r"`((?:[\w.\-]+/)*[\w.\-]+\.[a-z]{1,5}):(\d+)(?:-(\d+))?`|`:(\d+)(?:-(\d+))?`")
DECORATOR_RE = re.compile(r"""\.(get|post|put|patch|delete)\(\s*["']([^"']*)["']""", re.I)
LIST_ITEM_RE = re.compile(r"^(\d+\.|[-*])\s")
CODE_SPAN_RE = re.compile(r"`([^`]+)`")
QUOTED_RE = re.compile(r"\"([^\"]+)\"|「([^」]+)」|“([^”]+)”")
WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_\-]{3,}")
WINDOW_BEFORE, WINDOW_AFTER = 1, 1  # point at the decorator (or the def right under it)


@dataclass
class Ref:
    path: str
    start: int
    end: int
    raw: str


@dataclass
class Item:
    section: str
    line_no: int
    text: str
    checked: bool


@dataclass
class Report:
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


class Code:
    """Read tracked files from the working tree or a git revision."""

    def __init__(self, rev):
        self.rev = rev
        args = ["git", "ls-tree", "-r", "--name-only", rev] if rev else ["git", "ls-files"]
        self.files = subprocess.run(args, capture_output=True, text=True, check=True).stdout.split()
        self.cache = {}

    def resolve(self, path, hint_dirs):
        if path in self.files:
            return [path]
        matches = [f for f in self.files if f.endswith("/" + path)]
        for hint in sorted(hint_dirs, key=len, reverse=True):  # most specific directory first
            near = [m for m in matches if m.startswith(hint)]
            if len(near) == 1:
                return near
        return matches

    def lines(self, path):
        if path not in self.cache:
            if self.rev:
                text = subprocess.run(["git", "show", f"{self.rev}:{path}"], capture_output=True,
                                      text=True, check=True).stdout
            else:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            self.cache[path] = text.splitlines()
        return self.cache[path]


def split_items(markdown):
    """Yield top-level list items / paragraphs with the section they belong to."""
    items, section, current = [], "", None
    in_comment = False
    for no, line in enumerate(markdown.splitlines(), 1):
        if "<!--" in line:
            in_comment = True
        if in_comment:
            in_comment = "-->" not in line
            continue
        if line.startswith("## "):
            section, current = line[3:].strip(), None
            continue
        if not line.strip():
            current = None
            continue
        if current is None or LIST_ITEM_RE.match(line):
            current = Item(section, no, "", section.lower() in CHECKED_SECTIONS)
            items.append(current)
        current.text += line + "\n"
    return items


def parse_refs(text, last_path):
    refs = []
    for m in REF_RE.finditer(text):
        if m.group(1):
            last_path = m.group(1)
            start, end = int(m.group(2)), int(m.group(3) or m.group(2))
        elif last_path:
            start, end = int(m.group(4)), int(m.group(5) or m.group(4))
        else:
            continue
        refs.append((m.start(), Ref(last_path, start, end, m.group(0))))
    return refs, last_path


def normalize(path):
    return re.sub(r"\{[^}]*\}|<[^>]*>", "{}", path.rstrip("/"))


def route_suffix_matches(path, route):
    """True when `route` (a decorator path, maybe under a router prefix) is a suffix of `path`.

    `{param}` in the route matches any concrete segment the guide wrote, e.g. `e2e-no-such-session`.
    """
    have = [s for s in normalize(path).split("/") if s]
    want = [s for s in route.split("/") if s]
    if len(want) > len(have):
        return False
    tail = have[len(have) - len(want):]
    return all(w == "{}" or w == h for w, h in zip(want, tail))


def defines_endpoint(lines, ref, method, path):
    window = window_text(lines, ref)
    decorators = [(m.group(1).upper(), normalize(m.group(2))) for m in DECORATOR_RE.finditer(window)]
    if decorators:
        return any(meth == method and route_suffix_matches(path, p) for meth, p in decorators)
    static = [s for s in path.strip("/").split("/") if s and not s.startswith("{")]
    return bool(static) and static[-1] in window


def window_text(lines, ref):
    lo, hi = max(ref.start - 1 - WINDOW_BEFORE, 0), min(ref.end + WINDOW_AFTER, len(lines))
    return "\n".join(lines[lo:hi])


def mentions(item_text):
    """Words of 4+ chars inside the item's backticked spans, minus endpoints and refs."""
    spans = [s for s in CODE_SPAN_RE.findall(item_text) if not REF_RE.fullmatch(f"`{s}`")]
    spans += ["".join(groups) for groups in QUOTED_RE.findall(item_text)]  # page text such as "Observe only" or 「最近通话」
    words = {w for s in spans for w in WORD_RE.findall(s)}
    env_parts = {p.lower() for w in words if w.isupper() and "_" in w for p in w.split("_") if len(p) >= 4}
    return words, env_parts  # env vars map to lower-case settings fields: VERDICT_MODEL -> model


def check_ref(code, ref, hint_dirs, where, report):
    found = code.resolve(ref.path, hint_dirs)
    if not found:
        report.errors.append(f"{where}: {ref.raw} -- no tracked file matches `{ref.path}`")
        return None
    if len(found) > 1:
        report.errors.append(f"{where}: {ref.raw} -- `{ref.path}` matches {len(found)} files "
                             f"({', '.join(found[:3])}...); write a longer path")
        return None
    lines = code.lines(found[0])
    if ref.end > len(lines) or ref.start < 1 or ref.start > ref.end:
        report.errors.append(f"{where}: {ref.raw} -- {found[0]} has {len(lines)} lines")
        return None
    return lines


def service_dirs(markdown):
    m = SERVICES_RE.search(markdown)
    keys = [k.strip().split(".")[0] for k in m.group(1).split(",")] if m else []
    return {SERVICE_DIRS[k] for k in keys if k in SERVICE_DIRS}


def check_guide(markdown, code):
    """An endpoint counts as cited when some `file:line` in the same item defines it."""
    report, last_path = Report(), None
    hint_dirs = service_dirs(markdown)
    cited, uncited = set(), {}
    for item in split_items(markdown):
        refs, last_path = parse_refs(item.text, last_path)
        where = f"line {item.line_no} [{item.section}]"
        resolved = [(ref, check_ref(code, ref, hint_dirs, where, report)) for _, ref in refs]
        resolved = [(ref, lines) for ref, lines in resolved if lines is not None]
        for ref, _ in resolved:  # later short paths like `agents.py` resolve next to earlier full ones
            hint_dirs.add(code.resolve(ref.path, hint_dirs)[0].rsplit("/", 1)[0] + "/")
        if not item.checked:
            continue
        words, env_parts = mentions(item.text)
        for ref, lines in resolved:
            window = window_text(lines, ref)
            hit = any(w in window for w in words) or any(p in window.lower() for p in env_parts)
            if words and not hit:
                report.warnings.append(f"{where}: {ref.raw} -- none of this item's backticked names appear "
                                       f"around that line; the line number may have drifted")
        for m in ENDPOINT_RE.finditer(item.text):
            method, path = m.group(1), m.group(2).strip()
            key = (method, normalize(path))
            if any(defines_endpoint(lines, ref, method, path) for ref, lines in resolved):
                cited.add(key)
            else:
                uncited.setdefault(key, f"{where} `{method} {path}`")
    for key, where in uncited.items():
        if key not in cited:
            report.errors.append(f"{where}: no `file:line` pointing at its route definition -- find it on the "
                                 f"source branch (mind router prefixes); if it does not exist, the endpoint is wrong")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("guide")
    parser.add_argument("--rev", help="read code from this git revision instead of the working tree")
    args = parser.parse_args()
    with open(args.guide, encoding="utf-8") as fh:
        markdown = fh.read()
    report = check_guide(markdown, Code(args.rev))
    for msg in report.errors:
        print(f"ERROR   {msg}")
    for msg in report.warnings:
        print(f"WARN    {msg}")
    print(f"{len(report.errors)} error(s), {len(report.warnings)} warning(s)")
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
