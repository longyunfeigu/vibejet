#!/usr/bin/env bash
# Usage: ./run-bdd.sh [module|all|smoke] [env=local]
# module: all | smoke | auth | home
# env:    an environment name in config/environments.json (default: local)
MODULE=${1:-all}
ENV=${2:-local}

# map module alias -> playwright --project value (bash 3.2 compatible)
case "$MODULE" in
  all)   PROJECT="bdd" ;;
  smoke) PROJECT="bdd" ;;
  auth)  PROJECT="auth" ;;
  home)  PROJECT="home" ;;
  *)
    echo "Unknown module: $MODULE"
    echo "Valid modules: all | smoke | auth | home"
    exit 1
    ;;
esac

GREP_ARG=""
if [ "$MODULE" = "smoke" ]; then GREP_ARG="--grep @smoke"; fi

PROJECT_ARG="--project=$PROJECT"

export E2E_ENV=$ENV

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$ROOT"

echo "[run-bdd.sh] module=$MODULE env=$ENV"
echo "[run-bdd.sh] project=$PROJECT"
if [ -n "$GREP_ARG" ]; then echo "[run-bdd.sh] grep=@smoke"; fi

# playwright-bdd does not remove specs for feature files that were deleted on
# another branch. Clean the generated tree before each compile so branch
# switches cannot execute stale scenarios.
rm -rf "$ROOT/core/.gen-bdd"

npx bddgen test --config config/playwright.config.ts
BDDGEN_E=$?
if [ $BDDGEN_E -ne 0 ]; then
  echo "[run-bdd.sh] bddgen failed (exit $BDDGEN_E)"
  exit $BDDGEN_E
fi

npx playwright test --config config/playwright.config.ts $PROJECT_ARG $GREP_ARG
E=$?

# Emit a CSV of failed cases (用例名称/测试目的/测试步骤/失败原因) when any failed.
node core/runner/gen-failed-cases-csv.mjs "$ENV"

exit $E
