#!/usr/bin/env bash
# ==============================================================================
# Start OpcHub Frontend Web Server (Port 3000)
# ==============================================================================
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

PORT=${FRONTEND_PORT:-3000}
HOST=${FRONTEND_HOST:-0.0.0.0}
PID_FILE="$PROJECT_ROOT/frontend/frontend.pid"
LOG_FILE="$PROJECT_ROOT/frontend/frontend.log"

mkdir -p "$PROJECT_ROOT/frontend"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "[*] Frontend Server is already running with PID $PID on http://$HOST:$PORT"
        exit 0
    fi
fi

if [ ! -d "$PROJECT_ROOT/frontend/dist" ]; then
    echo "[*] Building Vue 3 frontend application with Vite..."
    cd "$PROJECT_ROOT/frontend"
    node node_modules/vite/bin/vite.js build
    cd "$PROJECT_ROOT"
fi

PYTHON_CMD="python3"
if [ -f "backend/.venv/bin/python3" ]; then
    PYTHON_CMD="backend/.venv/bin/python3"
fi

echo "[*] Starting OpcHub Frontend Web Server in background..."
PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/backend" setsid $PYTHON_CMD -m uvicorn frontend.server:app --host "$HOST" --port "$PORT" > "$LOG_FILE" 2>&1 &
NEW_PID=$!
echo "$NEW_PID" > "$PID_FILE"

# Wait up to 10 seconds for service to become ready
for i in {1..20}; do
    if curl --noproxy '*' -s "http://127.0.0.1:$PORT/health" | grep -q "UP"; then
        echo "[SUCCESS] Frontend Server started successfully on http://127.0.0.1:$PORT (PID: $NEW_PID)"
        exit 0
    fi
    sleep 0.5
done

echo "[WARN] Frontend launched, checking logs:"
cat "$LOG_FILE"
