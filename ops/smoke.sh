#!/usr/bin/env bash
set -euo pipefail

API_BASE="${1:-}"
ORIGIN="${2:-https://pfcreativeaistudio.vercel.app}"

if [[ -z "$API_BASE" ]]; then
  echo "Usage: $0 <API_BASE> [ORIGIN]"
  echo "Example: $0 https://pfsystem-api-XXXX.a.run.app https://pfcreativeaistudio.vercel.app"
  exit 1
fi

# Helper to print just status codes
code() { local URL="$1"; shift; curl -s -o /dev/null -w "%{http_code}" "$@" "$URL"; }

echo "== Preflight OPTIONS /login from Origin: $ORIGIN =="
PREFLIGHT_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X OPTIONS "$API_BASE/login" \
  -H "Origin: $ORIGIN" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type")
echo "Status: $PREFLIGHT_STATUS"
if [[ "$PREFLIGHT_STATUS" != "200" && "$PREFLIGHT_STATUS" != "204" ]]; then
  echo "❌ Preflight failed with status $PREFLIGHT_STATUS"
  exit 1
fi

echo
echo "== GET /healthz (fallback to /ping) =="
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE/healthz")
PING_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE/ping")
echo "Status: /healthz=$HEALTH_STATUS /ping=$PING_STATUS"
if [[ "$HEALTH_STATUS" != "200" && "$PING_STATUS" != "200" ]]; then
  echo "❌ Health check failed: /healthz=$HEALTH_STATUS, /ping=$PING_STATUS"
  exit 1
fi

echo
echo "== Attempt dummy POST /login (expect 2xx/4xx but MUST reach server) =="
LOGIN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API_BASE/login" \
  -H "Origin: $ORIGIN" \
  -H "Content-Type: application/json" \
  --data '{"email":"demo@example.com","password":"fake"}')
echo "Status: $LOGIN_STATUS"
if [[ "$LOGIN_STATUS" -lt 200 || "$LOGIN_STATUS" -ge 500 ]]; then
  echo "❌ Login request failed with status $LOGIN_STATUS"
  exit 1
fi

echo
echo "== Director veo-3-prompt (OPTIONS then POST) =="
DIR_OPT_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X OPTIONS "$API_BASE/v1/director/veo-3-prompt" \
  -H "Origin: $ORIGIN" -H "Access-Control-Request-Method: POST" -H "Access-Control-Request-Headers: content-type,authorization")
echo "OPTIONS status: $DIR_OPT_STATUS"
DIR_POST_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API_BASE/v1/director/veo-3-prompt" \
  -H "Origin: $ORIGIN" -H "Content-Type: application/json" --data '{"prompt":"hi","history":[]}')
echo "POST status: $DIR_POST_STATUS"
if [[ "$DIR_POST_STATUS" -ge 500 ]]; then
  echo "❌ Director POST failed with status $DIR_POST_STATUS"
  exit 1
fi

echo
# Compact summary with numeric codes
echo "=== SMOKE SUMMARY ==="
echo "SERVICE_URL: $API_BASE"
echo -n "OPTIONS /login: "; code "$API_BASE/login" -X OPTIONS -H "Origin: $ORIGIN" -H "Access-Control-Request-Method: POST" -H "Access-Control-Request-Headers: content-type"; echo

echo -n "GET /ping: "; code "$API_BASE/ping"; echo

echo -n "GET /health: "; code "$API_BASE/health"; echo

echo -n "GET /healthz: "; code "$API_BASE/healthz"; echo

echo -n "OPTIONS /v1/director/veo-3-prompt: "; code "$API_BASE/v1/director/veo-3-prompt" -X OPTIONS -H "Origin: $ORIGIN" -H "Access-Control-Request-Method: POST" -H "Access-Control-Request-Headers: content-type,authorization"; echo

echo -n "POST /v1/director/veo-3-prompt: "; code "$API_BASE/v1/director/veo-3-prompt" -X POST -H "Origin: $ORIGIN" -H "Content-Type: application/json" --data '{"prompt":"hi","history":[]}'; echo

echo -n "POST /login: "; code "$API_BASE/login" -X POST -H "Origin: $ORIGIN" -H "Content-Type: application/json" --data '{"email":"x@y","password":"z"}'; echo

echo "====================="
echo
echo "== Check Cloud Run logs for POST /login request details =="
