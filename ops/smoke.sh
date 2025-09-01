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
curl -i -X OPTIONS "$API_BASE/login" \
  -H "Origin: $ORIGIN" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type" | sed -n '1,30p'

echo
echo "== GET /healthz =="
curl -sf "$API_BASE/healthz" | jq . 2>/dev/null || curl -sf "$API_BASE/healthz"

echo
echo "== Attempt dummy POST /login (expect 2xx/4xx but MUST reach server) =="
curl -i -X POST "$API_BASE/login" \
  -H "Origin: $ORIGIN" \
  -H "Content-Type: application/json" \
  --data '{"email":"demo@example.com","password":"fake"}' | sed -n '1,30p'

echo
echo "== Test complete. Check Cloud Run logs for POST /login request =="
