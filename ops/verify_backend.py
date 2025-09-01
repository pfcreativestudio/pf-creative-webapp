#!/usr/bin/env python3
"""
Simple backend verification script that checks CORS configuration
without requiring external dependencies.
"""

import sys
import os
import re

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_cors_config():
    """Check CORS configuration in main.py"""
    print("=== Backend CORS Configuration Check ===\n")
    
    passed = 0
    failed = 0
    
    try:
        with open('main.py', 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ FAIL: Could not read main.py: {e}")
        return False
    
    # Check 1: supports_credentials=True
    if 'supports_credentials=True' in content:
        print("✅ PASS: CORS supports_credentials enabled")
        passed += 1
    else:
        print("❌ FAIL: CORS supports_credentials not enabled")
        failed += 1
    
    # Check 2: Required headers in allow_headers
    required_headers = ['Authorization', 'Content-Type', 'X-Admin-Password', 'X-Requested-With']
    allow_headers_match = re.search(r'allow_headers=\[(.*?)\]', content, re.DOTALL)
    
    if allow_headers_match:
        allow_headers_text = allow_headers_match.group(1)
        for header in required_headers:
            if header in allow_headers_text:
                print(f"✅ PASS: CORS allows header: {header}")
                passed += 1
            else:
                print(f"❌ FAIL: CORS missing required header: {header}")
                failed += 1
    else:
        print("❌ FAIL: Could not find allow_headers configuration")
        failed += 1
    
    # Check 3: No wildcard origins
    if 'Access-Control-Allow-Origin: *' in content or '"*"' in content.replace('r"/*"', '').replace("'*'", ''):
        print("❌ FAIL: Found potential wildcard CORS origin - security risk")
        failed += 1
    else:
        print("✅ PASS: No wildcard CORS origin found")
        passed += 1
    
    # Check 4: FRONTEND_BASE_URLS support
    if 'FRONTEND_BASE_URLS' in content:
        print("✅ PASS: FRONTEND_BASE_URLS environment variable supported")
        passed += 1
    else:
        print("❌ FAIL: FRONTEND_BASE_URLS environment variable not found")
        failed += 1
    
    # Check 5: Healthz endpoint returns status: ok
    healthz_match = re.search(r'@app\.route\("/healthz".*?def.*?\n(.*?)\n.*?@app\.route', content, re.DOTALL)
    if healthz_match and '"status": "ok"' in healthz_match.group(1):
        print("✅ PASS: /healthz endpoint returns proper status")
        passed += 1
    elif '"status": "ok"' in content:
        print("✅ PASS: /healthz endpoint returns proper status")
        passed += 1
    else:
        print("❌ FAIL: /healthz endpoint does not return proper status")
        failed += 1
    
    print(f"\n=== BACKEND CHECK SUMMARY ===")
    if failed == 0:
        print(f"🎉 ALL {passed} BACKEND CHECKS PASSED")
        return True
    else:
        print(f"❌ {failed} check(s) failed, {passed} passed")
        return False

def check_api_wrapper():
    """Check that apiFetch wrapper is properly configured"""
    print("\n=== API Wrapper Check ===\n")
    
    try:
        with open('api.js', 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ FAIL: Could not read api.js: {e}")
        return False
    
    passed = 0
    failed = 0
    
    # Check credentials: include
    if 'credentials: "include"' in content:
        print("✅ PASS: apiFetch sets credentials: include")
        passed += 1
    else:
        print("❌ FAIL: apiFetch missing credentials: include")
        failed += 1
    
    # Check mode: cors
    if 'mode: "cors"' in content:
        print("✅ PASS: apiFetch sets mode: cors")
        passed += 1
    else:
        print("❌ FAIL: apiFetch missing mode: cors")
        failed += 1
    
    # Check function exists
    if 'function apiFetch' in content or 'apiFetch =' in content:
        print("✅ PASS: apiFetch function defined")
        passed += 1
    else:
        print("❌ FAIL: apiFetch function not found")
        failed += 1
    
    if failed == 0:
        print(f"🎉 ALL {passed} API WRAPPER CHECKS PASSED")
        return True
    else:
        print(f"❌ {failed} check(s) failed, {passed} passed")
        return False

if __name__ == "__main__":
    cors_ok = check_cors_config()
    api_ok = check_api_wrapper()
    
    if cors_ok and api_ok:
        print("\n🎉 ALL BACKEND VERIFICATIONS PASSED")
        sys.exit(0)
    else:
        print("\n❌ BACKEND VERIFICATION FAILED")
        sys.exit(1)
