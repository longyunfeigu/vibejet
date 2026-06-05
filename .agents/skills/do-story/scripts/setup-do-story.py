#!/usr/bin/env python3
"""
setup-do-story.py - 状态初始化 + 设计文档解析 + Epic 模式支持

功能:
1. 解析 Story 文件路径 + #anchor (Single Story Mode)
2. --scan: 扫描 Epic 文件中所有 Stories (Epic Mode)
3. --stories: 初始化选定的 Stories (Epic Mode)
4. 读取设计文档，提取约束
5. 创建包含设计约束的状态文件
"""
import argparse
import json
import os
import re
import secrets
import sys
import time
from typing import Optional


def parse_story_path(story_path: str) -> tuple:
    """解析 path#anchor 格式"""
    if "#" in story_path:
        path, anchor = story_path.rsplit("#", 1)
        return path, anchor
    return story_path, None


def scan_all_stories(epic_path: str) -> list:
    """扫描 Epic 文件中所有 Stories，返回 Story 列表"""
    with open(epic_path, "r", encoding="utf-8") as f:
        content = f.read()

    stories = []
    # 只匹配明确的 Story 格式:
    # ### Story 1.1: Title
    # ### Story 1.2: Title
    # ## Story 1.1: Title
    # Story 必须作为关键词存在，后面跟数字ID
    pattern = r"^#{2,3}\s+Story\s+([\d]+\.[\d]+)[:\s]+(.+?)$"

    for match in re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE):
        story_id = match.group(1)
        title = match.group(2).strip()
        stories.append(
            {
                "id": story_id,
                "title": title,
            }
        )

    return stories


def extract_epic_title(epic_path: str) -> str:
    """提取 Epic 标题"""
    with open(epic_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. 尝试从 YAML frontmatter 中提取 epic_name
    frontmatter_match = re.search(r'^epic_name:\s*["\']?([^"\']+)["\']?', content, re.MULTILINE)
    if frontmatter_match:
        return frontmatter_match.group(1).strip()

    # 2. 尝试从 # Epic X: Title 格式提取
    epic_title_match = re.search(r"^#\s+Epic\s+\d+[:\s]+(.+?)$", content, re.MULTILINE)
    if epic_title_match:
        return epic_title_match.group(1).strip()

    # 3. 尝试从第一个 # 标题提取
    title_match = re.search(r"^#\s+(.+?)$", content, re.MULTILINE)
    if title_match:
        return title_match.group(1).strip()

    # 4. 从文件名提取
    return os.path.basename(epic_path).replace(".md", "").replace("-", " ").title()


def parse_epic_source_documents(epic_path: str, project_dir: str) -> dict:
    """从 Epic YAML frontmatter 解析 source_documents 路径映射"""
    with open(epic_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 提取 YAML frontmatter
    fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not fm_match:
        return {}

    frontmatter = fm_match.group(1)
    if not frontmatter.endswith("\n"):
        frontmatter += "\n"

    # 提取 source_documents 块
    sd_match = re.search(
        r"^source_documents:\s*\n((?:\s+\w+:.*\n)*)", frontmatter, re.MULTILINE
    )
    if not sd_match:
        return {}

    # key 映射: YAML key → doc name
    key_map = {
        "ui_spec": "design_guidelines",
        "api_design": "api_spec",
        "data_model": "database_schema",
        "architecture": "architecture",
        "prd": "requirements",
    }

    result = {}
    for line in sd_match.group(1).split("\n"):
        line = line.strip()
        if not line:
            continue
        m = re.match(r'(\w+):\s*["\']?([^"\'#]+)["\']?', line)
        if m:
            yaml_key, rel_path = m.group(1), m.group(2).strip()
            doc_name = key_map.get(yaml_key, yaml_key)
            abs_path = os.path.join(project_dir, rel_path)
            if os.path.exists(abs_path):
                result[doc_name] = abs_path
            else:
                print(
                    f"Warning: source_documents.{yaml_key} not found: {abs_path}",
                    file=sys.stderr,
                )

    return result


def extract_story_content(story_path: str, anchor: Optional[str]) -> dict:
    """从 Epic 文件提取指定 Story"""
    with open(story_path, "r", encoding="utf-8") as f:
        content = f.read()

    story_content = content  # 默认使用全部内容

    # 如果有 anchor，提取对应 Story section
    if anchor:
        # 匹配 "### Story X.Y:" 格式，提取到下一个 ### Story 或文件结束
        pattern = rf"(###\s+Story\s+{re.escape(anchor)}:.+?)(?=\n###\s+Story\s+\d|\Z)"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            story_content = match.group(1).strip()

    # 提取验收标准
    ac_match = re.search(
        r"####?\s*(?:Acceptance\s*Criteria|验收标准)[^\n]*\n(.*?)(?=\n####|\Z)",
        story_content,
        re.DOTALL | re.IGNORECASE,
    )
    criteria = []
    if ac_match:
        for line in ac_match.group(1).split("\n"):
            line = line.strip()
            if line.startswith("- ") or line.startswith("* "):
                # 去掉 checkbox 前缀 [ ]
                text = line[2:].strip()
                if text.startswith("[ ] "):
                    text = text[4:]
                if text:
                    criteria.append(text)

    return {
        "story_id": anchor or "full",
        "epic_ref": os.path.basename(story_path).replace(".md", ""),
        "content": story_content,
        "acceptance_criteria": criteria,
    }


def extract_story_by_id(epic_path: str, story_id: str) -> dict:
    """根据 Story ID 提取 Story 内容"""
    return extract_story_content(epic_path, story_id)


def extract_md_section(content: str, section_number: int, keyword: str) -> str:
    """通用 markdown section 提取，支持 '## N. Title' 和 '## Title' 格式"""
    # Pattern 1: ## N. Keyword...
    pattern1 = rf"(##\s+{section_number}\.\s+{re.escape(keyword)}.*?)(?=\n##\s+\d|\Z)"
    m = re.search(pattern1, content, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # Pattern 2: ## Keyword... (without number)
    pattern2 = rf"(##\s+{re.escape(keyword)}.*?)(?=\n##\s|\Z)"
    m = re.search(pattern2, content, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return ""


def extract_ui_spec_summary(content: str, path: str, project_dir: str = None) -> str:
    """从 docs/project/design_guidelines.md 提取关键 section：§7, §1, §2, §3"""
    display_path = os.path.relpath(path, project_dir) if project_dir else path
    summary = f"[Full file: {display_path}]\n\n"

    sections = [
        (7, "Implementation Priority", 5000),
        (1, "Page Inventory", 3000),
        (2, "Component Mapping", 5000),
        (3, "Data Flow", 5000),
    ]

    for num, keyword, limit in sections:
        text = extract_md_section(content, num, keyword)
        if text:
            if len(text) > limit:
                text = text[:limit] + "\n\n... (truncated, see full file)"
            summary += text + "\n\n"

    return summary.rstrip() + "\n"


def extract_prototype_structures(proto_dir: str, project_dir: str) -> str:
    """从原型 HTML 文件提取 design tokens + 每页 body 结构，嵌入状态文件"""
    if not proto_dir or not os.path.isdir(proto_dir):
        return ""

    html_files = []
    for root, _dirs, files in os.walk(proto_dir):
        for fname in sorted(files):
            if fname.endswith(".html"):
                html_files.append(os.path.join(root, fname))

    if not html_files:
        return ""

    # 安全上限：防止原型文件过多导致状态文件膨胀
    MAX_PROTOTYPE_FILES = 10
    if len(html_files) > MAX_PROTOTYPE_FILES:
        html_files = html_files[:MAX_PROTOTYPE_FILES]

    parts = []
    design_tokens_extracted = False

    for html_path in html_files:
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        rel_path = os.path.relpath(html_path, project_dir)
        parent_name = os.path.basename(os.path.dirname(html_path))
        page_name = parent_name.replace("_", " ").replace("-", " ").strip().title()

        # 提取共享 design tokens（仅从第一个文件）
        if not design_tokens_extracted:
            # tailwind.config — 用 greedy .* 匹配嵌套大括号，</script> 锚定右边界
            tc_match = re.search(
                r"tailwind\.config\s*=\s*(\{.*\})\s*\n\s*</script>",
                html_content,
                re.DOTALL,
            )
            if tc_match:
                parts.append("#### Design Tokens (tailwind.config)")
                parts.append("```js")
                parts.append(f"tailwind.config = {tc_match.group(1).strip()}")
                parts.append("```")
                parts.append("")

            # custom CSS
            style_blocks = re.findall(r"<style[^>]*>(.*?)</style>", html_content, re.DOTALL)
            if style_blocks:
                combined_css = "\n".join(s.strip() for s in style_blocks if s.strip())
                if combined_css:
                    parts.append("#### Custom CSS")
                    parts.append("```css")
                    parts.append(combined_css)
                    parts.append("```")
                    parts.append("")

            design_tokens_extracted = True

        # 提取 body HTML 结构
        body_match = re.search(r"<body[^>]*>(.*)</body>", html_content, re.DOTALL)
        if body_match:
            # group(0) 保留 <body class="..."> 以获取页面级 Tailwind classes
            body_html = body_match.group(0).strip()
            # 每页限制 4000 chars，保留顶层结构
            if len(body_html) > 4000:
                body_html = body_html[:4000] + "\n<!-- ... truncated, read full file -->"

            parts.append(f"#### Prototype: {page_name}")
            parts.append(f"<!-- source: {rel_path} -->")
            parts.append("```html")
            parts.append(body_html)
            parts.append("```")
            parts.append("")

    return "\n".join(parts)


def list_prototype_files(proto_dir: str, project_dir: str) -> str:
    """遍历 ui-prototype/ 目录，输出 HTML 原型文件的 markdown 表格"""
    if not proto_dir or not os.path.isdir(proto_dir):
        return ""

    rows = []
    for root, _dirs, files in os.walk(proto_dir):
        for fname in sorted(files):
            if not fname.endswith(".html"):
                continue
            full_path = os.path.join(root, fname)
            rel_path = os.path.relpath(full_path, project_dir)
            # 从目录名推导页面名（将下划线/连字符转为空格并 title-case）
            parent_name = os.path.basename(root)
            page_name = parent_name.replace("_", " ").replace("-", " ").strip().title()
            rows.append((page_name, rel_path))

    if not rows:
        return ""

    lines = ["| # | Page | File Path |", "|---|------|-----------|"]
    for i, (page, path) in enumerate(rows, 1):
        lines.append(f"| {i} | {page} | {path} |")

    return "\n".join(lines)


def read_design_docs(
    project_dir: str, epic_path: str = None, source_documents: dict = None
) -> dict:
    """读取设计文档摘要 — 优先使用 Epic YAML source_documents，然后读取 docs/project/"""
    docs = {}
    source_documents = source_documents or {}

    project_docs_dir = os.path.join(project_dir, "docs", "project")
    research_dir = os.path.join(project_dir, "docs", "reference", "research")

    def has_markdown_source(path: str) -> bool:
        """目录至少含一个 Markdown 文件才可覆盖旧单文件 fallback。"""
        if os.path.isdir(path):
            return any(filename.endswith(".md") for filename in os.listdir(path))
        return os.path.isfile(path)

    def read_markdown_source(path: str) -> str:
        """读取单文件或模块化 Markdown 目录。目录内容按文件名稳定拼接。"""
        if os.path.isdir(path):
            sections = []
            for filename in sorted(os.listdir(path)):
                if not filename.endswith(".md"):
                    continue
                file_path = os.path.join(path, filename)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                rel_path = os.path.relpath(file_path, project_dir)
                sections.append(f"## Source: {rel_path}\n\n{content}")
            return "\n\n".join(sections)

        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    doc_candidates = {
        "architecture": ["architecture.md"],
        # 模块化目录优先；旧单文件仅兼容读取。
        "api_spec": ["api", "api_spec.md"],
        "database_schema": ["data", "database_schema.md"],
        "requirements": ["requirements.md"],
        "design_guidelines": ["design_guidelines.md"],
    }

    for name, candidates in doc_candidates.items():
        # 优先使用 source_documents 中的路径
        path = source_documents.get(name)
        if not path or not has_markdown_source(path):
            path = None
            for candidate in candidates:
                candidate_path = os.path.join(project_docs_dir, candidate)
                if has_markdown_source(candidate_path):
                    path = candidate_path
                    break

        if path and has_markdown_source(path):
            content = read_markdown_source(path)
            if name == "design_guidelines":
                docs[name] = extract_ui_spec_summary(content, path, project_dir)
            else:
                docs[name] = content[:3000] if len(content) > 3000 else content

    # 发现原型 HTML 目录并生成文件列表
    proto_dir = None
    for dirname in ("ui-prototype", "prototypes"):
        candidate = os.path.join(research_dir, dirname)
        if os.path.isdir(candidate):
            proto_dir = candidate
            break

    if proto_dir:
        proto_table = list_prototype_files(proto_dir, project_dir)
        if proto_table:
            docs["_prototype_files"] = proto_table
        else:
            docs["_prototype_files"] = f"(empty directory: {os.path.relpath(proto_dir, project_dir)})"

        # 提取原型结构（design tokens + body HTML）嵌入状态文件
        proto_structures = extract_prototype_structures(proto_dir, project_dir)
        if proto_structures:
            docs["_prototype_structures"] = proto_structures

    return docs


def generate_single_story_state(story: dict, docs: dict, epic_ref: str) -> str:
    """生成单 Story 模式的状态文件内容"""
    ac_text = (
        "\n".join(f"- {c}" for c in story["acceptance_criteria"])
        if story["acceptance_criteria"]
        else "- (见 Story 内容)"
    )

    return f"""---
active: true
mode: "story"
current_phase: 1
phase_name: "Understand"
max_phases: 6
completion_promise: "<promise>DO_STORY_COMPLETE</promise>"
checkpoints: []
story_id: "{story['story_id']}"
epic_ref: "{epic_ref}"
---

# do-story state

## Story
{story['content']}

## Acceptance Criteria
{ac_text}

## Design Constraints

### Architecture (from docs/project/architecture.md)
{docs.get('architecture', 'Not found - please create docs/project/architecture.md')[:1500]}

### API Contract (optional, from docs/project/api/*.md)
{docs.get('api_spec', 'N/A - update only when this Story changes the API contract')[:1500]}

### Data Model (optional, from docs/project/data/*.md)
{docs.get('database_schema', 'N/A - update only when this Story changes schema, migration, or persistence model')[:1500]}

### UI Spec (from docs/project/design_guidelines.md)
{docs.get('design_guidelines', 'Not found')}

### Prototype Files
{docs.get('_prototype_files', 'Not found')}

### Prototype Structures [BLOCKING - 前端 Story 必须参考]
{docs.get('_prototype_structures', 'Not found - no prototype HTML files')}

### DDD Compliance Rules [BLOCKING]
- Domain 层禁止导入: infrastructure/, application/, api/
- Infrastructure 必须实现 Domain 定义的 Repository 接口
- Application 层禁止直接使用 ORM Model (如 SQLAlchemy Model)
- API 层只处理 HTTP I/O，不包含业务逻辑

## Notes
- Update current_phase/phase_name after each phase
- Include completion_promise in final output when done
- To abort early, set active: false
"""


def generate_epic_state(
    epic_path: str, epic_title: str, selected_stories: list, all_stories_data: list, docs: dict
) -> str:
    """生成 Epic 模式的状态文件内容"""
    epic_ref = os.path.basename(epic_path).replace(".md", "")

    # 构建 selected_stories YAML
    stories_yaml_lines = []
    for i, story in enumerate(selected_stories):
        status = "in_progress" if i == 0 else "pending"
        stories_yaml_lines.append(f'  - id: "{story["id"]}"')
        stories_yaml_lines.append(f'    title: "{story["title"]}"')
        stories_yaml_lines.append(f'    status: "{status}"')
        if i == 0:
            stories_yaml_lines.append("    current_phase: 1")
            stories_yaml_lines.append('    phase_name: "Understand"')
    stories_yaml = "\n".join(stories_yaml_lines)

    # 第一个 Story 的内容
    first_story = all_stories_data[0] if all_stories_data else {}
    first_story_content = first_story.get("content", "(Story content not found)")
    ac_text = (
        "\n".join(f"- {c}" for c in first_story.get("acceptance_criteria", []))
        if first_story.get("acceptance_criteria")
        else "- (见 Story 内容)"
    )

    return (
        f"""---
active: true
mode: "epic"
epic_file: "{epic_path}"
epic_title: "{epic_title}"
epic_ref: "{epic_ref}"

selected_stories:
{stories_yaml}

current_story_index: 0
total_stories: {len(selected_stories)}
current_phase: 1
phase_name: "Understand"
max_phases: 6
completion_promise: "<promise>DO_STORY_COMPLETE</promise>"
checkpoints: []
---

# do-story state (Epic Mode)

## Epic: {epic_title}

### Selected Stories
| # | ID | Title | Status |
|---|-----|-------|--------|
"""
        + "\n".join(
            [
                f'| {i+1} | {s["id"]} | {s["title"]} | {"🔄 In Progress" if i == 0 else "⏳ Pending"} |'
                for i, s in enumerate(selected_stories)
            ]
        )
        + f"""

---

## Current Story: {selected_stories[0]["id"]} - {selected_stories[0]["title"]}

{first_story_content}

## Acceptance Criteria
{ac_text}

## Design Constraints

### Architecture (from docs/project/architecture.md)
{docs.get('architecture', 'Not found - please create docs/project/architecture.md')[:1500]}

### API Contract (optional, from docs/project/api/*.md)
{docs.get('api_spec', 'N/A - update only when this Story changes the API contract')[:1500]}

### Data Model (optional, from docs/project/data/*.md)
{docs.get('database_schema', 'N/A - update only when this Story changes schema, migration, or persistence model')[:1500]}

### UI Spec (from docs/project/design_guidelines.md)
{docs.get('design_guidelines', 'Not found')}

### Prototype Files
{docs.get('_prototype_files', 'Not found')}

### Prototype Structures [BLOCKING - 前端 Story 必须参考]
{docs.get('_prototype_structures', 'Not found - no prototype HTML files')}

### DDD Compliance Rules [BLOCKING]
- Domain 层禁止导入: infrastructure/, application/, api/
- Infrastructure 必须实现 Domain 定义的 Repository 接口
- Application 层禁止直接使用 ORM Model (如 SQLAlchemy Model)
- API 层只处理 HTTP I/O，不包含业务逻辑

## Notes
- Epic Mode: Complete all phases for current Story before moving to next
- After Phase 5: Update current Story status to "completed", increment current_story_index
- When all Stories complete: Output completion_promise
- To abort early, set active: false
"""
    )


def cmd_scan(epic_path: str):
    """扫描模式：列出所有 Stories 供选择"""
    stories = scan_all_stories(epic_path)
    epic_title = extract_epic_title(epic_path)

    if not stories:
        print(f"Error: No stories found in {epic_path}", file=sys.stderr)
        print("Expected format: ## Story X.Y: Title or ## X.Y Title", file=sys.stderr)
        sys.exit(1)

    # 输出 JSON 格式供 Claude 解析
    print("STORIES_FOUND:")
    print(
        json.dumps(
            {"epic_file": epic_path, "epic_title": epic_title, "stories": stories},
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_init_epic(epic_path: str, story_ids: str, project_dir: str):
    """Epic 模式：初始化选定的 Stories"""
    all_stories = scan_all_stories(epic_path)
    epic_title = extract_epic_title(epic_path)

    # 解析选定的 Story IDs
    selected_ids = [s.strip() for s in story_ids.split(",")]

    # 过滤出选定的 Stories
    selected_stories = [s for s in all_stories if s["id"] in selected_ids]

    if not selected_stories:
        print(f"Error: No matching stories found for IDs: {story_ids}", file=sys.stderr)
        sys.exit(1)

    # 按原始顺序排序
    id_order = {id: i for i, id in enumerate(selected_ids)}
    selected_stories.sort(key=lambda s: id_order.get(s["id"], 999))

    # 提取每个 Story 的内容
    all_stories_data = []
    for story in selected_stories:
        story_data = extract_story_by_id(epic_path, story["id"])
        story_data["title"] = story["title"]
        all_stories_data.append(story_data)

    # 解析 Epic YAML source_documents
    source_documents = parse_epic_source_documents(epic_path, project_dir)

    # 读取设计文档（优先 YAML 路径，fallback 到目录搜索）
    docs = read_design_docs(project_dir, epic_path=epic_path, source_documents=source_documents)

    # 生成状态文件
    task_id = f"{int(time.time())}-{os.getpid()}-{secrets.token_hex(4)}"
    state_dir = os.path.join(project_dir, ".claude")
    os.makedirs(state_dir, exist_ok=True)
    state_file = os.path.join(state_dir, f"do-story.{task_id}.local.md")

    content = generate_epic_state(epic_path, epic_title, selected_stories, all_stories_data, docs)

    with open(state_file, "w", encoding="utf-8") as f:
        f.write(content)

    # 输出信息
    print(f"Initialized (Epic Mode): {state_file}")
    print(f"task_id: {task_id}")
    print(f"epic: {epic_title}")
    print(f"selected_stories: {len(selected_stories)}")
    for s in selected_stories:
        print(f"  - {s['id']}: {s['title']}")
    print(f"design_docs_found: {list(docs.keys())}")
    print(f"\nexport DO_STORY_TASK_ID={task_id}")


def cmd_init_single(story_path: str, anchor: str, project_dir: str):
    """Single Story 模式：初始化单个 Story"""
    # 提取 Story 内容
    story = extract_story_content(story_path, anchor)
    epic_ref = os.path.basename(story_path).replace(".md", "")

    # 解析 Epic YAML source_documents
    source_documents = parse_epic_source_documents(story_path, project_dir)

    # 读取设计文档（优先 YAML 路径，fallback 到目录搜索）
    docs = read_design_docs(project_dir, epic_path=story_path, source_documents=source_documents)

    # 生成状态文件
    task_id = f"{int(time.time())}-{os.getpid()}-{secrets.token_hex(4)}"
    state_dir = os.path.join(project_dir, ".claude")
    os.makedirs(state_dir, exist_ok=True)
    state_file = os.path.join(state_dir, f"do-story.{task_id}.local.md")

    content = generate_single_story_state(story, docs, epic_ref)

    with open(state_file, "w", encoding="utf-8") as f:
        f.write(content)

    # 输出信息
    print(f"Initialized (Single Story Mode): {state_file}")
    print(f"task_id: {task_id}")
    print(f"story: {story['story_id']} from {epic_ref}")
    print(f"design_docs_found: {list(docs.keys())}")
    print(f"acceptance_criteria: {len(story['acceptance_criteria'])} items")
    print(f"\nexport DO_STORY_TASK_ID={task_id}")


def main():
    parser = argparse.ArgumentParser(description="Initialize do-story workflow state")
    parser.add_argument(
        "epic_path",
        help="Epic file path with optional #story-id (e.g., docs/tasks/epics/epic-001.md or docs/tasks/epics/epic-001.md#1.2)",
    )
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Scan mode: list all stories in the Epic file (for Epic mode selection)",
    )
    parser.add_argument(
        "--stories", type=str, help='Comma-separated Story IDs to implement (e.g., "1.1,1.2,1.3")'
    )
    args = parser.parse_args()

    # 解析路径
    path, anchor = parse_story_path(args.epic_path)

    # 检查文件存在
    if not os.path.exists(path):
        print(f"Error: Epic file not found: {path}", file=sys.stderr)
        sys.exit(1)

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

    # 模式选择
    if args.scan:
        # 扫描模式：列出所有 Stories
        cmd_scan(path)
    elif args.stories:
        # Epic 模式：初始化选定的 Stories
        cmd_init_epic(path, args.stories, project_dir)
    elif anchor:
        # Single Story 模式：带 #anchor
        cmd_init_single(path, anchor, project_dir)
    else:
        # 默认：如果没有 anchor 也没有 --stories，进入扫描模式
        cmd_scan(path)


if __name__ == "__main__":
    main()
