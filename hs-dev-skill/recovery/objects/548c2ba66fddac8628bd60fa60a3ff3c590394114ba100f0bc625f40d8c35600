#!/usr/bin/env bash
# ==============================================================================
# Start All OpcHub Services: Mock Server, Backend Service, Frontend Web Console
# ==============================================================================
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=================================================================="
echo "  🚀 正在启动 OpcHub 全套服务（Mock 服务、后端核心、前端工作台）..."
echo "=================================================================="

# 1. 启动 Mock 服务
"$PROJECT_ROOT/scripts/start_mock_server.sh"

# 2. 启动 后端服务
"$PROJECT_ROOT/scripts/start_backend.sh"

# 3. 启动 前端服务
"$PROJECT_ROOT/scripts/start_frontend.sh"

echo ""
echo "=================================================================="
echo "  🎉 OpcHub 全套服务已全部启动就绪！欢迎进行验收测试！"
echo "=================================================================="
echo "  🌐 前端独立控制台 : http://localhost:3000/"
echo "  🌐 后端可视化工作台: http://localhost:8000/console"
echo "  📖 API 交互文档   : http://localhost:8000/docs"
echo "  🔍 统一网关分发入口: http://localhost:8000/api/welcom/opc_world"
echo "  🤖 统一 Mock 服务  : http://localhost:8099/health"
echo "------------------------------------------------------------------"
echo "  停止所有服务: ./scripts/stop_all.sh"
echo "=================================================================="
