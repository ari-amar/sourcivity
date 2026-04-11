#!/bin/bash
# Auto-commit and push any changes in the sourcivity repo
cd /home/ubuntu/sourcivity || exit 1

# Check for changes
if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
    exit 0
fi

git add -A
git commit -m "auto-sync $(date '+%Y-%m-%d %H:%M')"
git push origin main
