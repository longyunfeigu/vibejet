#!/usr/bin/env bash
# input: Epic markdown file from this repo or a downstream application
# output: Makefile generation + sequential/parallel story execution via claude -p
# owner: wanhua.gu
# pos: 脚本工具 - Epic 级 Story 自动化编排（已弃用）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
set -euo pipefail

# ─────────────────────────────────────────────
# ⛔ DEPRECATED (2026-07-02)
# 本脚本内部调用的 run-story skill 已从仓库移除，直接运行会产出无效 session。
# Epic 执行请改用：vj-epic-plan 生成 task packets → vj-work 编排执行
# （vj-work 自带波次并行、worktree 隔离与 verify/review gate）。
# 如确需强制运行本脚本：FORCE_RUN_EPIC=1 ./scripts/run-epic.sh <epic-file>
# ─────────────────────────────────────────────
if [[ "${FORCE_RUN_EPIC:-0}" != "1" ]]; then
  echo "⛔ run-epic.sh 已弃用：依赖的 run-story skill 已移除。请改用 vj-epic-plan + vj-work。" >&2
  echo "   如确需强制运行：FORCE_RUN_EPIC=1 $0 ..." >&2
  exit 1
fi

# ─────────────────────────────────────────────
# run-epic.sh — Epic 文件即 Pipeline
#
# 从 Epic markdown 解析 story 列表和依赖关系，
# 自动生成 Makefile DAG，用 make 编排 claude -p 执行。
#
# Usage:
#   ./scripts/run-epic.sh <epic-file>                  # 顺序执行所有 story
#   ./scripts/run-epic.sh <epic-file> -j2              # 最多 2 个 story 并行
#   ./scripts/run-epic.sh <epic-file> --dry-run        # 只生成 Makefile，不执行
#   ./scripts/run-epic.sh <epic-file> --from 1.3       # 从 story 1.3 开始
#   ./scripts/run-epic.sh <epic-file> --target 1.4     # 只跑到 story 1.4（含依赖）
#   ./scripts/run-epic.sh <epic-file> --reset 1.2      # 清除 1.2 的完成标记，重跑
#   ./scripts/run-epic.sh <epic-file> --status         # 查看各 story 完成状态
# ─────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RUN_DIR="$PROJECT_ROOT/.epic-run"
CHECK_SCRIPT="$SCRIPT_DIR/check-story-result.sh"

# ── Colors ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ── Defaults ──
EPIC_FILE=""
PARALLEL=""
DRY_RUN=false
FROM_STORY=""
TARGET_STORY=""
RESET_STORY=""
SHOW_STATUS=false

# ── Parse args ──
while [[ $# -gt 0 ]]; do
  case $1 in
    -j*)
      PARALLEL="$1"
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --from)
      FROM_STORY="$2"
      shift 2
      ;;
    --target)
      TARGET_STORY="$2"
      shift 2
      ;;
    --reset)
      RESET_STORY="$2"
      shift 2
      ;;
    --status)
      SHOW_STATUS=true
      shift
      ;;
    -h|--help)
      head -25 "$0" | tail -14
      exit 0
      ;;
    *)
      if [[ -z "$EPIC_FILE" ]]; then
        EPIC_FILE="$1"
      fi
      shift
      ;;
  esac
done

if [[ -z "$EPIC_FILE" ]]; then
  echo -e "${RED}Error: Epic file path required${NC}"
  echo "Usage: $0 <epic-file> [options]"
  exit 1
fi

# Resolve to absolute path
if [[ ! "$EPIC_FILE" = /* ]]; then
  EPIC_FILE="$PROJECT_ROOT/$EPIC_FILE"
fi

if [[ ! -f "$EPIC_FILE" ]]; then
  echo -e "${RED}Error: Epic file not found: $EPIC_FILE${NC}"
  exit 1
fi

# ── Extract epic ID from filename (epic-1-infrastructure.md → 1) ──
EPIC_BASENAME="$(basename "$EPIC_FILE" .md)"
EPIC_ID="$(echo "$EPIC_BASENAME" | sed -E 's/^epic-([0-9]+).*/\1/')"

DONE_DIR="$RUN_DIR/done/epic-$EPIC_ID"
LOG_DIR="$RUN_DIR/logs/epic-$EPIC_ID"
MAKEFILE="$RUN_DIR/Makefile.epic-$EPIC_ID"

# ── Reset mode ──
if [[ -n "$RESET_STORY" ]]; then
  marker="$DONE_DIR/$RESET_STORY"
  if [[ -f "$marker" ]]; then
    rm "$marker"
    echo -e "${YELLOW}Reset: story $RESET_STORY marker removed${NC}"
  else
    echo -e "${YELLOW}Story $RESET_STORY was not marked as done${NC}"
  fi
  exit 0
fi

# ─────────────────────────────────────────────
# Parse Epic → extract stories and dependencies
# ─────────────────────────────────────────────
parse_epic() {
  local epic_file="$1"
  local current_story=""

  # Arrays: stories[i] = "X.Y", deps[i] = "X.Y X.Z" (space-separated) or ""
  STORIES=()
  STORY_DEPS=()

  while IFS= read -r line; do
    # Match story heading: ### Story X.Y: ...
    if [[ "$line" =~ ^###[[:space:]]+Story[[:space:]]+([0-9]+\.[0-9]+) ]]; then
      current_story="${BASH_REMATCH[1]}"
      STORIES+=("$current_story")
      STORY_DEPS+=("")  # placeholder, filled when we see 依赖 line
    fi

    # Match dependency line: **依赖**: ...
    if [[ "$line" =~ ^\*\*依赖\*\*:[[:space:]]*(.*) ]] && [[ -n "$current_story" ]]; then
      local dep_text="${BASH_REMATCH[1]}"
      local deps=""

      if [[ "$dep_text" == "无" ]]; then
        deps=""
      else
        # Extract all Story X.Y references (handles both intra and cross-epic)
        deps=$(echo "$dep_text" | grep -oE '[0-9]+\.[0-9]+' | tr '\n' ' ' | sed 's/ $//')
      fi

      # Update last entry in STORY_DEPS
      STORY_DEPS[${#STORY_DEPS[@]}-1]="$deps"
      current_story=""  # prevent re-matching
    fi
  done < "$epic_file"
}

parse_epic "$EPIC_FILE"

if [[ ${#STORIES[@]} -eq 0 ]]; then
  echo -e "${RED}Error: No stories found in $EPIC_FILE${NC}"
  exit 1
fi

# ── Status mode ──
if $SHOW_STATUS; then
  echo -e "${BOLD}Epic $EPIC_ID — Story Status${NC}"
  echo "─────────────────────────────"
  for i in "${!STORIES[@]}"; do
    sid="${STORIES[$i]}"
    if [[ -f "$DONE_DIR/$sid" ]]; then
      echo -e "  ${GREEN}✅ Story $sid${NC}  (done $(date -r "$DONE_DIR/$sid" '+%m-%d %H:%M'))"
    else
      echo -e "  ${YELLOW}⬚  Story $sid${NC}  (pending)"
    fi
  done
  total=${#STORIES[@]}
  done_count=$(find "$DONE_DIR" -maxdepth 1 -type f 2>/dev/null | wc -l | tr -d ' ')
  echo "─────────────────────────────"
  echo -e "  ${CYAN}$done_count / $total completed${NC}"
  exit 0
fi

# ─────────────────────────────────────────────
# Generate Makefile
# ─────────────────────────────────────────────
mkdir -p "$DONE_DIR" "$LOG_DIR"

# Determine the final target
if [[ -n "$TARGET_STORY" ]]; then
  ALL_TARGET="$DONE_DIR/$TARGET_STORY"
else
  # Default: last story in the epic
  ALL_TARGET=""
  for sid in "${STORIES[@]}"; do
    ALL_TARGET="$ALL_TARGET $DONE_DIR/$sid"
  done
fi

# Relative epic path for the prompt
EPIC_REL="$(python3 -c "import os; print(os.path.relpath('$EPIC_FILE', '$PROJECT_ROOT'))")"

cat > "$MAKEFILE" << 'HEADER'
# Auto-generated by run-epic.sh — do not edit
SHELL := /bin/bash
.ONESHELL:

HEADER

echo "all: $ALL_TARGET" >> "$MAKEFILE"
echo "" >> "$MAKEFILE"

for i in "${!STORIES[@]}"; do
  sid="${STORIES[$i]}"
  dep_str="${STORY_DEPS[$i]}"

  # Build prerequisite list
  prereqs=""
  if [[ -n "$dep_str" ]]; then
    for dep in $dep_str; do
      # Check if this dep is in the current epic
      dep_epic="${dep%%.*}"
      if [[ "$dep_epic" == "$EPIC_ID" ]]; then
        prereqs="$prereqs $DONE_DIR/$dep"
      else
        # Cross-epic dependency — check marker from another epic run
        cross_marker="$RUN_DIR/done/epic-$dep_epic/$dep"
        prereqs="$prereqs $cross_marker"
      fi
    done
  fi

  # Handle --from: skip touch for stories before FROM_STORY
  # (We pre-create done markers so make skips them)

  cat >> "$MAKEFILE" << EOF
$DONE_DIR/$sid:$prereqs
	@echo ""
	@echo -e "\033[1;34m════════════════════════════════════════\033[0m"
	@echo -e "\033[1;34m  Story $sid — Starting\033[0m"
	@echo -e "\033[1;34m════════════════════════════════════════\033[0m"
	@mkdir -p $DONE_DIR $LOG_DIR
	cd $PROJECT_ROOT && claude -p "使用 run-story，处理 $EPIC_REL#story-$sid" \\
	  --output-format json \\
	  --permission-mode auto \\
	  --no-session-persistence \\
	  2>&1 | tee $LOG_DIR/$sid.log
	@$CHECK_SCRIPT $LOG_DIR/$sid.log
	@touch \$@
	@echo -e "\033[0;32m✅ Story $sid — Done\033[0m"

EOF
done

# ── --from: pre-mark earlier stories as done ──
if [[ -n "$FROM_STORY" ]]; then
  for sid in "${STORIES[@]}"; do
    if [[ "$sid" == "$FROM_STORY" ]]; then
      break
    fi
    if [[ ! -f "$DONE_DIR/$sid" ]]; then
      touch "$DONE_DIR/$sid"
      echo -e "${YELLOW}⏭  Skipping Story $sid (--from $FROM_STORY)${NC}"
    fi
  done
fi

# ── Summary ──
echo ""
echo -e "${BOLD}Epic $EPIC_ID — Pipeline${NC}"
echo "─────────────────────────────"
for i in "${!STORIES[@]}"; do
  sid="${STORIES[$i]}"
  dep_str="${STORY_DEPS[$i]}"
  if [[ -f "$DONE_DIR/$sid" ]]; then
    status="${GREEN}✅${NC}"
  else
    status="${YELLOW}⬚${NC}"
  fi
  if [[ -n "$dep_str" ]]; then
    echo -e "  $status Story $sid  ← depends on: $dep_str"
  else
    echo -e "  $status Story $sid  (no dependencies)"
  fi
done
echo "─────────────────────────────"
echo -e "  Makefile: ${CYAN}$MAKEFILE${NC}"

if $DRY_RUN; then
  echo ""
  echo -e "${YELLOW}Dry run — Makefile generated but not executed${NC}"
  echo -e "To execute: ${BOLD}make -f $MAKEFILE all${NC}"
  echo ""
  echo "Generated Makefile:"
  echo "─────────────────────────────"
  cat "$MAKEFILE"
  exit 0
fi

# ── Execute ──
echo ""
echo -e "${BOLD}Starting execution...${NC}"
echo ""

MAKE_ARGS="-f $MAKEFILE"
if [[ -n "$PARALLEL" ]]; then
  MAKE_ARGS="$MAKE_ARGS $PARALLEL"
fi

make $MAKE_ARGS all

echo ""
echo -e "${GREEN}${BOLD}════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  Epic $EPIC_ID — All stories completed${NC}"
echo -e "${GREEN}${BOLD}════════════════════════════════════════${NC}"
