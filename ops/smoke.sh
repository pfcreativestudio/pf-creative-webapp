#!/usr/bin/env bash
set -euo pipefail

API_BASE="${1:-}"
ORIGIN="${2:-https://pfcreativeaistudio.vercel.app}"

if [[ -z "$API_BASE" ]]; then
  echo "Usage: $0 <API_BASE> [ORIGIN]"
  echo "Example: $0 https://pfsystem-api-XXXX.a.run.app https://pfcreativeaistudio.vercel.app"
  exit 1
fi

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
echo "== GET /healthz =="
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE/healthz")
echo "Status: $HEALTH_STATUS"
if [[ "$HEALTH_STATUS" != "200" ]]; then
  echo "❌ Health check failed with status $HEALTH_STATUS"
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
echo "== GET /v1/director/veo-3-prompt (expect 200 or 400, must reach server) =="
DIRECTOR_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$API_BASE/v1/director/veo-3-prompt" \
  -H "Origin: $ORIGIN")
echo "Status: $DIRECTOR_STATUS"
if [[ "$DIRECTOR_STATUS" -lt 200 || "$DIRECTOR_STATUS" -ge 500 ]]; then
  echo "❌ Director endpoint failed with status $DIRECTOR_STATUS"
  exit 1
fi

echo
echo "✅ All smoke tests passed!"
echo
echo "=== SMOKE SUMMARY ==="
echo "SERVICE_URL: $API_BASE"
echo "OPTIONS /login: $PREFLIGHT_STATUS"
echo "GET /healthz: $HEALTH_STATUS"
echo "POST /login: $LOGIN_STATUS"
echo "GET /v1/director/veo-3-prompt: $DIRECTOR_STATUS"
echo "====================="
echo
echo "== Check Cloud Run logs for POST /login request details =="
