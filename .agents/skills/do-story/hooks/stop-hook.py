#!/usr/bin/env python3
"""
stop-hook.py - 检查 do-story 工作流是否完成

功能:
- 查找活跃的 do-story 状态文件
- 支持 Single Story 和 Epic 模式
- 检查是否已完成所有 phase 和所有 Stories
- 如果未完成，阻止退出
"""
import glob
import json
import os
import re
import sys

PHASE_NAMES = {
    1: "Understand",
    2: "Clarify",
    3: "Design",
    4: "Implement",
    5: "Complete",
}


def get_frontmatter(file_path: str, key: str) -> str:
    """从 YAML frontmatter 中提取值"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if not lines or lines[0].strip() != "---":
            return ""

        for line in lines[1:]:
            if line.strip() == "---":
                break
            # 匹配 key: value 或 key: "value"
            match = re.match(rf'^{re.escape(key)}:\s*["\']?([^"\']+)["\']?', line)
            if match:
                return match.group(1).strip()
    except Exception:
        pass
    return ""


def get_frontmatter_int(file_path: str, key: str, default: int = 0) -> int:
    """从 YAML frontmatter 中提取整数值"""
    raw = get_frontmatter(file_path, key)
    try:
        return int(raw)
    except (ValueError, TypeError):
        return default


def get_body(file_path: str) -> str:
    """获取 frontmatter 之后的内容"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[2]
    except Exception:
        pass
    return ""


def check_single_story_state(state_file: str, stdin_payload: str) -> str:
    """检查 Single Story 模式状态，返回阻止原因或空字符串"""
    current_phase = get_frontmatter_int(state_file, "current_phase", 1)
    max_phases = get_frontmatter_int(state_file, "max_phases", 5)
    phase_name = get_frontmatter(state_file, "phase_name") or PHASE_NAMES.get(
        current_phase, f"Phase {current_phase}"
    )
    completion_promise = (
        get_frontmatter(state_file, "completion_promise") or "<promise>DO_STORY_COMPLETE</promise>"
    )
    story_id = get_frontmatter(state_file, "story_id")
    epic_ref = get_frontmatter(state_file, "epic_ref")

    # 检查是否完成所有 phase
    phases_done = current_phase >= max_phases

    # 检查 completion promise 是否存在
    promise_met = check_promise_met(state_file, stdin_payload, completion_promise)

    # 如果完成，清理状态文件
    if phases_done and promise_met:
        try:
            os.remove(state_file)
        except Exception:
            pass
        return ""

    # 未完成，返回阻止原因
    story_info = f" (Story: {story_id} from {epic_ref})" if story_id else ""

    if not phases_done:
        return (
            f"do-story 未完成{story_info}: Phase {current_phase}/{max_phases} ({phase_name}). "
            f"请继续完成剩余阶段。更新 {os.path.basename(state_file)} 中的 current_phase/phase_name。"
            f"完成后输出: {completion_promise}。"
            f"如需强制退出，设置 active: false。"
        )
    else:
        return (
            f"do-story 已到最后阶段{story_info} (Phase {current_phase}/{max_phases}, {phase_name})，"
            f"但未检测到完成标记: {completion_promise}。"
            f"请在输出中包含此标记，或设置 active: false 强制退出。"
        )


def check_epic_state(state_file: str, stdin_payload: str) -> str:
    """检查 Epic 模式状态，返回阻止原因或空字符串"""
    current_story_index = get_frontmatter_int(state_file, "current_story_index", 0)
    total_stories = get_frontmatter_int(state_file, "total_stories", 1)
    current_phase = get_frontmatter_int(state_file, "current_phase", 1)
    max_phases = get_frontmatter_int(state_file, "max_phases", 5)
    phase_name = get_frontmatter(state_file, "phase_name") or PHASE_NAMES.get(
        current_phase, f"Phase {current_phase}"
    )
    completion_promise = (
        get_frontmatter(state_file, "completion_promise") or "<promise>DO_STORY_COMPLETE</promise>"
    )
    epic_title = get_frontmatter(state_file, "epic_title") or "Epic"

    # Epic 完成条件：所有 Stories 都完成 (current_story_index >= total_stories - 1) 且 promise 存在
    all_stories_done = current_story_index >= total_stories - 1 and current_phase >= max_phases
    promise_met = check_promise_met(state_file, stdin_payload, completion_promise)

    # 如果完成，清理状态文件
    if all_stories_done and promise_met:
        try:
            os.remove(state_file)
        except Exception:
            pass
        return ""

    # 计算进度
    completed_stories = current_story_index
    current_story_num = current_story_index + 1

    # 未完成，返回阻止原因
    if not all_stories_done:
        return (
            f"do-story Epic 未完成 ({epic_title}): "
            f"Story {current_story_num}/{total_stories}, Phase {current_phase}/{max_phases} ({phase_name}). "
            f"已完成 {completed_stories} 个 Stories。"
            f"请继续完成当前 Story 的剩余阶段。"
            f"当前 Story 完成后，更新 current_story_index 并开始下一个 Story。"
            f"所有 Stories 完成后输出: {completion_promise}。"
            f"如需强制退出，设置 active: false。"
        )
    else:
        return (
            f"do-story Epic 已完成所有 Stories ({epic_title})，"
            f"但未检测到完成标记: {completion_promise}。"
            f"请在输出中包含此标记，或设置 active: false 强制退出。"
        )


def check_promise_met(state_file: str, stdin_payload: str, completion_promise: str) -> bool:
    """检查 completion promise 是否存在

    Uses strict line-based matching to avoid false positives when the promise
    string is merely mentioned in discussion (e.g. talking about hooks).
    """
    if not completion_promise:
        return False

    # 检查 stdin — require promise on its own line (trimmed)
    if stdin_payload:
        for line in stdin_payload.splitlines():
            if line.strip() == completion_promise:
                return True

    # 检查状态文件 body — same strict matching
    body = get_body(state_file)
    if body:
        for line in body.splitlines():
            if line.strip() == completion_promise:
                return True

    return False


def check_state_file(state_file: str, stdin_payload: str) -> str:
    """检查单个状态文件，返回阻止原因或空字符串"""
    # 检查是否活跃
    active_raw = get_frontmatter(state_file, "active")
    if active_raw.lower() not in ("true", "1", "yes", "on"):
        return ""

    # 判断模式
    mode = get_frontmatter(state_file, "mode")

    if mode == "epic":
        return check_epic_state(state_file, stdin_payload)
    else:
        # 默认为 single story 模式
        return check_single_story_state(state_file, stdin_payload)


def main():
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    state_dir = os.path.join(project_dir, ".claude")

    # 检查特定 task_id (如果设置了环境变量)
    task_id = os.environ.get("DO_STORY_TASK_ID", "")

    if task_id:
        candidate = os.path.join(state_dir, f"do-story.{task_id}.local.md")
        state_files = [candidate] if os.path.isfile(candidate) else []
    else:
        # 查找所有 do-story 状态文件
        state_files = glob.glob(os.path.join(state_dir, "do-story.*.local.md"))

    if not state_files:
        sys.exit(0)

    # 读取 stdin (用于检查 completion promise)
    stdin_payload = ""
    if not sys.stdin.isatty():
        try:
            stdin_payload = sys.stdin.read()
        except Exception:
            pass

    # 检查每个状态文件
    blocking_reasons = []
    for state_file in state_files:
        reason = check_state_file(state_file, stdin_payload)
        if reason:
            blocking_reasons.append(reason)

    if not blocking_reasons:
        sys.exit(0)

    # 输出阻止信息
    combined_reason = " ".join(blocking_reasons)
    print(json.dumps({"decision": "block", "reason": combined_reason}))
    sys.exit(0)


if __name__ == "__main__":
    main()
