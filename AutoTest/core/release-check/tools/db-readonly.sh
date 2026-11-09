#!/usr/bin/env bash
# Release-Check tool `db-readonly`: run one read-only SQL query against a service's database.
# The query runs inside the service's own pod, with the pod's own database settings, in a
# read-only transaction (writes fail) with a 30 s statement timeout. Output is TSV.
#
# Usage: db-readonly.sh --via "<remote command prefix>" --service <deployment> [--namespace <ns>] [--max-rows N] --sql "<SELECT ...>"
#   db-readonly.sh --via "ssh my-env" --service flow-backend --sql "SELECT count(*) FROM pg_stat_activity"
# The pod must carry DATABASE_URL or POSTGRES_HOST/USER/PASSWORD/DB.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
VIA_STR=""; SERVICE=""; NS="voice-agent"; SQL=""; MAX=200
while [ $# -gt 0 ]; do
  case "$1" in
    --via) VIA_STR=$2; shift 2 ;;
    --service) SERVICE=$2; shift 2 ;;
    --namespace) NS=$2; shift 2 ;;
    --max-rows) MAX=$2; shift 2 ;;
    --sql) SQL=$2; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
[ -n "$VIA_STR" ] && [ -n "$SERVICE" ] && [ -n "$SQL" ] || { echo "usage: $0 --via \"<prefix>\" --service <deployment> [--namespace ns] [--max-rows N] --sql \"<SELECT ...>\"" >&2; exit 2; }
[[ "$SERVICE" =~ ^[a-z0-9-]+$ && "$NS" =~ ^[a-z0-9-]+$ && "$MAX" =~ ^[0-9]+$ ]] || { echo "invalid service, namespace or max-rows" >&2; exit 2; }
read -r -a VIA <<< "$VIA_STR"
SQL_B64=$(printf '%s' "$SQL" | base64 | tr -d '\n')
"${VIA[@]}" "kubectl exec -i -n $NS deploy/$SERVICE -- python3 - $SQL_B64 $MAX" < "$HERE/db_readonly.py"
