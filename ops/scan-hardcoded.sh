#!/usr/bin/env bash
set -euo pipefail

echo "Scanning for hardcoded Cloud Run API domains..."

if grep -RIn --exclude-dir=node_modules --exclude-dir=.git "https://pfsystem-api-" . ; then
  echo "ERROR: Found hard-coded API domain(s). Refactor to use apiFetch/getApiBase."
  exit 1
fi

echo "OK: No hard-coded Cloud Run API domains found."
echo "All API calls should use apiFetch() or getApiBase() from runtime-config.js"
