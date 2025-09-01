# Release Notes - v1.0.0-rc.1

## What Changed

### 🚀 New Features
- **Complete QA Suite**: Frontend, backend, and static analysis testing
- **CI/CD Pipeline**: GitHub Actions for automated quality assurance
- **Runtime Configuration**: Dynamic API base configuration
- **Centralized API Handling**: apiFetch wrapper for all API calls

### 🔧 Improvements
- **Script Loading Order**: Fixed runtime-config.js loading sequence
- **CORS Hardening**: Specific header allowlists and security improvements
- **Code Deduplication**: Removed duplicate script includes
- **Cross-platform Testing**: Bash and PowerShell regression runners

### 🛡️ Security Enhancements
- **CSP Headers**: Content Security Policy implementation
- **CORS Configuration**: Restricted origins and header validation
- **Runtime Injection**: Secure API configuration at deployment

## Quick QA Testing

### One-Command Local Regression

**On Linux/macOS:**
```bash
bash ops/regress.sh
```

**On Windows PowerShell:**
```powershell
powershell -ExecutionPolicy Bypass -File ops/regress.ps1
```

**Note for Windows Users:** Ensure "C:\Program Files\Git\bin" is in your PATH so bash is available in PowerShell.

### Individual QA Commands

- **Frontend**: `npm run qa:frontend`
- **Static**: `bash ops/qa_static.sh`
- **Backend**: `pytest -q`
- **Hardcoded Scan**: `bash ops/scan-hardcoded.sh`

## Post-Deploy Go/No-Go Checklist

### ✅ Must Pass (Go)
- [ ] Site opens without errors
- [ ] DevTools Network shows OPTIONS then POST /login
- [ ] No CSP violations in console
- [ ] API pages load runtime-config.js before any other scripts
- [ ] All QA checks pass locally: `bash ops/regress.sh`

### ❌ Must Fail (No-Go)
- [ ] Console shows CORS errors
- [ ] CSP violations in browser console
- [ ] Script loading errors or race conditions
- [ ] API calls fail with 4xx/5xx errors
- [ ] QA suite reports failures

### 🔍 Verification Steps

1. **Open site in browser**
2. **Open DevTools → Console**
3. **Check for any error messages**
4. **Navigate to login page**
5. **Monitor Network tab for API calls**
6. **Verify runtime-config.js loads first**
7. **Run local QA suite**

## Rollback Plan

If issues are detected:
1. Revert to previous version
2. Run full QA suite on rollback version
3. Document issues found
4. Fix and re-test before next deployment

## Support

For deployment issues or questions:
- Check CI/CD pipeline status
- Review QA test results
- Consult release engineer
- Refer to CHANGELOG.md for detailed changes
