#!/usr/bin/env bash
# ==============================================================================
# Start Aliyun Content Moderation HTTP Mock Server
# ==============================================================================
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

PORT=${MOCK_PORT:-8099}
HOST=${MOCK_HOST:-0.0.0.0}
PID_FILE="$PROJECT_ROOT/mock_server/mock_server.pid"
LOG_FILE="$PROJECT_ROOT/mock_server/mock_server.log"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "[*] Mock Server is already running with PID $PID on http://$HOST:$PORT"
        exit 0
    fi
fi

PYTHON_CMD="python3"
if [ -f "backend/.venv/bin/python3" ]; then
    PYTHON_CMD="backend/.venv/bin/python3"
fi

echo "[*] Starting Aliyun Content Moderation Mock Server in background..."
PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/backend" setsid $PYTHON_CMD -m uvicorn mock_server.app:app --host "$HOST" --port "$PORT" > "$LOG_FILE" 2>&1 &
NEW_PID=$!
echo "$NEW_PID" > "$PID_FILE"

# Wait up to 5 seconds for service to become ready
for i in {1..10}; do
    if curl --noproxy '*' -s "http://127.0.0.1:$PORT/health" | grep -q "UP"; then
        echo "[SUCCESS] Mock Server started successfully on http://127.0.0.1:$PORT (PID: $NEW_PID)"
        exit 0
    fi
    sleep 0.5
done

echo "[WARN] Server launched, checking logs:"
cat "$LOG_FILE"
