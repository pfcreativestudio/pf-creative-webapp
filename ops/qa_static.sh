#!/usr/bin/env bash
set -euo pipefail

echo "=== PF System API - Static QA Audit ==="
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

FAILED=0
WARNINGS=0

# Helper functions
fail() {
    echo -e "${RED}❌ FAIL:${NC} $1"
    FAILED=$((FAILED + 1))
}

warn() {
    echo -e "${YELLOW}⚠️  WARN:${NC} $1"
    WARNINGS=$((WARNINGS + 1))
}

pass() {
    echo -e "${GREEN}✅ PASS:${NC} $1"
}

# 1. Check for hard-coded API domains
echo "1. Checking for hard-coded API domains..."
if grep -RIn \
  --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=ops \
  --exclude=vercel.json \
  --include='*.js' --include='*.ts' --include='*.jsx' --include='*.tsx' --include='*.html' --include='*.css' \
  "https://pfsystem-api-" . ; then
  fail "Found hard-coded Cloud Run API domain(s). Refactor to use apiFetch/getApiBase."
else
  pass "No hard-coded API domains found"
fi

# Check for any other hardcoded run.app domains (excluding vercel.json)
if grep -RIn \
  --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=ops \
  --exclude=vercel.json \
  --include='*.js' --include='*.ts' --include='*.jsx' --include='*.tsx' --include='*.html' --include='*.css' \
  "https://.*\.run\.app" . ; then
  fail "Found other hard-coded Cloud Run domains. Refactor to use runtime configuration"
else
  pass "No other hardcoded Cloud Run domains found"
fi

echo

# 2. Check runtime-config.js inclusion and ordering
echo "2. Checking runtime-config.js inclusion and ordering..."

HTML_FILES=(
    "login.html"
    "register.html" 
    "chatroom.html"
    "admin.html"
    "dashboard.html"
    "pricing.html"
    "payment-success.html"
    "index.html"
    "privacy.html"
)

for file in "${HTML_FILES[@]}"; do
    if [[ ! -f "$file" ]]; then
        warn "HTML file $file not found"
        continue
    fi
    
    # Check if runtime-config.js is included
    if ! grep -q '<script src="runtime-config.js">' "$file"; then
        fail "$file: Missing runtime-config.js script inclusion"
        continue
    fi
    
    # Check if it's in head section
    if ! awk '/<head>/,/<\/head>/' "$file" | grep -q 'runtime-config.js'; then
        fail "$file: runtime-config.js not in <head> section"
        continue
    fi
    
    # Check for duplicate inclusion
    count=$(grep -c 'runtime-config.js' "$file")
    if [[ $count -gt 1 ]]; then
        fail "$file: runtime-config.js included $count times (should be once)"
        continue
    fi
    
    # Check if it's before other scripts that might call API
    head_content=$(awk '/<head>/,/<\/head>/' "$file")
    runtime_line=$(echo "$head_content" | grep -n 'runtime-config.js' | cut -d: -f1)
    
    # Check if there are any script tags before runtime-config.js that might call API
    script_before=$(echo "$head_content" | head -n $((runtime_line - 1)) | grep -c '<script' || echo "0")
    if [[ $script_before -gt 0 ]]; then
        warn "$file: runtime-config.js not at the very top of <head> (after $script_before other script tags)"
    fi
    
    pass "$file: runtime-config.js properly included in <head>"
done

echo

# 3. Check apiFetch usage vs direct fetch calls
echo "3. Checking apiFetch usage..."

# Find direct fetch calls to API endpoints
API_PATHS=("/login" "/get-user-status" "/v1/" "/admin/" "/create-bill" "/register" "/activity/log")
for path in "${API_PATHS[@]}"; do
    # Look for fetch calls that might bypass apiFetch
    if grep -rIn \
      --exclude-dir=ops --exclude-dir=.git --exclude-dir=.venv \
      --exclude="*.md" \
      --include='*.js' --include='*.ts' --include='*.jsx' --include='*.tsx' --include='*.html' \
      "fetch.*$path" . ; then
        warn "Found potential direct fetch calls to $path. Ensure these use apiFetch()"
    fi
done

# Check for fetch calls with absolute URLs
if grep -rIn \
  --exclude-dir=ops --exclude-dir=.git --exclude-dir=.venv \
  --exclude="*.md" \
  --include='*.js' --include='*.ts' --include='*.jsx' --include='*.tsx' --include='*.html' \
  'fetch.*"http' . ; then
    warn "Found fetch calls with absolute URLs. These should use apiFetch() with relative paths"
else
    pass "No fetch calls with absolute URLs found"
fi

echo

# 4. Check CSP duplication
echo "4. Checking CSP duplication..."

# Check for meta CSP tags
META_CSP_FILES=()
while IFS= read -r -d '' file; do
    META_CSP_FILES+=("$file")
done < <(grep -rIl --exclude-dir=ops --exclude-dir=.git --exclude="*.md" 'http-equiv="Content-Security-Policy"' . 2>/dev/null || true)

if [[ ${#META_CSP_FILES[@]} -gt 0 ]]; then
    warn "Found meta CSP tags in: ${META_CSP_FILES[*]}"
    warn "Since vercel.json provides CSP headers, consider removing meta tags to avoid conflicts"
else
    pass "No meta CSP tags found (good - using vercel.json headers only)"
fi

echo

# 5. Check CORS headers vs frontend usage
echo "5. Checking CORS headers configuration..."

# Extract allow_headers from main.py
ALLOW_HEADERS=$(grep -A 10 "allow_headers" main.py | grep -o '"[^"]*"' | tr -d '"' | tr '\n' ' ')

# Check for common headers that should be allowed
REQUIRED_HEADERS=("Authorization" "Content-Type" "X-Admin-Password" "X-Requested-With")
for header in "${REQUIRED_HEADERS[@]}"; do
    if echo "$ALLOW_HEADERS" | grep -q "$header"; then
        pass "CORS allows header: $header"
    else
        fail "CORS missing required header: $header"
    fi
done

# Check if supports_credentials is True
if grep -q "supports_credentials=True" main.py; then
    pass "CORS supports credentials enabled"
else
    fail "CORS supports_credentials not enabled"
fi

# Check for wildcard origin
if grep -q "Access-Control-Allow-Origin: \*" main.py; then
    fail "Found wildcard CORS origin - security risk"
else
    pass "No wildcard CORS origin found"
fi

echo

# 6. Check credentials mode in apiFetch
echo "6. Checking credentials mode configuration..."

if grep -q 'credentials: "include"' api.js; then
    pass "apiFetch sets credentials: include"
else
    fail "apiFetch missing credentials: include"
fi

echo

# Summary
echo "=== AUDIT SUMMARY ==="
if [[ $FAILED -eq 0 ]]; then
    echo -e "${GREEN}🎉 ALL CHECKS PASSED${NC}"
    exit 0
else
    echo -e "${RED}❌ $FAILED checks failed${NC}"
    if [[ $WARNINGS -gt 0 ]]; then
        echo -e "${YELLOW}⚠️  $WARNINGS warnings${NC}"
    fi
    exit 1
fi
