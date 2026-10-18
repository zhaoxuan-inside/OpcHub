#!/usr/bin/env bash
# ==============================================================================
# Stop OpcHub Backend Service
# ==============================================================================
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

PID_FILE="$PROJECT_ROOT/backend/backend.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "[*] Stopping Backend Server (PID: $PID)..."
        kill "$PID" || kill -9 "$PID"
        rm -f "$PID_FILE"
        echo "[SUCCESS] Backend Server stopped."
        exit 0
    else
        echo "[*] Process $PID not running. Cleaning stale PID file."
        rm -f "$PID_FILE"
        exit 0
    fi
else
    pkill -f "uvicorn src.main:app" && echo "[SUCCESS] Backend Server stopped via pattern." || echo "[*] No backend server running."
fi
