#!/usr/bin/env bash
# ==============================================================================
# Start OpcHub Backend Service (FastAPI + Unified Gateway + Microkernel)
# ==============================================================================
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

PORT=${BACKEND_PORT:-8000}
HOST=${BACKEND_HOST:-0.0.0.0}
PID_FILE="$PROJECT_ROOT/backend/backend.pid"
LOG_FILE="$PROJECT_ROOT/backend/backend.log"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "[*] Backend Server is already running with PID $PID on http://$HOST:$PORT"
        exit 0
    fi
fi

PYTHON_CMD="python3"
if [ -f "backend/.venv/bin/python3" ]; then
    PYTHON_CMD="backend/.venv/bin/python3"
fi

RELOAD_ARG=""
if [ "${BACKEND_RELOAD:-1}" = "1" ]; then
    RELOAD_ARG="--reload --reload-dir $PROJECT_ROOT/backend/src"
fi

echo "[*] Starting OpcHub Backend Server in background (hot-reload: ${BACKEND_RELOAD:-1})..."
PYTHONPATH="$PROJECT_ROOT/backend:$PROJECT_ROOT" setsid $PYTHON_CMD -m uvicorn src.main:app --host "$HOST" --port "$PORT" --app-dir "$PROJECT_ROOT/backend" $RELOAD_ARG > "$LOG_FILE" 2>&1 &
NEW_PID=$!
echo "$NEW_PID" > "$PID_FILE"

# Wait up to 10 seconds for service to become ready
for i in {1..20}; do
    if curl --noproxy '*' -s "http://127.0.0.1:$PORT/health" | grep -q -E "ok|UP|healthy"; then
        echo "[SUCCESS] Backend Server started successfully on http://127.0.0.1:$PORT (PID: $NEW_PID)"
        exit 0
    fi
    sleep 0.5
done

echo "[WARN] Backend launched, checking logs:"
cat "$LOG_FILE"
