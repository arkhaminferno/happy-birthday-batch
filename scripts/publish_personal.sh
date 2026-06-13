#!/usr/bin/env bash
# Publish batch_birthday to personal GitHub (arkhaminferno).
set -euo pipefail

REPO_NAME="${1:-happy-birthday-batch}"
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if ! gh auth status >/dev/null 2>&1; then
  echo "Run: gh auth login"
  echo "Then re-run: ./scripts/publish_personal.sh"
  exit 1
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  git remote add origin "git@github-personal:arkhaminferno/${REPO_NAME}.git"
fi

if ! git rev-parse HEAD >/dev/null 2>&1; then
  git add -A
  git commit -m "Add Happy Birthday batch template pipeline"
fi

if ! git push -u origin main 2>/dev/null; then
  gh repo create "$REPO_NAME" \
    --public \
    --description "Happy Birthday [Name] batch template for ACE-Step 1.5" \
    --source=. \
    --remote=origin \
    --push
fi

echo "Published: https://github.com/arkhaminferno/${REPO_NAME}"
