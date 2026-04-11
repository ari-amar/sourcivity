#!/bin/bash
# Two-way auto-sync for sourcivity repo
# Pulls remote changes, then pushes local changes
cd /home/ubuntu/sourcivity || exit 1

# Pull remote changes first (rebase to keep history clean)
git pull --rebase origin main 2>/dev/null

# Check for local changes
if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
    exit 0
fi

git add -A
git commit -m "auto-sync $(date '+%Y-%m-%d %H:%M')"
git push origin main
