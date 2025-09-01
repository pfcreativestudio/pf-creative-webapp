#!/usr/bin/env bash
set -euo pipefail

echo "== Frontend checks =="
npm run -s qa:frontend

echo
echo "== Static QA =="
bash ops/qa_static.sh

echo
echo "== Backend tests =="
pytest -q

echo
echo "== Hardcoded scan =="
bash ops/scan-hardcoded.sh

echo
echo "ALL CHECKS PASSED"
