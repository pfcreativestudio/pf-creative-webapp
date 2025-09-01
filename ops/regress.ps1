Write-Host "== Frontend checks ==" -ForegroundColor Cyan
node ops/check_frontend.mjs

Write-Host "`n== Static QA ==" -ForegroundColor Cyan
bash ops/qa_static.sh

Write-Host "`n== Backend tests ==" -ForegroundColor Cyan
pytest -q

Write-Host "`n== Hardcoded scan ==" -ForegroundColor Cyan
bash ops/scan-hardcoded.sh

Write-Host "`nALL CHECKS PASSED" -ForegroundColor Green
