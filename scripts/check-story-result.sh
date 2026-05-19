#!/usr/bin/env bash
# input: Story 执行日志文件 (.epic-run/logs/epic-N/X.Y.log)
# output: exit 0 (success) / exit 1 (blocked or failed)
# owner: wanhua.gu
# pos: 脚本工具 - Story 执行结果检查；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
set -euo pipefail

LOG_FILE="${1:-}"

if [[ -z "$LOG_FILE" ]]; then
  echo "Usage: $0 <log-file>"
  exit 1
fi

if [[ ! -f "$LOG_FILE" ]]; then
  echo "❌ Log file not found: $LOG_FILE"
  exit 1
fi

# Check for blocked indicators in the output
# The run-story skill outputs a final conclusion: done / done with risks / blocked
if grep -qi '"blocked"' "$LOG_FILE" 2>/dev/null; then
  # Distinguish "blocked" as final conclusion vs. mentioned in passing
  # Look for patterns that indicate the story itself is blocked
  if grep -qiE '(最终结论|conclusion|final).*blocked' "$LOG_FILE" 2>/dev/null; then
    echo "🚫 Story blocked — see log: $LOG_FILE"
    exit 1
  fi
fi

# Check for common failure patterns
if grep -qi 'error.*fatal\|FATAL\|panic\|Traceback' "$LOG_FILE" 2>/dev/null; then
  # Only fail if these appear near the end (last 50 lines) — early errors may be fixed
  if tail -50 "$LOG_FILE" | grep -qi 'error.*fatal\|FATAL\|panic' 2>/dev/null; then
    echo "❌ Story failed with errors — see log: $LOG_FILE"
    exit 1
  fi
fi

# If we get here, consider it a success
exit 0
