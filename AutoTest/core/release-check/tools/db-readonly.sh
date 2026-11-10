#!/usr/bin/env bash
# Release-Check tool `db-readonly`: run one read-only SQL query against vibejet's Postgres.
# The query runs through psql inside the database container, in a read-only transaction
# (writes fail) with a 30 s statement timeout. Output is a psql table.
#
# Usage: db-readonly.sh [--container user_db] [--user user] [--db userdb] [--via "<remote prefix>"] --sql "<SELECT ...>"
#   db-readonly.sh --sql "SELECT count(*) FROM users WHERE username LIKE 'e2e-%'"
# Defaults come from DB_CONTAINER / DB_USER / DB_NAME, then the docker-compose.yml values.
set -euo pipefail
CONTAINER="${DB_CONTAINER:-user_db}"; DB_USER="${DB_USER:-user}"; DB_NAME="${DB_NAME:-userdb}"; VIA_STR=""; SQL=""
while [ $# -gt 0 ]; do
  case "$1" in
    --container) CONTAINER=$2; shift 2 ;;
    --user) DB_USER=$2; shift 2 ;;
    --db) DB_NAME=$2; shift 2 ;;
    --via) VIA_STR=$2; shift 2 ;;
    --sql) SQL=$2; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
[ -n "$SQL" ] || { echo "usage: $0 [--container c] [--user u] [--db d] [--via \"<prefix>\"] --sql \"<SELECT ...>\"" >&2; exit 2; }
[[ "$CONTAINER" =~ ^[A-Za-z0-9_.-]+$ && "$DB_USER" =~ ^[A-Za-z0-9_]+$ && "$DB_NAME" =~ ^[A-Za-z0-9_]+$ ]] || { echo "invalid container, user or db" >&2; exit 2; }
VIA=()
[ -n "$VIA_STR" ] && read -r -a VIA <<< "$VIA_STR"
printf 'SET statement_timeout = 30000;\nBEGIN READ ONLY;\n%s;\nROLLBACK;\n' "${SQL%;}" \
  | ${VIA[@]+"${VIA[@]}"} docker exec -i "$CONTAINER" psql -v ON_ERROR_STOP=1 -X -q -U "$DB_USER" -d "$DB_NAME"
