#!/usr/bin/env bash
# ==============================================================================
# Stop OpcHub Frontend Web Server
# ==============================================================================
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

PID_FILE="$PROJECT_ROOT/frontend/frontend.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "[*] Stopping Frontend Server (PID: $PID)..."
        kill "$PID" || kill -9 "$PID"
        rm -f "$PID_FILE"
        echo "[SUCCESS] Frontend Server stopped."
        exit 0
    else
        echo "[*] Process $PID not running. Cleaning stale PID file."
        rm -f "$PID_FILE"
        exit 0
    fi
else
    pkill -f "uvicorn frontend.server:app" && echo "[SUCCESS] Frontend Server stopped via pattern." || echo "[*] No frontend server running."
fi
