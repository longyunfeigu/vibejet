#!/usr/bin/env python3
"""vj-mock-board P4 机检：mock board HTML 的确定性约束校验。

检查项（对应 SKILL.md 铁律）：
  1. anchors        — screen-inventory.md 锚点列的每个 id 在板内存在且唯一
  2. colors         — 裸色值只允许出现在 :root 块内，且值 ∈ DESIGN.md 色值集合；
                      正文只允许 var(--token)。rgba() 为阴影/遮罩白名单（设计决策，
                      见 spec 2026-07-08），rgb()/hsl() 一律禁止。
                      --wireframe 模式：跳过 DESIGN.md 比对，:root 只允许灰阶。
  3. self-contained — 无 http(s):// 资源引用、无 @import（data: URI 允许）
  4. notes          — 每屏（无 -- 后缀的默认态锚点）的卡内有 .note 注记框

用法：
  validate_mock_board.py <board.html> --inventory <screen-inventory.md> \
      [--design <DESIGN.md>] [--wireframe]

exit code: 0 全过 / 1 有违规 / 2 输入或解析错误
"""

from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b")
ROOT_BLOCK_RE = re.compile(r":root\s*\{[^}]*\}")
VOID_TAGS = frozenset(
    "area base br col embed hr img input link meta param source track wbr".split()
)


def norm_hex(h: str) -> str:
    h = h.lower().lstrip("#")
    if len(h) in (3, 4):
        h = "".join(c * 2 for c in h)
    return "#" + h[:6]  # 忽略 alpha 位，色相一致即视为同源


def is_grayscale(h: str) -> bool:
    h = norm_hex(h)[1:]
    return h[0:2] == h[2:4] == h[4:6]


def line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


class Node:
    __slots__ = ("tag", "id", "classes", "children")

    def __init__(self, tag: str, attrs: list) -> None:
        d = dict(attrs)
        self.tag = tag
        self.id = d.get("id")
        self.classes = set((d.get("class") or "").split())
        self.children: list[Node] = []


class TreeBuilder(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.root = Node("#root", [])
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list) -> None:
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list) -> None:
        self.stack[-1].children.append(Node(tag, attrs))

    def handle_endtag(self, tag: str) -> None:
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break


def iter_nodes(node: Node):
    yield node
    for child in node.children:
        yield from iter_nodes(child)


def find_by_id(root: Node, node_id: str) -> Node | None:
    return next((n for n in iter_nodes(root) if n.id == node_id), None)


def parse_inventory_anchors(inv_text: str) -> list[str]:
    """解析 markdown 表：定位含「锚点」的表头列，收集逗号分隔的 id。"""
    anchors: list[str] = []
    col = None
    in_table = False
    for raw in inv_text.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            if in_table:
                break  # 首张锚点表结束即停，后续表格不解析
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if col is None:
            if any("锚点" in c for c in cells):
                col = next(i for i, c in enumerate(cells) if "锚点" in c)
            continue
        in_table = True
        if set(line) <= {"|", "-", " ", ":"}:
            continue
        if col < len(cells) and cells[col]:
            anchors.extend(a.strip() for a in cells[col].split(",") if a.strip())
    return anchors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("board")
    ap.add_argument("--inventory", required=True)
    ap.add_argument("--design")
    ap.add_argument("--wireframe", action="store_true")
    args = ap.parse_args()

    try:
        html = Path(args.board).read_text(encoding="utf-8")
        inv_text = Path(args.inventory).read_text(encoding="utf-8")
    except OSError as e:
        print(f"ERROR 读取输入失败: {e}")
        return 2

    anchors = parse_inventory_anchors(inv_text)
    if not anchors:
        print(f"ERROR inventory 无锚点列或为空: {args.inventory}")
        return 2
    dupes = {a for a in anchors if anchors.count(a) > 1}
    if dupes:
        print(f"ERROR inventory 锚点重复: {sorted(dupes)}")
        return 2

    design_hexes: set[str] = set()
    if not args.wireframe:
        if not args.design:
            print("ERROR 非 --wireframe 模式必须提供 --design DESIGN.md 路径")
            return 2
        try:
            design_text = Path(args.design).read_text(encoding="utf-8")
        except OSError as e:
            print(f"ERROR 读取 DESIGN.md 失败: {e}")
            return 2
        design_hexes = {norm_hex(m.group(0)) for m in HEX_RE.finditer(design_text)}
        if not design_hexes:
            print(f"ERROR DESIGN.md 未解析到任何色值: {args.design}")
            return 2

    fails: list[str] = []

    # --- 1. anchors ---
    parser = TreeBuilder()
    parser.feed(html)
    seen_ids = [n.id for n in iter_nodes(parser.root) if n.id]
    dup_dom = {i for i in seen_ids if seen_ids.count(i) > 1}
    for d in sorted(dup_dom):
        fails.append(f"[anchors] 板内 id 重复: #{d}")
    missing = [a for a in anchors if a not in seen_ids]
    for a in missing:
        fails.append(f"[anchors] inventory 锚点在板内缺失: #{a}")

    # --- 2. colors ---
    # 锚点 href="#..."、svg url(#...) 不是颜色；HTML 注释（视觉系统声明可能引用色值）
    # 不参与渲染——三者先打掩码再扫 hex。掩码保留换行以维持行号。
    masked = re.sub(r'href="#[^"]*"', 'href=""', html)
    masked = re.sub(r"url\(#[^)]*\)", "url()", masked)
    masked = re.sub(
        r"<!--.*?-->", lambda m: re.sub(r"[^\n]", " ", m.group(0)), masked, flags=re.S
    )
    root_spans = [m.span() for m in ROOT_BLOCK_RE.finditer(masked)]
    if not root_spans and not args.wireframe:
        fails.append("[colors] 板内未找到 :root token 块")
    for m in HEX_RE.finditer(masked):
        in_root = any(s <= m.start() < e for s, e in root_spans)
        h, ln = m.group(0), line_of(masked, m.start())
        if not in_root:
            fails.append(f"[colors] L{ln} 正文裸色值 {h}（只允许 var(--token)）")
        elif args.wireframe:
            if not is_grayscale(h):
                fails.append(f"[colors] L{ln} wireframe 模式 :root 出现非灰阶 {h}")
        elif norm_hex(h) not in design_hexes:
            fails.append(f"[colors] L{ln} :root 色值 {h} 不在 DESIGN.md 色值集合中")
    for pat, label in ((r"\brgb\(", "rgb()"), (r"\bhsla?\(", "hsl()/hsla()")):
        for m in re.finditer(pat, masked):
            fails.append(f"[colors] L{line_of(masked, m.start())} 禁止 {label}（rgba 阴影除外）")

    # --- 3. self-contained ---
    for m in re.finditer(r"https?://", html):
        ln = line_of(html, m.start())
        ctx = html[m.start() : m.start() + 60].splitlines()[0]
        fails.append(f"[self-contained] L{ln} 外部引用: {ctx}")
    for m in re.finditer(r"@import\b", html):
        fails.append(f"[self-contained] L{line_of(html, m.start())} 禁止 @import")

    # --- 4. notes ---
    for a in anchors:
        if "--" in a or a in missing:
            continue  # 状态变体卡不要求 note；缺失锚点已在检查 1 报过
        card = find_by_id(parser.root, a)
        if card and not any("note" in n.classes for n in iter_nodes(card)):
            fails.append(f"[notes] #{a} 默认态卡内缺注记框 .note")

    if fails:
        print(f"FAIL {len(fails)} 项违规：")
        for f in fails:
            print(f"  {f}")
        return 1
    print(f"OK 机检通过：{len(anchors)} 个锚点 / colors / self-contained / notes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
