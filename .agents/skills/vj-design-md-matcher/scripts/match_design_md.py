#!/usr/bin/env python3
"""Retrieve and rank DESIGN.md references from awesome-design-md."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import urllib.error
import urllib.request
from urllib.parse import urljoin
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable


DEFAULT_REPO = "VoltAgent/awesome-design-md"
DEFAULT_REF = "main"
SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CACHE = SKILL_DIR / "assets" / "awesome-design-md"
VIBEUI_BASE_URL = "https://vibeui.top/"
VIBEUI_DESIGNS_URL = urljoin(VIBEUI_BASE_URL, "site-assets/designs.js")
README_URL = "https://raw.githubusercontent.com/{repo}/{ref}/README.md"
RAW_DESIGN_URL = "https://raw.githubusercontent.com/{repo}/{ref}/design-md/{slug}/DESIGN.md"
CONTENTS_URL = "https://api.github.com/repos/{repo}/contents/design-md?ref={ref}"
HTML_DESIGN_URL = "https://github.com/{repo}/tree/{ref}/design-md/{slug}"


@dataclass
class Candidate:
    name: str
    slug: str
    category: str = "Uncategorized"
    description: str = ""
    source: str = ""
    source_path: str = ""
    search_text: str = ""
    design_url: str = ""
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)
    source_mode: str = ""


def fetch_text(url: str, timeout: int = 20) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json, text/plain;q=0.9, */*;q=0.1",
            "User-Agent": "vj-design-md-matcher",
        },
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def tokenize(text: str) -> set[str]:
    latin = re.findall(r"[a-z0-9][a-z0-9.+#_-]{1,}", text.lower())
    chinese = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    return set(latin + chinese)


def normalize_slug_from_url(url: str) -> str | None:
    match = re.search(r"getdesign\.md/([^)\s]+?)/design-md", url)
    if match:
        return match.group(1).strip("/")
    return None


def parse_readme_collection(readme: str) -> dict[str, Candidate]:
    candidates: dict[str, Candidate] = {}
    category = "Uncategorized"
    line_re = re.compile(r"^-\s+\[\*\*(?P<name>.+?)\*\*\]\((?P<url>.+?)\)\s+-\s+(?P<desc>.+)$")

    for raw_line in readme.splitlines():
        line = raw_line.strip()
        if line.startswith("### "):
            category = line[4:].strip()
            continue
        match = line_re.match(line)
        if not match:
            continue
        slug = normalize_slug_from_url(match.group("url"))
        if not slug:
            continue
        candidates[slug] = Candidate(
            name=match.group("name").strip(),
            slug=slug,
            category=category,
            description=match.group("desc").strip(),
            source=match.group("url").strip(),
        )
    return candidates


def parse_vibeui_designs_js(script: str) -> tuple[dict[str, object], list[dict[str, object]]]:
    meta_match = re.search(r"window\.SITE_META\s*=\s*(\{.*?\});", script, re.DOTALL)
    designs_match = re.search(r"window\.DESIGNS\s*=\s*(\[.*\]);\s*$", script, re.DOTALL)
    if not meta_match or not designs_match:
        raise ValueError("Could not parse vibeui designs.js")
    meta = json.loads(meta_match.group(1))
    designs = json.loads(designs_match.group(1))
    return meta, designs


def vibeui_candidate(entry: dict[str, object], cache_root: Path | None = None) -> Candidate:
    slug = str(entry.get("slug") or "")
    name = str(entry.get("name") or slug.replace("-", " ").title())
    source_site = entry.get("sourceSite") or {}
    files = entry.get("files") or {}
    if not isinstance(source_site, dict):
        source_site = {}
    if not isinstance(files, dict):
        files = {}
    source_path = str(files.get("design") or "")
    category = str(entry.get("categoryLabelEn") or entry.get("categoryLabelZh") or entry.get("categoryKey") or "Uncategorized")
    source = str(source_site.get("url") or "")
    search_terms = entry.get("searchTerms") or []
    if not isinstance(search_terms, list):
        search_terms = []
    overview = entry.get("overview") or []
    if not isinstance(overview, list):
        overview = []
    key_characteristics = entry.get("keyCharacteristics") or []
    if not isinstance(key_characteristics, list):
        key_characteristics = []
    design_url = urljoin(VIBEUI_BASE_URL, source_path) if source_path else ""
    source_mode = "remote"
    if cache_root is not None:
        design_url = str(cache_root / "entries" / slug / "DESIGN.md")
        source_mode = "local"
    return Candidate(
        name=name,
        slug=slug,
        category=category,
        description=str(entry.get("summary") or ""),
        source=source,
        source_path=source_path,
        search_text=" ".join(str(item) for item in [*overview, *key_characteristics, *search_terms]),
        design_url=design_url,
        source_mode=source_mode,
    )


def local_design_dir(local_path: Path) -> Path:
    if (local_path / "DESIGN.md").exists():
        raise SystemExit("--local must point to a repo root or design-md directory, not one entry")
    if (local_path / "design-md").is_dir():
        return local_path / "design-md"
    return local_path


def list_local_slugs(local_path: Path) -> list[str]:
    design_dir = local_design_dir(local_path)
    if not design_dir.is_dir():
        raise SystemExit(f"Local design-md directory not found: {design_dir}")
    return sorted(path.name for path in design_dir.iterdir() if (path / "DESIGN.md").is_file())


def read_local_design(local_path: Path, slug: str) -> str:
    return (local_design_dir(local_path) / slug / "DESIGN.md").read_text(encoding="utf-8", errors="replace")


def read_local_readme(local_path: Path) -> str:
    root = local_path
    if root.name == "design-md":
        root = root.parent
    readme = root / "README.md"
    if readme.exists():
        return readme.read_text(encoding="utf-8", errors="replace")
    return ""


def read_local_catalog(local_path: Path) -> tuple[dict[str, object], list[dict[str, object]]] | None:
    catalog = local_path / "catalog.json"
    if not catalog.exists():
        return None
    data = json.loads(catalog.read_text(encoding="utf-8"))
    return data.get("meta", {}), data.get("designs", [])


def local_cache_available(cache_path: Path) -> bool:
    catalog = read_local_catalog(cache_path)
    if catalog:
        _meta, designs = catalog
        return any((cache_path / "entries" / str(entry.get("slug")) / "DESIGN.md").exists() for entry in designs)
    try:
        return bool(list_local_slugs(cache_path))
    except SystemExit:
        return False


def cache_path_for_args(args: argparse.Namespace) -> Path:
    return Path(args.cache).expanduser() if args.cache else DEFAULT_CACHE


def list_remote_slugs(repo: str, ref: str) -> list[str]:
    raw = fetch_text(CONTENTS_URL.format(repo=repo, ref=ref))
    data = json.loads(raw)
    return sorted(item["name"] for item in data if item.get("type") == "dir")


def read_remote_design(repo: str, ref: str, slug: str) -> str:
    return fetch_text(RAW_DESIGN_URL.format(repo=repo, ref=ref, slug=slug))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def download_cache(args: argparse.Namespace) -> int:
    cache_root = cache_path_for_args(args)
    tmp_root = cache_root.with_name(cache_root.name + ".tmp")

    if tmp_root.exists():
        shutil.rmtree(str(tmp_root))
    (tmp_root / "entries").mkdir(parents=True, exist_ok=True)

    designs_js = fetch_text(VIBEUI_DESIGNS_URL)
    meta, designs = parse_vibeui_designs_js(designs_js)
    write_text(tmp_root / "site-assets" / "designs.js", designs_js)
    write_text(tmp_root / "catalog.json", json.dumps({"meta": meta, "designs": designs}, ensure_ascii=False, indent=2) + "\n")
    slugs = [str(entry.get("slug")) for entry in designs]

    failures: list[dict[str, str]] = []
    for index, entry in enumerate(designs, start=1):
        slug = str(entry.get("slug") or f"entry-{index}")
        files = entry.get("files") or {}
        if not isinstance(files, dict):
            files = {}
        design_path = str(files.get("design") or "")
        if not design_path:
            failures.append({"slug": slug, "error": "missing files.design"})
            print(f"[{index}/{len(designs)}] failed {slug}: missing files.design", file=sys.stderr)
            continue
        try:
            doc = fetch_text(urljoin(VIBEUI_BASE_URL, design_path))
            write_text(tmp_root / "entries" / slug / "DESIGN.md", doc)
            print(f"[{index}/{len(slugs)}] cached {slug}")
        except (urllib.error.URLError, urllib.error.HTTPError) as exc:
            failures.append({"slug": slug, "error": str(exc)})
            print(f"[{index}/{len(slugs)}] failed {slug}: {exc}", file=sys.stderr)

    manifest = {
        "source": "vibeui",
        "sourceUrl": VIBEUI_DESIGNS_URL,
        "generatedAt": meta.get("generatedAt"),
        "count": len(slugs),
        "cached": len(slugs) - len(failures),
        "failures": failures,
        "slugs": slugs,
        "categoryCounts": meta.get("categoryCounts", {}),
    }
    write_text(tmp_root / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

    if cache_root.exists():
        shutil.rmtree(str(cache_root))
    tmp_root.rename(cache_root)

    print(f"\nCached {manifest['cached']}/{len(slugs)} DESIGN.md files at {cache_root / 'entries'}")
    if failures:
        print(f"Failures recorded in {cache_root / 'manifest.json'}", file=sys.stderr)
        return 1
    return 0


def load_prd_text(args: argparse.Namespace) -> str:
    parts: list[str] = []
    if args.prd:
        path = Path(args.prd)
        if not path.exists():
            raise SystemExit(f"PRD file not found: {path}")
        parts.append(path.read_text(encoding="utf-8", errors="replace"))
    if args.query:
        parts.append(args.query)
    if not parts:
        default_prd = Path("docs/project/requirements.md")
        if default_prd.exists():
            parts.append(default_prd.read_text(encoding="utf-8", errors="replace"))
    if not parts:
        raise SystemExit("Provide --prd, --query, or create docs/project/requirements.md")
    return "\n\n".join(parts)


def infer_signals(query: str) -> dict[str, float]:
    text = query.lower()
    signals = {
        "admin": 0.0,
        "content": 0.0,
        "technical": 0.0,
        "finance": 0.0,
        "consumer": 0.0,
        "creative": 0.0,
        "marketing": 0.0,
        "analytics": 0.0,
        "style": 0.0,
    }
    keyword_groups = {
        "admin": [
            "admin",
            "dashboard",
            "console",
            "management",
            "workflow",
            "approval",
            "review",
            "table",
            "filter",
            "exam",
            "grading",
            "employee",
            "管理",
            "后台",
            "审核",
            "考试",
            "阅卷",
            "员工",
            "表格",
            "筛选",
        ],
        "content": ["docs", "document", "knowledge", "editor", "cms", "content", "training", "课程", "知识", "文档", "编辑", "素材"],
        "technical": ["api", "developer", "code", "database", "infra", "devops", "monitoring", "llm", "agent", "开发", "接口", "模型"],
        "finance": ["payment", "bank", "trading", "finance", "crypto", "billing", "invoice", "支付", "金融", "账单"],
        "consumer": ["retail", "shopping", "marketplace", "travel", "music", "social", "consumer", "电商", "零售", "消费"],
        "creative": ["design", "canvas", "creative", "collaboration", "prototype", "media", "设计", "画布", "创意", "协作"],
        "marketing": ["landing", "brand", "campaign", "hero", "marketing", "官网", "品牌", "营销", "首页"],
        "analytics": ["analytics", "dashboard", "heatmap", "heat map", "drill", "monitoring", "kpi", "metrics", "chart", "bi", "仪表盘", "分析", "指标", "监控", "热图"],
        "style": ["style", "template", "visual", "aesthetic", "ui style", "风格", "模板", "视觉"],
    }
    for signal, keywords in keyword_groups.items():
        signals[signal] = sum(1 for keyword in keywords if keyword in text)
    return signals


def score_candidate(candidate: Candidate, doc: str, query: str, query_tokens: set[str], signals: dict[str, float]) -> Candidate:
    haystack = " ".join([candidate.name, candidate.slug, candidate.category, candidate.description, candidate.search_text, doc[:6000]]).lower()
    hay_tokens = tokenize(haystack)
    overlap = len(query_tokens & hay_tokens)

    score = overlap * 1.6
    reasons: list[str] = []
    if overlap:
        reasons.append(f"keyword overlap {overlap}")

    category = candidate.category.lower()
    slug = candidate.slug.lower()

    if signals["admin"]:
        if any(term in category for term in ["productivity", "saas", "developer", "backend", "design"]):
            score += 6
            reasons.append("admin/SaaS category fit")
        if slug in {"linear.app", "airtable", "notion", "intercom", "sentry", "clickhouse", "figma", "mintlify", "slack"}:
            score += 5
            reasons.append("strong admin workflow precedent")
        if slug in {"linear.app", "airtable", "sentry", "clickhouse"}:
            score += 3
            reasons.append("high-density operational UI precedent")
        if any(term in category for term in ["automotive", "media", "consumer", "e-commerce"]):
            score -= 3
            reasons.append("less suited to operational UI")

    if signals["content"]:
        if slug in {"notion", "mintlify", "airtable", "sanity"}:
            score += 5
            reasons.append("content/knowledge fit")
        if any(term in category for term in ["productivity", "design", "backend"]):
            score += 2

    if signals["technical"]:
        if any(term in category for term in ["developer", "backend", "ai"]):
            score += 5
            reasons.append("technical product fit")
        if slug in {"linear.app", "sentry", "clickhouse", "supabase", "vercel", "cursor", "mintlify"}:
            score += 3

    if signals["finance"]:
        if any(term in category for term in ["fintech", "crypto"]):
            score += 7
            reasons.append("finance category fit")

    if signals["consumer"]:
        if any(term in category for term in ["e-commerce", "media", "consumer"]):
            score += 5
            reasons.append("consumer category fit")

    if signals["creative"]:
        if any(term in category for term in ["design", "creative"]):
            score += 5
            reasons.append("creative workflow fit")

    if signals["marketing"]:
        if any(term in category for term in ["landing", "template"]):
            score += 9
            reasons.append("landing template fit")
        if any(term in haystack for term in ["marketing", "hero", "editorial", "cinematic", "photography"]):
            score += 4
            reasons.append("marketing surface fit")

    if signals["analytics"]:
        if any(term in category for term in ["analytics", "dashboard"]):
            score += 10
            reasons.append("analytics template fit")
        if any(term in haystack for term in ["dashboard", "analytics", "heatmap", "kpi", "metrics", "monitoring", "drill-down"]):
            score += 5
            reasons.append("analytics keyword fit")

    if signals["style"]:
        if slug.startswith("uiuxpro-") or "template" in category:
            score += 6
            reasons.append("style template fit")

    if re.search(r"\b(table|dashboard|filter|status|review|workflow|admin)\b", haystack):
        score += 2
    if re.search(r"(表格|筛选|状态|审核|后台|管理)", haystack):
        score += 2

    candidate.score = round(score, 2)
    candidate.reasons = reasons[:6] or ["metadata similarity"]
    return candidate


def ensure_candidates_have_urls(candidates: Iterable[Candidate], repo: str, ref: str) -> None:
    for candidate in candidates:
        if not candidate.design_url:
            candidate.design_url = RAW_DESIGN_URL.format(repo=repo, ref=ref, slug=candidate.slug)
        if not candidate.source:
            candidate.source = HTML_DESIGN_URL.format(repo=repo, ref=ref, slug=candidate.slug)


def load_local_index(local: Path) -> tuple[dict[str, Candidate], list[str]]:
    catalog = read_local_catalog(local)
    if catalog:
        _meta, designs = catalog
        candidates: dict[str, Candidate] = {}
        slugs: list[str] = []
        for entry in designs:
            slug = str(entry.get("slug") or "")
            if not slug:
                continue
            if not (local / "entries" / slug / "DESIGN.md").exists():
                continue
            candidates[slug] = vibeui_candidate(entry, cache_root=local)
            slugs.append(slug)
        return candidates, sorted(slugs)

    readme = read_local_readme(local)
    candidates = parse_readme_collection(readme) if readme else {}
    slugs = list_local_slugs(local)
    for slug in slugs:
        candidates.setdefault(slug, Candidate(name=slug.replace("-", " ").title(), slug=slug))
    for candidate in candidates.values():
        candidate.design_url = str(local_design_dir(local) / candidate.slug / "DESIGN.md")
        candidate.source = candidate.design_url
        candidate.source_mode = "local"
    return candidates, slugs


def load_remote_index(args: argparse.Namespace) -> tuple[dict[str, Candidate], list[str]]:
    if args.source == "vibeui":
        designs_js = fetch_text(VIBEUI_DESIGNS_URL)
        _meta, designs = parse_vibeui_designs_js(designs_js)
        candidates: dict[str, Candidate] = {}
        slugs: list[str] = []
        for entry in designs:
            candidate = vibeui_candidate(entry)
            if not candidate.slug:
                continue
            candidates[candidate.slug] = candidate
            slugs.append(candidate.slug)
        return candidates, sorted(slugs)

    readme = fetch_text(README_URL.format(repo=args.repo, ref=args.ref))
    candidates = parse_readme_collection(readme)
    slugs = list_remote_slugs(args.repo, args.ref)
    for slug in slugs:
        candidates.setdefault(slug, Candidate(name=slug.replace("-", " ").title(), slug=slug))
    ensure_candidates_have_urls(candidates.values(), args.repo, args.ref)
    for candidate in candidates.values():
        candidate.source_mode = "remote"
    return candidates, slugs


def load_index(args: argparse.Namespace) -> tuple[dict[str, Candidate], list[str], Path | None, bool]:
    local: Path | None = Path(args.local).expanduser() if args.local else None
    if not local and not args.no_cache:
        cache = cache_path_for_args(args)
        if local_cache_available(cache):
            local = cache

    if local:
        try:
            candidates, slugs = load_local_index(local)
            return candidates, slugs, local, not args.offline
        except SystemExit:
            if args.offline:
                raise

    if args.offline:
        cache = local or cache_path_for_args(args)
        raise SystemExit(f"Offline mode requested, but local cache is not available: {cache}")

    candidates, slugs = load_remote_index(args)
    return candidates, slugs, None, True


def merge_remote_missing(args: argparse.Namespace, candidates: dict[str, Candidate], slugs: list[str]) -> tuple[dict[str, Candidate], list[str]]:
    if args.offline:
        return candidates, slugs
    try:
        remote_candidates, remote_slugs = load_remote_index(args)
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
        return candidates, slugs

    merged = dict(candidates)
    for slug in remote_slugs:
        if slug not in merged:
            merged[slug] = remote_candidates[slug]
    return merged, sorted(set(slugs) | set(remote_slugs))


def load_remote_candidate(args: argparse.Namespace, slug: str) -> Candidate:
    if args.source == "vibeui":
        try:
            designs_js = fetch_text(VIBEUI_DESIGNS_URL)
            _meta, designs = parse_vibeui_designs_js(designs_js)
            for entry in designs:
                if str(entry.get("slug") or "") == slug:
                    return vibeui_candidate(entry)
        except (ValueError, urllib.error.URLError, urllib.error.HTTPError):
            pass

    try:
        readme = fetch_text(README_URL.format(repo=args.repo, ref=args.ref))
        candidates = parse_readme_collection(readme)
    except (urllib.error.URLError, urllib.error.HTTPError):
        candidates = {}
    candidate = candidates.get(slug) or Candidate(name=slug.replace("-", " ").title(), slug=slug)
    ensure_candidates_have_urls([candidate], args.repo, args.ref)
    candidate.source_mode = "remote"
    return candidate


def read_design_doc(args: argparse.Namespace, candidate: Candidate, local: Path | None, allow_remote: bool) -> str:
    if candidate.source_mode == "local" and local:
        try:
            local_design = Path(candidate.design_url)
            if local_design.exists():
                return local_design.read_text(encoding="utf-8", errors="replace")
            return read_local_design(local, candidate.slug)
        except OSError:
            if not allow_remote:
                raise
            remote_candidate = load_remote_candidate(args, candidate.slug)
            candidate.design_url = remote_candidate.design_url
            candidate.source = remote_candidate.source
            candidate.source_mode = "remote-fallback"
    if not allow_remote:
        raise OSError(f"Missing local DESIGN.md for {candidate.slug}")
    if candidate.source_path:
        return fetch_text(urljoin(VIBEUI_BASE_URL, candidate.source_path))
    return read_remote_design(args.repo, args.ref, candidate.slug)


def rank(args: argparse.Namespace) -> list[Candidate]:
    query = load_prd_text(args)
    query_tokens = tokenize(query)
    signals = infer_signals(query)
    candidates, slugs, local, allow_remote = load_index(args)
    if local and allow_remote:
        candidates, slugs = merge_remote_missing(args, candidates, slugs)

    prelim: list[Candidate] = []
    for slug in slugs:
        candidate = candidates[slug]
        metadata = " ".join([candidate.name, candidate.slug, candidate.category, candidate.description])
        prelim.append(score_candidate(candidate, metadata, query, query_tokens, signals))
    prelim.sort(key=lambda item: item.score, reverse=True)

    enriched: list[Candidate] = []
    for candidate in prelim[: args.max_docs]:
        try:
            doc = read_design_doc(args, candidate, local, allow_remote)
        except (OSError, urllib.error.URLError, urllib.error.HTTPError) as exc:
            candidate.reasons.append(f"DESIGN.md fetch failed: {exc}")
            doc = ""
        enriched.append(score_candidate(candidate, doc, query, query_tokens, signals))

    untouched = [candidate for candidate in prelim[args.max_docs :] if candidate.slug not in {item.slug for item in enriched}]
    ranked = enriched + untouched
    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked[: args.limit]


def print_markdown(candidates: list[Candidate]) -> None:
    print("## DESIGN.md Candidate Matches\n")
    for index, candidate in enumerate(candidates, start=1):
        print(f"{index}. **{candidate.name}** (`{candidate.slug}`) - score {candidate.score}")
        print(f"   - Category: {candidate.category}")
        if candidate.description:
            print(f"   - Description: {candidate.description}")
        print(f"   - Reasons: {', '.join(candidate.reasons)}")
        if candidate.source_mode:
            print(f"   - Source mode: {candidate.source_mode}")
        print(f"   - DESIGN.md: {candidate.design_url}")
        print(f"   - Catalog: {candidate.source}")
        print()


def candidate_output(candidate: Candidate) -> dict[str, object]:
    data = asdict(candidate)
    data.pop("search_text", None)
    return data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prd", help="Path to a PRD or product brief")
    parser.add_argument("--query", help="Inline product description or matching query")
    parser.add_argument("--local", help="Local awesome-design-md repo root or design-md directory")
    parser.add_argument("--cache", help=f"Cache directory, default {DEFAULT_CACHE}")
    parser.add_argument("--download-cache", action="store_true", help="Download vibeui catalog metadata and every DESIGN.md into the cache, then exit")
    parser.add_argument("--no-cache", action="store_true", help="Do not use the bundled cache automatically")
    parser.add_argument("--offline", action="store_true", help="Use local/cache only; fail instead of falling back to network")
    parser.add_argument("--source", choices=["vibeui", "github"], default="vibeui", help="Network matching source, default vibeui; cache download uses vibeui")
    parser.add_argument("--repo", default=DEFAULT_REPO, help=f"GitHub repo, default {DEFAULT_REPO}")
    parser.add_argument("--ref", default=DEFAULT_REF, help=f"Git ref, default {DEFAULT_REF}")
    parser.add_argument("--limit", type=int, default=8, help="Number of candidates to output")
    parser.add_argument("--max-docs", type=int, default=30, help="How many top metadata candidates to enrich by reading DESIGN.md")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of Markdown")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.download_cache:
        try:
            return download_cache(args)
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
            print(f"vj-design-md-matcher cache download failed: {exc}", file=sys.stderr)
            return 1

    try:
        candidates = rank(args)
    except (SystemExit, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
        print(f"vj-design-md-matcher failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps([candidate_output(candidate) for candidate in candidates], ensure_ascii=False, indent=2))
    else:
        print_markdown(candidates)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
