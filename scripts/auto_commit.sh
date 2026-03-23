#!/bin/bash
# Auto-commit script for Polymarket Agent
# Usage: bash scripts/auto_commit.sh [message]
# - Run manually: bash scripts/auto_commit.sh "my commit message"
# - Hourly via Task Scheduler or cron

cd "$(dirname "$0")/.." || exit 1

MSG="${1:-Auto-commit $(date '+%Y-%m-%d %H:%M')}"

# Check for changes
if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
    echo "No changes to commit."
    exit 0
fi

git add -A
git commit -m "$MSG"
git push origin "$(git branch --show-current)" 2>/dev/null || true
echo "Committed and pushed: $MSG"
