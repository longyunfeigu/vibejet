#!/usr/bin/env bash
# Usage: ./run-bdd.sh [module|all|smoke] [env=uat]
# module: all | smoke | kb | va | ai | mcp | wa | pn
# env:    sg | uat | dev  (default: uat)
MODULE=${1:-all}
ENV=${2:-uat}

# map module alias -> playwright --project value (bash 3.2 compatible)
case "$MODULE" in
  all)   PROJECT="bdd" ;;
  smoke) PROJECT="bdd" ;;
  kb)    PROJECT="knowledge-base" ;;
  va)    PROJECT="voice-agent" ;;
  ai)    PROJECT="ai-simulation" ;;
  mcp)   PROJECT="mcp-registry" ;;
  wa)    PROJECT="whatsapp" ;;
  pn)    PROJECT="phone-number" ;;
  *)
    echo "Unknown module: $MODULE"
    echo "Valid modules: all | smoke | kb | va | ai | mcp | wa | pn"
    exit 1
    ;;
esac

GREP_ARG=""
if [ "$MODULE" = "smoke" ]; then GREP_ARG="--grep @smoke"; fi

PROJECT_ARG=""
if [ -n "$PROJECT" ]; then PROJECT_ARG="--project=$PROJECT"; fi

export VOICE_AGENT_ENV=$ENV

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$ROOT"

echo "[run-bdd.sh] module=$MODULE env=$ENV"
if [ -n "$PROJECT_ARG" ]; then echo "[run-bdd.sh] project=$PROJECT"; fi
if [ -n "$GREP_ARG" ]; then echo "[run-bdd.sh] grep=@smoke"; fi

# playwright-bdd does not remove specs for feature files that were deleted on
# another branch. Clean the generated tree before each compile so branch
# switches cannot execute stale scenarios.
GEN_BDD_DIR="$ROOT/core/.gen-bdd"
if [ "$GEN_BDD_DIR" = "$ROOT/core/.gen-bdd" ]; then
  rm -rf "$GEN_BDD_DIR"
fi

npx bddgen test --config config/playwright.config.ts
BDDGEN_E=$?
if [ $BDDGEN_E -ne 0 ]; then
  echo "[run-bdd.sh] bddgen failed (exit $BDDGEN_E)"
  exit $BDDGEN_E
fi

npx playwright test --config config/playwright.config.ts $PROJECT_ARG $GREP_ARG
E=$?

npx tsx core/runner/generate-smoke-report.ts
npx tsx core/runner/generate-ai-sim-metrics-report.ts

# Emit a CSV of failed cases (用例名称/测试目的/测试步骤/失败原因) when any failed.
node core/runner/gen-failed-cases-csv.mjs "$ENV"

exit $E
