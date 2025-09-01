$ErrorActionPreference = "Stop"

function Get-OwnerRepo {
  $origin = git remote get-url origin 2>$null
  if (-not $origin) { return $null }
  $norm = $origin -replace "^git@github.com:", "https://github.com/"
  $norm = $norm -replace "\.git$", ""
  return ($norm -replace "^https://github.com/", "")
}

if (-not (git rev-parse --is-inside-work-tree 2>$null)) {
  git init
}

git add -A
$p = (git diff --cached --quiet) ; if (-not $?) { git commit -m "chore(ci): QA workflow + regression runners + docs" }

git branch -M main | Out-Null

$origin = git remote get-url origin 2>$null
if (-not $origin) {
  Write-Host "No origin remote. Trying GitHub CLI (gh)..." -ForegroundColor Yellow
  $repoName = (Split-Path -Leaf (Get-Location)).ToLower().Replace(" ","-")
  if (Get-Command gh -ErrorAction SilentlyContinue) {
    gh repo create $repoName --private --source=. --remote=origin --push
  } else {
    Write-Host "gh not found. Create repo manually then:" -ForegroundColor Red
    Write-Host "git remote add origin https://github.com/<owner>/$repoName.git"
    Write-Host "git push -u origin main"
    exit 2
  }
}

git push -u origin main | Out-Null

$ownerRepo = Get-OwnerRepo
Write-Host "--------------------------------------------------" -ForegroundColor Green
Write-Host "PUSH COMPLETE → $(git remote get-url origin)" -ForegroundColor Green
Write-Host "GitHub Actions (QA) workflow:" -ForegroundColor Green
Write-Host "https://github.com/$ownerRepo/actions/workflows/qa.yml" -ForegroundColor Green
Write-Host "--------------------------------------------------" -ForegroundColor Green
