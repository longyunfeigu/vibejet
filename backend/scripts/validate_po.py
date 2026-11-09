#!/usr/bin/env python3
"""Validate .po files: syntax, and every key used in code has a non-empty translation.

Exit non-zero if any .po cannot be parsed, or a key used in code is missing or untranslated.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import polib  # type: ignore
except Exception:  # pragma: no cover
    print("polib not installed; install it to validate .po files", file=sys.stderr)
    sys.exit(1)

# \b：只认独立的 t(...)，否则 get("x") / split(".") 这类以 t( 结尾的调用都会被当成 key
KEY_RE = re.compile(r"\bt\(\s*['\"]([a-zA-Z0-9_.]+)['\"]")
MSGKEY_RE = re.compile(r"message_key\s*=\s*['\"]([a-zA-Z0-9_.]+)['\"]")
# tests 不是运行时代码，里面会故意用没有翻译的 key
EXCLUDE_DIRS = {".git", "venv", ".venv", "alembic", "locales", "grpc_app/generated", "tests"}


def _syntax_errors(po_files: list[Path]) -> list[str]:
    errors: list[str] = []
    for f in po_files:
        try:
            polib.pofile(str(f))
        except Exception as exc:  # pragma: no cover
            errors.append(f"{f}: {exc}")
    return errors


def _used_keys(src_root: Path) -> set[str]:
    used_keys: set[str] = set()
    for p in src_root.rglob("*.py"):
        if any(part in EXCLUDE_DIRS for part in p.relative_to(src_root).parts):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        used_keys.update(KEY_RE.findall(text))
        used_keys.update(MSGKEY_RE.findall(text))
    return used_keys


def _print_keys(label: str, f: Path, keys: list[str]) -> None:
    print(f"[i18n] {label} keys in {f}: {len(keys)}", file=sys.stderr)
    print("  " + ", ".join(keys[:20]) + (" ..." if len(keys) > 20 else ""), file=sys.stderr)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    po_files = list((root / "locales").glob("*/LC_MESSAGES/*.po"))
    if not po_files:
        return 0

    errors = _syntax_errors(po_files)
    if errors:
        print("PO syntax errors detected:\n" + "\n".join(errors), file=sys.stderr)
        return 1

    used_keys = _used_keys(root)
    problems = 0
    for f in po_files:
        po = polib.pofile(str(f))
        keys_in_po = {e.msgid for e in po}
        missing = sorted(used_keys - keys_in_po)
        untranslated = sorted(e.msgid for e in po if not (e.msgstr or "").strip())
        if missing:
            _print_keys("Missing", f, missing)
        if untranslated:
            _print_keys("Untranslated", f, untranslated)
        problems += len(missing) + len(untranslated)

        # info: extra keys (not used in code)
        extras = sorted(keys_in_po - used_keys)
        if extras:
            print(f"[i18n] Extra keys in {f}: {len(extras)} (info)")

    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
