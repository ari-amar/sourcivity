#!/bin/bash
# Usage: ./start.sh <customer_name>
# Example: ./start.sh anna
#
# Starts a Sourcivity instance for the given customer using their .env
# All customers share the same sourcivity codebase at /home/ubuntu/sourcivity

CUSTOMER="$1"
if [ -z "$CUSTOMER" ]; then
  echo "Usage: $0 <customer_name>"
  echo "Available customers:"
  ls -d /home/ubuntu/customers/*/  2>/dev/null | xargs -I{} basename {}
  exit 1
fi

CUSTOMER_DIR="/home/ubuntu/customers/$CUSTOMER"
ENV_FILE="$CUSTOMER_DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
  echo "Error: No .env found at $ENV_FILE"
  exit 1
fi

LOG_FILE="/tmp/sourcivity-${CUSTOMER}.log"

# Kill existing instance using .pid file, then port as fallback
PID_FILE="$CUSTOMER_DIR/.pid"
if [ -f "$PID_FILE" ]; then
  OLD_PID=$(cat "$PID_FILE")
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Stopping existing instance (pid $OLD_PID)..."
    kill "$OLD_PID" 2>/dev/null
    sleep 1
    # Force kill if still alive
    kill -0 "$OLD_PID" 2>/dev/null && kill -9 "$OLD_PID" 2>/dev/null
  fi
fi
# Fallback: kill anything on the port
PORT=$(grep SERVE_PORT "$ENV_FILE" | cut -d= -f2)
EXISTING=$(lsof -ti:"$PORT" 2>/dev/null)
if [ -n "$EXISTING" ]; then
  echo "Killing process on port $PORT (pid $EXISTING)..."
  kill $EXISTING 2>/dev/null
  sleep 1
fi

echo "Starting Sourcivity for customer: $CUSTOMER"
echo "  .env:      $ENV_FILE"
echo "  Log:       $LOG_FILE"

cd /home/ubuntu/sourcivity
ENV_FILE="$ENV_FILE" nohup python3 server.py > "$LOG_FILE" 2>&1 &
NEW_PID=$!
echo $NEW_PID > "$CUSTOMER_DIR/.pid"
sleep 2

# Verify it started
PORT=$(grep SERVE_PORT "$ENV_FILE" | cut -d= -f2)
if curl -s --max-time 3 "http://localhost:${PORT}/api/config" > /dev/null 2>&1; then
  echo "  Running on port $PORT (pid $NEW_PID) ✓"
else
  echo "  WARNING: Server may not have started. Check $LOG_FILE"
fi
