#!/usr/bin/env python3
# input: --domains slug1,slug2（业务域，lower-kebab）[--frontend] [--repo-root DIR]
# output: markdown 侦察报告（stdout）——架构基线 / catalog 清单 / 后端复用锚点 /
#         共享注册点 / 前端锚点 / solutions 候选
# pos: vj-epic-plan Phase 2 确定性侦察脚本。替代原研究代理 A（架构与契约）/ C（codebase
#      侦察）/ D（solutions 检索）的确定性部分：这些信息可机械枚举，不需要 LLM 兜一圈；
#      主上下文拿到清单后只精读命中的少量文件补语义判断。Agent E（外部生态）仍是 LLM 任务。
#      一旦我被更新，务必更新我的开头注释以及所属文件夹的 md
"""Deterministic repo scout for vj-epic-plan Phase 2.

Usage:
    python3 scout.py --domains document,file-asset [--frontend] [--repo-root .]

只读；无外部依赖（stdlib）；扫不到的面输出「暂无」而不是报错退出。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", ".vj", "dist", "build"}


def iter_files(root: Path, exts: tuple[str, ...]) -> list[Path]:
    out: list[Path] = []
    if not root.is_dir():
        return out
    for p in root.rglob("*"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.is_file() and p.suffix in exts:
            out.append(p)
    return out


def grep_files(files: list[Path], patterns: list[str]) -> dict[str, list[str]]:
    """pattern -> 命中文件相对路径列表（每 pattern 上限 20）。"""
    hits: dict[str, list[str]] = {p: [] for p in patterns}
    regs = {p: re.compile(re.escape(p), re.I) for p in patterns}
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for p, rx in regs.items():
            if len(hits[p]) < 20 and rx.search(text):
                hits[p].append(str(f))
    return hits


def listing(path: Path, note: str = "") -> str:
    if not path.is_dir():
        return f"- `{path}`：不存在{('（' + note + '）') if note else ''}"
    names = sorted(
        p.name for p in path.iterdir() if not p.name.startswith(("__", "."))
    )
    return f"- `{path}`：{', '.join(names) if names else '（空）'}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--domains", required=True, help="逗号分隔业务域 slug")
    ap.add_argument("--frontend", action="store_true")
    ap.add_argument("--repo-root", default=".")
    args = ap.parse_args()

    root = Path(args.repo_root).resolve()
    domains = [d.strip() for d in args.domains.split(",") if d.strip()]
    # slug 变体：file-asset -> file_asset，提高命中率
    probes: list[str] = []
    for d in domains:
        probes += [d, d.replace("-", "_")]
    probes = list(dict.fromkeys(probes))

    print("# scout 侦察报告（确定性，只读）\n")
    print(f"- repo: `{root}`  domains: {', '.join(domains)}  frontend: {args.frontend}\n")

    print("## 1. 架构基线")
    for f, note in [
        (root / "AGENTS.md", "分层/UoW/约束真相源"),
        (root / "docs/project/architecture.md", "缺失时以 AGENTS.md 为基线"),
        (root / "backend/pyproject.toml", "import-linter 契约所在"),
    ]:
        print(f"- `{f.relative_to(root)}`：{'存在' if f.is_file() else '**不存在**'}（{note}）")

    print("\n## 2. Catalog 现状（planned 条目只属于其所属 plan）")
    for sub in ("api", "data", "ui"):
        print(listing(root / "docs/project" / sub))
    planned = []
    for f in iter_files(root / "docs/project", (".md",)):
        for i, line in enumerate(
            f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1
        ):
            if "planned (Epic" in line:
                planned.append(f"  - {f.relative_to(root)}:{i} {line.strip()[:70]}")
    print("- planned 标记：")
    print("\n".join(planned[:15]) if planned else "  - 暂无")

    print("\n## 3. 后端结构与业务域命中")
    for sub in (
        "backend/domain",
        "backend/application/ports",
        "backend/application/services",
        "backend/infrastructure/models",
        "backend/infrastructure/repositories",
        "backend/api/routes",
        "backend/alembic/versions",
    ):
        print(listing(root / sub))
    be_files = iter_files(root / "backend", (".py",))
    dom_hits = grep_files(be_files, probes)
    print("- 业务域命中（已存在的相关代码）：")
    any_hit = False
    for p, files in dom_hits.items():
        for f in files:
            print(f"  - `{Path(f).relative_to(root)}` ← {p}")
            any_hit = True
    if not any_hit:
        print("  - 暂无（全新业务域）")

    print("\n## 4. 既有权威实现锚点（复用优先，禁止重建）")
    anchors = grep_files(
        be_files,
        ["belongs_to", "IdempotencyService", "success_response", "BusinessException"],
    )
    for p, files in anchors.items():
        shown = [
            str(Path(f).relative_to(root))
            for f in files
            if "/tests/" not in f
        ][:5]
        print(f"- `{p}`：{', '.join(shown) if shown else '暂无'}")
    print(listing(root / "backend/infrastructure/external", "外部服务 adapter 家族"))

    print("\n## 5. 共享注册点（barrier task 的 write scope 候选）")
    for f in (
        "backend/main.py",
        "backend/api/dependencies.py",
        "backend/infrastructure/models/__init__.py",
        "backend/application/ports/unit_of_work.py",
    ):
        p = root / f
        print(f"- `{f}`：{'存在' if p.is_file() else '不存在'}")

    if args.frontend:
        print("\n## 6. 前端锚点")
        for sub in ("frontend/src/routes", "frontend/src/features", "frontend/src/components/layout"):
            print(listing(root / sub))
        for f in ("frontend/src/lib/apiClient.ts", "docs/project/DESIGN.md"):
            p = root / f
            print(f"- `{f}`：{'存在' if p.is_file() else '**不存在**'}")
        print(listing(root / "docs/reference/research/designs", "设计稿/参考"))
        golden = root / "docs/reference/research/designs/golden"
        print(f"- golden 目录：{'存在' if golden.is_dir() else '不存在（front-of-house 屏注意参考图前置闸）'}")

    print("\n## 7. solutions 候选（Agent D 的确定性部分；命中才值得精读正文）")
    sol_files = iter_files(root / "docs/solutions", (".md",))
    sol_files = [f for f in sol_files if f.name != "README.md"]
    if not sol_files:
        print("- 暂无沉淀")
    else:
        sol_hits = grep_files(sol_files, probes)
        seen: set[str] = set()
        for p, files in sol_hits.items():
            for f in files:
                if f not in seen:
                    print(f"- `{Path(f).relative_to(root)}` ← {p}")
                    seen.add(f)
        if not seen:
            print(f"- {len(sol_files)} 条沉淀均未命中业务域关键词")

    print("\n> 用法提醒：本报告是清单不是结论——主上下文按命中项精读少量文件补语义判断；")
    print("> 外部生态检索（build-vs-buy）不在本脚本范围，按 research-agents.md 派 Agent E。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
