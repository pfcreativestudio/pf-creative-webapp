#!/usr/bin/env bash
set -euo pipefail

API_BASE="${1:-}"
ORIGIN="${2:-https://pfcreativeaistudio.vercel.app}"

if [[ -z "$API_BASE" ]]; then
  echo "Usage: $0 <API_BASE> [ORIGIN]"
  exit 1
fi

code() { local URL="$1"; shift; curl -s -o /dev/null -w "%{http_code}" "$@" "$URL"; }

# OPTIONS /login with header checks
echo "== OPTIONS /login =="
LOGIN_OPT_HEADERS=$(curl -s -D - -o /dev/null -X OPTIONS "$API_BASE/login" \
  -H "Origin: $ORIGIN" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type,x-admin-password")
LOGIN_OPT_CODE=$(echo "$LOGIN_OPT_HEADERS" | sed -n '1s/[^0-9]*\([0-9][0-9][0-9]\).*/\1/p')
echo "$LOGIN_OPT_HEADERS" | sed -n '1,20p'
if [[ "$LOGIN_OPT_CODE" != "200" && "$LOGIN_OPT_CODE" != "204" ]]; then
  echo "❌ Preflight /login bad code: $LOGIN_OPT_CODE"; exit 1; fi
ACAO=$(echo "$LOGIN_OPT_HEADERS" | tr -d '\r' | awk -F': ' 'tolower($1)=="access-control-allow-origin"{print $2}' | tail -n1)
ACAC=$(echo "$LOGIN_OPT_HEADERS" | tr -d '\r' | awk -F': ' 'tolower($1)=="access-control-allow-credentials"{print $2}' | tail -n1)
ACAH=$(echo "$LOGIN_OPT_HEADERS" | tr -d '\r' | awk -F': ' 'tolower($1)=="access-control-allow-headers"{print $2}' | tail -n1 | tr '[:upper:]' '[:lower:]')
ACAM=$(echo "$LOGIN_OPT_HEADERS" | tr -d '\r' | awk -F': ' 'tolower($1)=="access-control-allow-methods"{print $2}' | tail -n1 | tr '[:upper:]' '[:lower:]')
if [[ "$ACAC" != "true" ]]; then echo "❌ ACAC not exactly 'true': $ACAC"; exit 1; fi
if [[ "$ACAO" != "$ORIGIN" ]]; then echo "❌ ACAO wrong: $ACAO"; exit 1; fi
if ! echo "$ACAH" | grep -q 'content-type'; then echo "❌ ACAH missing content-type"; exit 1; fi
if ! echo "$ACAH" | grep -q 'x-admin-password'; then echo "❌ ACAH missing x-admin-password"; exit 1; fi
if ! echo "$ACAM" | grep -q 'post'; then echo "❌ ACAM missing POST"; exit 1; fi

# OPTIONS /admin/verify-password
echo "\n== OPTIONS /admin/verify-password =="
ADMIN_OPT_HEADERS=$(curl -s -D - -o /dev/null -X OPTIONS "$API_BASE/admin/verify-password" \
  -H "Origin: $ORIGIN" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type,x-admin-password")
ADMIN_OPT_CODE=$(echo "$ADMIN_OPT_HEADERS" | sed -n '1s/[^0-9]*\([0-9][0-9][0-9]\).*/\1/p')
echo "$ADMIN_OPT_HEADERS" | sed -n '1,20p'
if [[ "$ADMIN_OPT_CODE" != "200" && "$ADMIN_OPT_CODE" != "204" ]]; then
  echo "❌ Preflight /admin/verify-password bad code: $ADMIN_OPT_CODE"; exit 1; fi

# Check /v1/projects endpoints
echo "\n== OPTIONS /v1/projects =="
PROJECTS_OPT_CODE=$(code "$API_BASE/v1/projects?recent=1" -X OPTIONS -H "Origin: $ORIGIN" -H "Access-Control-Request-Method: GET" -H "Access-Control-Request-Headers: content-type")

# Functional checks
PING_CODE=$(code "$API_BASE/ping")
HEALTH_CODE=$(code "$API_BASE/health")
LOGIN_POST=$(code "$API_BASE/login" -X POST -H "Origin: $ORIGIN" -H "Content-Type: application/json" --data '{"email":"x@y","password":"z"}')
PROJECTS_GET=$(code "$API_BASE/v1/projects?recent=1")

# Summary
echo "\n=== SMOKE SUMMARY ==="
echo "OPTIONS /login: $LOGIN_OPT_CODE"
echo "OPTIONS /admin/verify-password: $ADMIN_OPT_CODE"
echo "OPTIONS /v1/projects: $PROJECTS_OPT_CODE"
echo "POST /login: $LOGIN_POST"
echo "GET /ping: $PING_CODE"
echo "GET /health: $HEALTH_CODE"
echo "GET /v1/projects: $PROJECTS_GET"
echo "====================="
