#!/usr/bin/env bash
# ==============================================================================
# Stop Aliyun Content Moderation HTTP Mock Server
# ==============================================================================
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

PID_FILE="$PROJECT_ROOT/mock_server/mock_server.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "[*] Stopping Mock Server (PID: $PID)..."
        kill "$PID" || kill -9 "$PID"
        rm -f "$PID_FILE"
        echo "[SUCCESS] Mock Server stopped."
        exit 0
    else
        echo "[*] Process $PID not running. Cleaning stale PID file."
        rm -f "$PID_FILE"
        exit 0
    fi
else
    # Fallback to pkill if PID file does not exist
    pkill -f "uvicorn mock_server.app:app" && echo "[SUCCESS] Mock Server stopped via pattern." || echo "[*] No mock server running."
fi
