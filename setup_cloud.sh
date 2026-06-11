#!/bin/bash
# ============================================================
# 云电脑一键部署脚本 — Coze Cloud Computer / Ubuntu
# 用法: bash setup_cloud.sh
# ============================================================
set -e

echo "========================================"
echo "  抖音爆款分析 — 云部署初始化"
echo "========================================"

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# ---------- 1. 系统依赖 ----------
echo ""
echo "[1/6] 安装系统依赖..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
    python3 python3-pip python3-venv \
    nodejs npm \
    ffmpeg \
    tesseract-ocr tesseract-ocr-chi-sim \
    chromium-browser \
    golang-go \
    curl wget

# 确保 python 命令可用
if ! command -v python &>/dev/null; then
    sudo ln -sf /usr/bin/python3 /usr/bin/python
fi

# ---------- 2. Python 依赖 ----------
echo ""
echo "[2/6] 安装 Python 依赖..."
pip3 install --break-system-packages -r requirements.txt 2>/dev/null || \
pip3 install -r requirements.txt

# ---------- 3. Node 依赖 ----------
echo ""
echo "[3/6] 安装 Node 依赖..."
npm install

# ---------- 4. Playwright 浏览器 ----------
echo ""
echo "[4/6] 安装 Playwright Chromium..."
npx playwright install chromium
npx playwright install-deps

# ---------- 5. lark-cli (飞书 CLI) ----------
echo ""
echo "[5/6] 安装 lark-cli..."
go install github.com/larksuite/oapi-sdk-go/v3/tools/lark_cli@latest 2>/dev/null || {
    echo "  Go install 失败，尝试从 GitHub 下载预编译版本..."
    ARCH=$(uname -m)
    case $ARCH in
        x86_64)  BIN_ARCH="amd64" ;;
        aarch64) BIN_ARCH="arm64" ;;
        *)       BIN_ARCH="amd64" ;;
    esac
    LARK_URL="https://github.com/larksuite/oapi-sdk-go/releases/latest/download/lark_cli_linux_${BIN_ARCH}"
    mkdir -p ~/go/bin
    curl -fsSL "$LARK_URL" -o ~/go/bin/cli 2>/dev/null || wget -q "$LARK_URL" -O ~/go/bin/cli
    chmod +x ~/go/bin/cli
}

# 验证 lark-cli
if [ -f ~/go/bin/cli ]; then
    echo "  lark-cli: $(~/go/bin/cli --version 2>&1 || echo 'installed')"
else
    echo "  ? lark-cli 安装失败，请在 Coze 控制台手动完成"
fi

# ---------- 6. 环境变量 ----------
echo ""
echo "[6/6] 配置环境变量..."

# 持久化到 .env 文件
cat > "$PROJECT_DIR/.env" << 'ENVEOF'
# 抖音爆款分析 — 环境变量
# 请在下方填入实际值
DEEPSEEK_API_KEY=sk-your-deepseek-key-here
FEISHU_BASE_TOKEN=your-feishu-base-token-here
ENVEOF

# 导出当前 shell
export DEEPSEEK_API_KEY="sk-your-deepseek-key-here"
export FEISHU_BASE_TOKEN="your-feishu-base-token-here"

echo ""
echo "========================================"
echo "  ? 部署完成！"
echo "========================================"
echo ""
echo "  下一步："
echo "  1. 飞书扫码登录: ~/go/bin/cli auth"
echo "  2. 启动服务: bash start_server.sh"
echo "  3. 验证: curl http://localhost:8080/health"
echo ""
