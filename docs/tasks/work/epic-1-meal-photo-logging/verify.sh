#!/usr/bin/env bash
# input: Unit ID（U1-U5）或 all
# output: 对应 Unit 的 Story AC `验证:` 命令逐条执行结果 + exit code
#         （0=全绿且至少执行 1 条真实断言；1=有失败；2=用法错误；3=该范围只有 MANUAL 项、零真实断言——不算通过）
# pos: vj-epic-plan 为 epic-1-meal-photo-logging 生成；vj-work 用它作 Unit done signal，Phase 4 收尾跑 all。
#      命令物化自 docs/tasks/epics/epic-1-meal-photo-logging/stories/ 的 AC `验证:` 三要素
#      （API/DB 类物化为对应 task 将创建的 pytest；Browser 类为 MANUAL，走 vj-work UI QA/截图 gate）。
#      与 story AC 冲突时以 story 为准。一旦我被更新，务必更新我的开头注释
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"

FAILED=0
EXECUTED=0
MANUAL=0
run() {
  echo "▶ $*"
  EXECUTED=$((EXECUTED + 1))
  if ! "$@"; then echo "✗ FAILED: $*"; FAILED=1; fi
}
manual() {
  echo "▸ MANUAL: $*"
  MANUAL=$((MANUAL + 1))
}

ALL_UNITS="U1 U2 U3 U4 U5"

unit_U1() {
  # Story 1.1 拍摄或上传餐食照片（API/pytest AC → T002 创建 tests/test_meal_photos.py）
  run bash -c "cd backend && uv run pytest tests/test_meal_photos.py -q"
  manual "story-1.1 前端 AC ×4（/record 上传入口/上传态/无相机仅相册/截图审查）→ vj-work UI QA gate"
}

unit_U2() {
  # Story 1.2 AI 识别菜品与营养估算（→ T003 创建 tests/test_meal_recognition.py）
  run bash -c "cd backend && uv run pytest tests/test_meal_recognition.py -q"
  # 识别零副作用不变量（Story 1.2 Edge/Integration AC）
  run bash -c "cd backend && uv run pytest tests/test_meal_recognition.py -k 'no_side_effects or keeps_photo' -q"
  manual "story-1.2 前端 AC ×3（识别中态/失败态双入口/结果态明细+总热量）→ vj-work UI QA gate"
}

unit_U3() {
  # Story 1.3 修正识别明细（重算纯函数 → T005 创建 vitest；交互 AC → Browser MANUAL）
  run bash -c "cd frontend && pnpm vitest run src/features/meal-record --reporter=basic"
  manual "story-1.3 交互 AC ×5（份量重算/删除项/边界值/空明细禁保存/名称校验）→ Browser 验证走 vj-work UI QA gate"
}

unit_U4() {
  # Story 1.4 确认保存饮食记录（→ T004 创建 tests/test_meal_records.py）
  run bash -c "cd backend && uv run pytest tests/test_meal_records.py -q"
  manual "story-1.4 前端 AC ×2 + 餐次默认值 Browser AC → vj-work UI QA gate"
}

unit_U5() {
  # Story 1.5 文本补录一餐（text 路径在 T003/T004 的测试文件内，-k text 过滤）
  run bash -c "cd backend && uv run pytest tests/test_meal_recognition.py -k 'text' -q"
  run bash -c "cd backend && uv run pytest tests/test_meal_records.py -k 'text_fallback' -q"
  manual "story-1.5 前端 AC（兜底入口仅失败态出现/空文本禁提交/失败保留输入）→ vj-work UI QA gate"
}

target="${1:-all}"
case "$target" in
  all) for u in $ALL_UNITS; do "unit_$u"; done ;;
  U*)  "unit_$target" ;;
  *)   echo "usage: verify.sh [U1|U2|U3|U4|U5|all]"; exit 2 ;;
esac

echo "── executed=$EXECUTED manual=$MANUAL failed=$FAILED"
if [ "$FAILED" -ne 0 ]; then echo "RESULT: FAIL"; exit 1; fi
if [ "$EXECUTED" -eq 0 ]; then echo "RESULT: MANUAL-ONLY（零真实断言，不构成 done signal）"; exit 3; fi
echo "RESULT: PASS (manual pending: $MANUAL)"
