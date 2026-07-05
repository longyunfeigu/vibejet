#!/usr/bin/env bash
# input: Unit ID（U1/U2/...）或 all
# output: 对应 Unit 的 Story AC `验证:` 命令逐条执行结果 + exit code
#         （0=全绿且至少执行 1 条真实断言；1=有失败；2=用法错误；3=该范围只有 MANUAL 项、零真实断言——不算通过）
# pos: vj-epic-plan Phase 5 按本模板为每个 epic 生成 work_dir/verify.sh；vj-work 用它作 Unit done signal，
#      Phase 4 收尾跑 all；一旦我被更新，务必更新我的开头注释
#
# 生成规则（vj-epic-plan 填充时遵守，然后删除本段注释）：
# - `验证:` 三要素（kind/target/assert）定义见 .agents/skills/vj-epic-story/SKILL.md Phase 4。
# - 每个 Unit 一个 unit_U{n} 函数，并把 U{n} 加进 ALL_UNITS；命令逐条物化自该 Unit Story AC。
# - 按 kind 物化（消除自由发挥）：
#     pytest  → run bash -c "cd backend && uv run pytest <target> -q"
#     API     → 优先物化为等价 pytest（httpx.AsyncClient）测试并按 pytest 跑；
#               确无对应测试时用 curl 探针：run bash -c "curl -fsS -X <METHOD> ${BASE_URL:-http://localhost:8000}<path> ..."
#               并在行上注释断言口径；探针需要起服务时在注释里写明前置命令
#     DB      → 物化为 pytest fixture 探针（推荐）或 run bash -c "cd backend && uv run python -c '<查询+断言>'"
#     Browser → manual "story-X.Y <AC 摘要>（浏览器验证，走 vj-work UI QA/截图 gate）"
# - manual 项不算失败也不算通过；某 Unit 全是 manual 时脚本会以 exit 3 拒绝当 done signal。
# - 命令与 story AC 冲突时以 story 为准并回改 story 或登记 ACD；不得在这里静默改口径。
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

ALL_UNITS="U1"

unit_U1() {
  # Story {N.M} {标题}
  # run bash -c "cd backend && uv run pytest tests/test_xxx.py -q"
  # manual "story-{N.M} {Browser AC 摘要}"
  :
}

target="${1:-all}"
case "$target" in
  all) for u in $ALL_UNITS; do "unit_$u"; done ;;
  U*)  "unit_$target" ;;
  *)   echo "usage: verify.sh [U1|...|all]"; exit 2 ;;
esac

echo "── executed=$EXECUTED manual=$MANUAL failed=$FAILED"
if [ "$FAILED" -ne 0 ]; then echo "RESULT: FAIL"; exit 1; fi
if [ "$EXECUTED" -eq 0 ]; then echo "RESULT: MANUAL-ONLY（零真实断言，不构成 done signal）"; exit 3; fi
echo "RESULT: PASS (manual pending: $MANUAL)"
