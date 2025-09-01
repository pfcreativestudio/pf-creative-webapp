#!/usr/bin/env bash
set -euo pipefail

# 1) Ensure git repo & initial commit
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git init
fi

# Stage everything (excluding what .gitignore covers)
git add -A
if ! git diff --cached --quiet; then
  git commit -m "chore(ci): QA workflow + regression runners + docs"
fi

# 2) Ensure main branch
git branch -M main || true

# 3) Determine if origin exists
if git remote get-url origin >/dev/null 2>&1; then
  echo "✓ Found existing origin remote"
else
  echo "ℹ No origin remote. Attempting to create with GitHub CLI (gh)..."
  # Determine repo name from folder (kebab-case)
  repo_name="$(basename "$(pwd)" | tr '[:upper:]' '[:lower:]' | sed 's/ /-/g')"
  if command -v gh >/dev/null 2>&1; then
    # Creates under the authenticated user's account
    gh repo create "$repo_name" --private --source=. --remote=origin --push
  else
    echo "✖ gh (GitHub CLI) not installed or not on PATH."
    echo "-> Please create a GitHub repo manually and set it as origin, e.g.:"
    echo "   git remote add origin https://github.com/<owner>/$repo_name.git"
    echo "   git push -u origin main"
    exit 2
  fi
fi

# 4) Push (idempotent)
git push -u origin main || true

# 5) Derive owner/repo from origin and print Actions link
origin_url="$(git remote get-url origin)"
# Normalize to https for parsing
norm="$origin_url"
norm="${norm/git@github.com:/https://github.com/}"
norm="${norm%.git}"
owner_repo="${norm#https://github.com/}"

echo "--------------------------------------------------"
echo "PUSH COMPLETE → $origin_url"
echo "GitHub Actions (QA) workflow:"
echo "https://github.com/${owner_repo}/actions/workflows/qa.yml"
echo "--------------------------------------------------"
