# PF System API - Production Runbook

## Environment Variables

### Backend (Cloud Run)

Set the following environment variable on your Cloud Run service `pfsystem-api`:

```bash
FRONTEND_BASE_URLS=https://pfcreativeaistudio.vercel.app,https://your-preview-domain.vercel.app
```

**Important**: Use comma-separated values for multiple domains. Include:
- Your production Vercel domain
- All Vercel preview domains you use
- Any custom domains

### Frontend (Vercel)

Set ONE of these environment variables in Vercel Project Settings → Environment Variables:

**Option 1:**
```
NEXT_PUBLIC_API_BASE=https://pfsystem-api-XXXX.a.run.app
```

**Option 2:**
```
VITE_API_BASE=https://pfsystem-api-XXXX.a.run.app
```

**Option 3:** Inject via meta tag in HTML (set at build time):
```html
<meta name="pf:apiBase" content="https://pfsystem-api-XXXX.a.run.app">
```

## Smoke Testing

### Prerequisites
- `curl` installed
- `jq` installed (optional, for prettier JSON output)
- Your Cloud Run service URL

### Run Smoke Tests

```bash
# Test from production domain
bash ops/smoke.sh https://pfsystem-api-XXXX.a.run.app https://pfcreativeaistudio.vercel.app

# Test from localhost
bash ops/smoke.sh https://pfsystem-api-XXXX.a.run.app http://localhost:3000

# Test from preview domain
bash ops/smoke.sh https://pfsystem-api-XXXX.a.run.app https://your-preview.vercel.app
```

### Expected Results

1. **OPTIONS /login**: Should return 200/204 with `Access-Control-Allow-Origin` header
2. **GET /healthz**: Should return 200 with `{"status":"ok"}`
3. **POST /login**: Should reach server (check Cloud Run logs for "--- LOGIN REQUEST ---")

### Verify in Cloud Run Logs

Look for these log entries in Cloud Run:
```
--- REQUEST --- OPTIONS /login | Origin: https://pfcreativeaistudio.vercel.app
--- REQUEST --- POST /login | Origin: https://pfcreativeaistudio.vercel.app
--- LOGIN REQUEST --- Method: POST, Origin: https://pfcreativeaistudio.vercel.app
```

## Code Quality Checks

### Scan for Hardcoded Domains

```bash
bash ops/scan-hardcoded.sh
```

This should pass with no hardcoded API domains found.

## Troubleshooting

### CORS Issues
- Verify `FRONTEND_BASE_URLS` includes your domain
- Check Cloud Run logs for CORS errors
- Ensure frontend loads `runtime-config.js` before any API calls

### API Base Resolution
- Check browser console for "PF runtime not initialized" errors
- Verify environment variables are set correctly
- Check meta tag injection if using build-time injection

### Login Not Working
- Verify OPTIONS preflight returns 200/204
- Check Cloud Run logs for request details
- Ensure `credentials: "include"` is set in fetch calls
