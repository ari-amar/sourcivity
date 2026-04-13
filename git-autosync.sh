#!/bin/bash
# Two-way auto-sync for sourcivity repo
# Pulls remote changes (restarts servers if code changed), then pushes local changes
cd /home/ubuntu/sourcivity || exit 1

BEFORE=$(git rev-parse HEAD 2>/dev/null)

# Pull remote changes first (rebase to keep history clean)
git pull --rebase origin main 2>/dev/null

AFTER=$(git rev-parse HEAD 2>/dev/null)

# If remote had new commits, restart all customer servers
if [ "$BEFORE" != "$AFTER" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Pulled new changes, restarting servers..."
    for c in demo; do
        bash /home/ubuntu/customers/start.sh "$c" >> /tmp/sourcivity-restart.log 2>&1
    done
    # Restart dev instance
    DEV_PID=$(pgrep -f "python3 server.py" | grep -v "$(pgrep -f 'ENV_FILE=')" | head -1)
    [ -n "$DEV_PID" ] && kill "$DEV_PID" 2>/dev/null
    sleep 1
    nohup python3 server.py > /tmp/sourcivity-dev.log 2>&1 &
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] All servers restarted."
fi

# Check for local changes
if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
    exit 0
fi

git add -A
git commit -m "auto-sync $(date '+%Y-%m-%d %H:%M')"
git push origin main
