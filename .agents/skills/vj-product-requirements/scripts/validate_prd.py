#!/usr/bin/env python3
# input: vj-product-requirements 产出的 PRD markdown（默认 docs/product/requirements.md）路径参数
# output: PRD 结构机检报告（stdout）+ exit code（0=全过，1=有 ERROR）
# pos: vj-product-requirements skill 校验脚本 - 第 6 步质量门机械检查的真相源（rubric 不复述规则清单）；
#      一旦我被更新，务必更新我的开头注释以及所属文件夹的 README.md
"""Validate PRD markdown against vj-product-requirements hard rules.

机检规则（机械检查的唯一真相源；语义检查在 quality_rubric.md）：
  P1  头部元数据齐全：工作模式 / 项目阶段 / 范围模式 / 调研模式
  P2  章节完整性：§1/§1.2/§3/§4/§5/§6/§7/§9/§10/§11/§12 必须存在；
      调研模式 light|deep 时 §2 必须存在（下游按节号消费，节号不可漂移）
  P3  §12 行为合同至少解析出 1 条 EARS 块（ERROR）；块合法：类型 ∈ When|If|While|Where|Ubiquitous|Scenario；
      块内含响应词"应"；块内含 ≥1 来源标注 [用户]/[调研]/[推断]/[未验证假设]。块在空行、表格行或非缩进的
      非列表行处结束（§12 后面的 eval 例子表不会被算进最后一条 R）；形似 R 编号却不符合格式的行 = WARNING
  P4  §12 的 R 编号唯一（重复=ERROR；跳号=WARNING）
  P5  占位符扫描：[填写] / <待定> / 句尾"未定" / 原样残留的模板占位（与 assets/requirements_template.md
      里的方括号描述一致）= ERROR；TBD / TODO 可能是正文 = WARNING。
      §8 与 §10 表格行里的"未定"是合法结论，不算占位
  P6  §1.2 mermaid 用户旅程不得保留方括号模板占位节点（如 ["[进入入口]"]）
  P7  文中存在 [推断] 时，§8 必须存在且表格含 ≥1 数据行
  P8  §3 为谁做与 §9 非目标各含 ≥1 条目
  P9  启发式（WARNING）：(If) 块含"期间"疑似状态冒充；(While) 块不含"期间"疑似写法不符；
      §4 / §12 出现 友好/智能/易用 等无度量模糊词
  P10 §4 能力行（**C<n>**）必须带来源标注（ERROR）；§4 出现 EARS 块（WARNING，应挪到 §12）
  P11 WARNING：§12 超过 12 条（行为合同只写高风险行为）；头部缺 **原型** 链接或链接文件不存在；
      §5 缺"为什么选我们"，或去掉来源标注后为空 / 仍是模板占位
  P12 WARNING：必需章节的标题与模板章节名不符（节号对了但内容可能是旧结构）
  P13 WARNING：人读部分像清单——§1（不含 §1.1/§1.2）、§3、§5 里列表文字的字数多于成段叙述的字数

Usage:
    python3 validate_prd.py <requirements.md> [more files...]

Exit codes:
    0 — 无 ERROR（WARNING 不阻塞）
    1 — 存在 ERROR，不得进入评分，不得放行 vj-architecture
    2 — 用法或文件读取错误
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

REQ_START = re.compile(r"^[*-]\s{1,3}\*\*(R\d+)\s*\(([^)]+)\)\*\*")
CAP_LINE = re.compile(r"^[*-]\s{1,3}\*\*(C\d+)\*\*")
H2 = re.compile(r"^##\s+(\d+)\.")
H15 = re.compile(r"^###\s+1\.2\.")
META_FIELDS = ("工作模式", "项目阶段", "范围模式", "调研模式")
RESEARCH_MODE = re.compile(r"^\*\*调研模式\*\*[:：]\s*([A-Za-z]+)")
PROTOTYPE_META = re.compile(r"^\*\*原型\*\*[:：].*?\]\(([^)\s]+)\)")
WHY_US = re.compile(r"为什么选我们\*{0,2}\s*(?:`?\[[^\]]+\]`?\s*)*[:：]\s*(.*)$")
SRC_INLINE = re.compile(r"`?\[(?:用户|调研|推断|未验证假设)\]`?")
R_LIKE = re.compile(r"^[*-]\s{1,3}\*\*R\d+")
TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "assets" / "requirements_template.md"
TEMPLATE_PH = re.compile(r"\[([^\[\]\n]*[\u4e00-\u9fff][^\[\]\n]*)\](?!\()")
SRC_LABEL = re.compile(r"\[(用户|调研|推断|未验证假设)\]")
VALID_TYPES = {"When", "If", "While", "Where", "Ubiquitous", "Scenario"}
MAX_CONTRACT = 12
# P5 分两档：无歧义占位符 = ERROR；TBD/TODO 可能是正文内容（如"TODO 列表"产品）= WARNING
UNDECIDED = re.compile(r"未定(?=[\s。；，、|）)】\]]|$)")  # 放过"未定义/未定期/未定向"等合法词
PLACEHOLDER_ERROR_RES = (re.compile(r"\[填写\]"), re.compile(r"<待定>"), UNDECIDED)
PLACEHOLDER_WARN_RES = (
    re.compile(r"(?<![\w/])TBD(?![\w/-])"),
    re.compile(r"(?<![\w/])TODO(?![\w/-])"),
)
VAGUE = re.compile(r"(友好|智能|易用)")
BULLET = re.compile(r"^[*-]\s+\S")
REQUIRED_SECTIONS = {1: "一句话与问题", 3: "为谁做", 4: "能力与场景", 5: "押注、留存与原则",
                     6: "约束与依赖", 7: "原型与验证", 9: "非目标", 10: "Architecture Handoff",
                     11: "Epic Decomposition Notes", 12: "行为合同"}


@dataclass
class Finding:
    level: str  # ERROR | WARNING
    rule: str
    where: str
    message: str


def section_ranges(lines: list[str]) -> dict[int, tuple[int, int]]:
    """按 `## N.` 标题切出各节的 [start, end) 行号区间。"""
    starts: list[tuple[int, int]] = []  # (section_no, line_idx)
    for i, line in enumerate(lines):
        m = H2.match(line)
        if m:
            starts.append((int(m.group(1)), i))
    ranges: dict[int, tuple[int, int]] = {}
    for idx, (no, start) in enumerate(starts):
        end = starts[idx + 1][1] if idx + 1 < len(starts) else len(lines)
        ranges[no] = (start, end)
    return ranges


def ears_blocks(lines: list[str], start: int, end: int) -> list[tuple[str, str, int, list[str]]]:
    """切出 [start, end) 内的 EARS 需求块：(rid, rtype, 行号, 块内各行)。"""
    blocks: list[tuple[str, str, int, list[str]]] = []
    current: tuple[str, str, int, list[str]] | None = None
    for i in range(start, end):
        line = lines[i]
        rm = REQ_START.match(line)
        ends = (
            not line.strip()
            or line.lstrip().startswith("|")
            or (not line[:1].isspace() and not line.startswith(("*", "-")))
        )
        if rm or line.startswith("#") or ends:
            if current:
                blocks.append(current)
                current = None
        if rm:
            rtype = re.split(r"[:：]", rm.group(2))[0].strip()
            current = (rm.group(1), rtype, i + 1, [line])
        elif current:
            current[3].append(line)
    if current:
        blocks.append(current)
    return blocks


def template_placeholders() -> set[str]:
    """模板 §1-§7 里的方括号描述（如 [为谁、解决什么、靠什么不同]），出现在正式 PRD 里就是没填。"""
    try:
        text = TEMPLATE_PATH.read_text(encoding="utf-8")
    except OSError:
        return set()
    return {m.group(0) for m in TEMPLATE_PH.finditer(text) if not SRC_LABEL.fullmatch(m.group(0))}


def check(path: Path) -> list[Finding]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    findings: list[Finding] = []
    ranges = section_ranges(lines)

    # P1 头部元数据
    for field_name in META_FIELDS:
        if not any(line.startswith(f"**{field_name}**") for line in lines[:20]):
            findings.append(Finding("ERROR", "P1", "头部", f"缺少元数据字段 **{field_name}**"))
    research = "none"
    prototype_link = None
    for line in lines[:20]:
        m = RESEARCH_MODE.match(line)
        if m:
            research = m.group(1).lower()
        pm = PROTOTYPE_META.match(line)
        if pm:
            prototype_link = pm.group(1)

    # P2 章节完整性
    for no, name in REQUIRED_SECTIONS.items():
        if no not in ranges:
            findings.append(Finding("ERROR", "P2", "章节", f"缺少 §{no} {name}（下游按节号消费）"))
    if research in ("light", "deep") and 2 not in ranges:
        findings.append(Finding("ERROR", "P2", "章节", f"调研模式={research} 但缺少 §2 市场与替代方案"))
    for no, name in REQUIRED_SECTIONS.items():
        if no in ranges:
            head = lines[ranges[no][0]]
            if not any(part in head for part in name.replace("、", " ").split()):
                findings.append(Finding("WARNING", "P12", f"§{no}", f"标题与模板章节名\"{name}\"不符：{head.strip()[:40]}"))
    if not any(H15.match(line) for line in lines):
        findings.append(Finding("ERROR", "P2", "章节", "缺少 §1.2 核心用户旅程"))

    # P10 §4 能力清单：来源标注；EARS 应挪到 §12
    if 4 in ranges:
        s4_start, s4_end = ranges[4]
        for i in range(s4_start, s4_end):
            cm = CAP_LINE.match(lines[i])
            if cm and not SRC_LABEL.search(lines[i]):
                findings.append(Finding("ERROR", "P10", f"§4/{cm.group(1)}(L{i + 1})", "能力行缺少来源标注 [用户]/[调研]/[推断]"))
        if ears_blocks(lines, s4_start, s4_end):
            findings.append(Finding("WARNING", "P10", "§4", "能力清单里出现 EARS 句式，行为细节应挪到 §12 行为合同"))
        vm = VAGUE.search("\n".join(lines[s4_start:s4_end]))
        if vm:
            findings.append(Finding("WARNING", "P9", "§4", f"出现无度量模糊词\"{vm.group(1)}\"，需可测试化或删除"))

    # P3/P4/P9/P11 —— §12 行为合同
    if 12 in ranges:
        s12_start, s12_end = ranges[12]
        blocks = ears_blocks(lines, s12_start, s12_end)
        if not blocks:
            findings.append(Finding("ERROR", "P3", "§12", "行为合同里没有解析出任何 EARS 条目（格式：* **R1 (If)**： ……）"))
        for i in range(s12_start, s12_end):
            if R_LIKE.match(lines[i]) and not REQ_START.match(lines[i]):
                findings.append(Finding("WARNING", "P3", f"§12(L{i + 1})", "形似 R 编号但格式不符，未被识别：" + lines[i].strip()[:40]))
        rids: list[int] = []
        for rid, rtype, lineno, block_lines in blocks:
            where = f"§12/{rid}(L{lineno})"
            block = "\n".join(block_lines)
            rids.append(int(rid[1:]))
            if rtype not in VALID_TYPES:
                findings.append(Finding("ERROR", "P3", where, f"非法 EARS 类型 ({rtype})"))
            if "应" not in block:
                findings.append(Finding("ERROR", "P3", where, "需求块缺少响应词\"应\""))
            if not SRC_LABEL.search(block):
                findings.append(Finding("ERROR", "P3", where, "需求块缺少来源标注 [用户]/[调研]/[推断]"))
            if rtype == "If" and "期间" in block:
                findings.append(Finding("WARNING", "P9", where, "If 块含\"期间\"，疑似持续状态冒充不期望事件（应改 While）"))
            if rtype == "While" and "期间" not in block:
                findings.append(Finding("WARNING", "P9", where, "While 块不含\"期间\"，检查是否为状态驱动写法"))
        for d in sorted({r for r in rids if rids.count(r) > 1}):
            findings.append(Finding("ERROR", "P4", "§12", f"R{d} 编号重复"))
        uniq = sorted(set(rids))
        if uniq and uniq != list(range(uniq[0], uniq[0] + len(uniq))):
            findings.append(Finding("WARNING", "P4", "§12", f"R 编号跳号：{uniq}"))
        if len(blocks) > MAX_CONTRACT:
            findings.append(Finding("WARNING", "P11", "§12", f"行为合同有 {len(blocks)} 条，超过 {MAX_CONTRACT}；只保留异常、状态、环境和安全边界"))
        vm = VAGUE.search("\n".join(lines[s12_start:s12_end]))
        if vm:
            findings.append(Finding("WARNING", "P9", "§12", f"出现无度量模糊词\"{vm.group(1)}\"，需可测试化或删除"))

    # P11 原型链接与"为什么选我们"
    if prototype_link is None:
        findings.append(Finding("WARNING", "P11", "头部", "缺少 **原型** 链接；没有原型时说明原因"))
    elif not prototype_link.startswith(("http://", "https://")) and not (path.parent / prototype_link).is_file():
        findings.append(Finding("WARNING", "P11", "头部", f"原型链接指向的文件不存在：{prototype_link}"))
    if 5 in ranges:
        s5_start, s5_end = ranges[5]
        why_line = next((i for i in range(s5_start, s5_end) if "为什么选我们" in lines[i]), None)
        content = ""
        if why_line is not None and lines[why_line].startswith("#"):  # 小标题写法：取下一段正文
            nxt = next((lines[j] for j in range(why_line + 1, s5_end) if lines[j].strip()), "")
            content = "" if nxt.startswith("#") else SRC_INLINE.sub("", nxt).strip()
        elif why_line is not None and WHY_US.search(lines[why_line]):
            content = SRC_INLINE.sub("", WHY_US.search(lines[why_line]).group(1) or "").strip()
            if not content:  # 内容写成下一级子列表
                nxt = lines[why_line + 1] if why_line + 1 < s5_end else ""
                content = SRC_INLINE.sub("", nxt).strip() if nxt[:1].isspace() else ""
        if not content or content.lstrip("*- ").startswith("["):
            findings.append(Finding("WARNING", "P11", "§5", "缺少\"为什么选我们\"，或内容为空 / 仍是模板占位"))

    # P13 人读部分像清单
    def prose_vs_list(start: int, end: int) -> tuple[int, int]:
        prose = bullets = 0
        in_fence = False
        for i in range(start, end):
            t = lines[i].strip()
            if t.startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence or not t or t.startswith(("#", ">", "|", "<!--")):
                continue
            if BULLET.match(lines[i]) or re.match(r"^\s+[*-]\s", lines[i]):
                bullets += len(t)
            else:
                prose += len(t)
        return prose, bullets
    for no in (1, 3, 5):
        if no not in ranges:
            continue
        start, end = ranges[no]
        if no == 1:  # 只看 §1.1 之前的叙述部分
            end = next((i for i in range(start, end) if re.match(r"^###\s+1\.[12]\.", lines[i])), end)
        prose, bullets = prose_vs_list(start + 1, end)
        if bullets > prose:
            findings.append(Finding("WARNING", "P13", f"§{no}", f"人读部分像清单（列表 {bullets} 字、叙述 {prose} 字），请用成段的话讲因果"))

    # P5 占位符（§8 / §10 的"未定"是合法结论）
    undecided_ok: set[int] = set()
    for no in (8, 10):
        if no in ranges:
            undecided_ok.update(i for i in range(*ranges[no]) if lines[i].lstrip().startswith("|"))
    if path.resolve() != TEMPLATE_PATH:
        residue = template_placeholders()
        for i, line in enumerate(lines):
            hit = next((ph for ph in residue if ph in line), None)
            if hit:
                findings.append(Finding("ERROR", "P5", f"L{i + 1}", f"模板占位没有填：{hit}"))
    for i, line in enumerate(lines):
        for pat in PLACEHOLDER_ERROR_RES:
            if pat is UNDECIDED and i in undecided_ok:
                continue
            if pat.search(line):
                findings.append(Finding("ERROR", "P5", f"L{i + 1}", f"占位符 {pat.pattern!r}: {line.strip()[:60]}"))
        for pat in PLACEHOLDER_WARN_RES:
            if pat.search(line):
                findings.append(Finding("WARNING", "P5", f"L{i + 1}", f"疑似占位符 {pat.pattern!r}（若为正文内容可忽略）: {line.strip()[:60]}"))

    # P6 §1.2 mermaid 模板占位
    if 1 in ranges:
        in_fence = False
        for i in range(*ranges[1]):
            if lines[i].strip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence and '"[' in lines[i]:
                findings.append(Finding("ERROR", "P6", f"L{i + 1}", "§1.2 mermaid 节点保留了方括号模板占位"))

    # P7 有 [推断] 时 §8 必须存在且非空
    if "[推断]" in text:
        if 8 not in ranges:
            findings.append(Finding("ERROR", "P7", "章节", "存在 [推断] 标注但缺少 §8 待验证假设与待决事项"))
        else:
            rows = [lines[i] for i in range(*ranges[8]) if lines[i].lstrip().startswith("|")]
            if len(rows) < 3:  # 表头 + 分隔行 + ≥1 数据行
                findings.append(Finding("ERROR", "P7", "§8", "待验证假设与待决事项表没有数据行"))

    # P8 §3 / §9 至少一条
    for no, label in ((3, "为谁做"), (9, "非目标")):
        if no in ranges:
            bullets = [lines[i] for i in range(*ranges[no]) if BULLET.match(lines[i])]
            if not bullets:
                findings.append(Finding("ERROR", "P8", f"§{no}", f"{label}没有任何条目"))

    return findings


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    total_errors = 0
    total_warnings = 0
    for arg in argv[1:]:
        path = Path(arg)
        try:
            findings = check(path)
        except OSError as e:
            print(f"✗ 读取失败 {path}: {e}", file=sys.stderr)
            return 2
        for x in findings:
            mark = "✗" if x.level == "ERROR" else "⚠"
            print(f"{mark} [{x.level}][{x.rule}] {path}:{x.where} — {x.message}")
        total_errors += sum(1 for x in findings if x.level == "ERROR")
        total_warnings += sum(1 for x in findings if x.level == "WARNING")
    print(
        f"\n校验完成：{len(argv) - 1} 个文件，{total_errors} ERROR，{total_warnings} WARNING"
        + ("（存在 ERROR，不得放行 vj-architecture）" if total_errors else " ✓")
    )
    return 1 if total_errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
