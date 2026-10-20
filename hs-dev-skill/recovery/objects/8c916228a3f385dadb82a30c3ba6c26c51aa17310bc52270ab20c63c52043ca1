#!/usr/bin/env bash
# ==============================================================================
# Stop All OpcHub Services: Frontend, Backend, Mock Server
# ==============================================================================
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=================================================================="
echo "  🛑 正在停止 OpcHub 所有服务..."
echo "=================================================================="

"$PROJECT_ROOT/scripts/stop_frontend.sh" || true
"$PROJECT_ROOT/scripts/stop_backend.sh" || true
"$PROJECT_ROOT/scripts/stop_mock_server.sh" || true

echo "=================================================================="
echo "  [SUCCESS] OpcHub 所有服务已安全停止。"
echo "=================================================================="
