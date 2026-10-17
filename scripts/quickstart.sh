#!/usr/bin/env bash
# ==============================================================================
# OpcHub: One-Click Quickstart & Container Management Script
# Designed for Super Individuals and Solo Makers (OPC)
# ==============================================================================
set -e

# Project root resolution
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Terminal formatting
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m' # No Color

print_banner() {
    echo -e "${BLUE}${BOLD}"
    echo "=================================================================="
    echo "  🚀 OpcHub: 一人公司(OPC)与超级个体全要素赋能平台即插即用启动器"
    echo "=================================================================="
    echo -e "${NC}"
}

ensure_env() {
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            echo -e "${YELLOW}[!] 未检测到 .env 配置文件，自动从 .env.example 复制生成...${NC}"
            cp .env.example .env
        else
            touch .env
        fi
    fi
    mkdir -p data
}

check_docker() {
    if command -v docker &> /dev/null; then
        return 0
    else
        return 1
    fi
}

start_docker() {
    print_banner
    ensure_env
    echo -e "${GREEN}[*] 正在启动 OpcHub 容器集群...${NC}"
    if docker compose version &> /dev/null; then
        docker compose up -d --build
    elif command -v docker-compose &> /dev/null; then
        docker-compose up -d --build
    else
        echo -e "${RED}[ERROR] 未检测到 Docker Compose，请先安装 Docker 或运行 './scripts/quickstart.sh local' 启动本地模式。${NC}"
        exit 1
    fi

    echo -e "${GREEN}[SUCCESS] OpcHub 服务已在后台成功启动！${NC}"
    echo -e "------------------------------------------------------------------"
    echo -e "  🌐 Web 可视化控制台 : ${BOLD}http://localhost:8000/${NC}"
    echo -e "  📖 API 交互文档     : ${BOLD}http://localhost:8000/docs${NC}"
    echo -e "  🔍 统一网关分发入口 : ${BOLD}http://localhost:8000/api/welcom/opc_world${NC}"
    echo -e "  💚 健康检查探针     : ${BOLD}http://localhost:8000/health${NC}"
    echo -e "------------------------------------------------------------------"
    echo -e "查看日志: ./scripts/quickstart.sh logs"
    echo -e "停止服务: ./scripts/quickstart.sh stop"
}

stop_docker() {
    echo -e "${YELLOW}[*] 正在停止 OpcHub 容器集群...${NC}"
    if docker compose version &> /dev/null; then
        docker compose down
    elif command -v docker-compose &> /dev/null; then
        docker-compose down
    fi
    echo -e "${GREEN}[SUCCESS] OpcHub 容器服务已安全停止。${NC}"
}

status_docker() {
    if docker compose version &> /dev/null; then
        docker compose ps
    elif command -v docker-compose &> /dev/null; then
        docker-compose ps
    fi
}

logs_docker() {
    if docker compose version &> /dev/null; then
        docker compose logs -f --tail=100
    elif command -v docker-compose &> /dev/null; then
        docker-compose logs -f --tail=100
    fi
}

start_local() {
    print_banner
    ensure_env
    echo -e "${GREEN}[*] 启动本地无容器轻量运行模式...${NC}"
    PYTHON_CMD="python3"
    if [ -f "$HOME/.virtualenvs/opchub/bin/python3" ]; then
        PYTHON_CMD="$HOME/.virtualenvs/opchub/bin/python3"
    elif [ -f "backend/.venv/bin/python3" ]; then
        PYTHON_CMD="backend/.venv/bin/python3"
    fi

    echo -e "${BLUE}[*] 使用 Python 解释器: ${PYTHON_CMD}${NC}"
    PYTHONPATH="$PROJECT_ROOT/backend:$PROJECT_ROOT" $PYTHON_CMD -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --app-dir "$PROJECT_ROOT/backend"
}

cmd="${1:-start}"
case "$cmd" in
    start)
        start_docker
        ;;
    stop)
        stop_docker
        ;;
    restart)
        stop_docker
        start_docker
        ;;
    status)
        status_docker
        ;;
    logs)
        logs_docker
        ;;
    local)
        start_local
        ;;
    help|--help|-h)
        print_banner
        echo "用法: ./scripts/quickstart.sh [start|stop|restart|status|logs|local]"
        echo "  start    : 构建并启动 Docker 容器 (默认)"
        echo "  stop     : 停止 Docker 容器"
        echo "  restart  : 重启容器"
        echo "  status   : 查看容器运行状态与健康度"
        echo "  logs     : 查看容器运行实时日志"
        echo "  local    : 使用本地 Python 虚拟环境直接启动 (无需 Docker)"
        ;;
    *)
        echo -e "${RED}[ERROR] 未知命令: $cmd${NC}"
        echo "运行 './scripts/quickstart.sh help' 查看帮助说明。"
        exit 1
        ;;
esac
