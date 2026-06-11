#!/bin/bash
# ============================================================
# 启动 API 服务 — Coze Cloud Computer
# 用法: bash start_server.sh [端口号，默认8080]
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
PORT="${1:-8080}"

# 加载环境变量
if [ -f .env ]; then
    set -a; source .env; set +a
fi

# 检查依赖
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] python3 未安装，请先运行 bash setup_cloud.sh"
    exit 1
fi

if ! command -v node &>/dev/null; then
    echo "[ERROR] node 未安装，请先运行 bash setup_cloud.sh"
    exit 1
fi

if ! command -v ffmpeg &>/dev/null; then
    echo "[ERROR] ffmpeg 未安装，请先运行 bash setup_cloud.sh"
    exit 1
fi

echo "========================================"
echo "  抖音爆款分析 API Server"
echo "========================================"
echo "  端口: $PORT"
echo "  工作目录: $SCRIPT_DIR"
echo "  Health: http://localhost:$PORT/health"
echo "  Webhook: POST http://localhost:$PORT/webhook"
echo "========================================"
echo ""

# 启动服务
python3 api_server.py --port "$PORT"
