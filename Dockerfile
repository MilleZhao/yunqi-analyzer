# ============================================================
# 抖音爆款分析 — 阿里云 FC 部署镜像
# 构建: docker build -t douyin-analyzer .
# 本地测试: docker run -p 9000:9000 --env-file .env douyin-analyzer
# ============================================================
FROM docker.m.daocloud.io/library/ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive     PYTHONUNBUFFERED=1     PORT=9000

# ---------- 系统依赖 ----------
RUN sed -i "s@http://.*archive.ubuntu.com@http://mirrors.aliyun.com@g" /etc/apt/sources.list.d/ubuntu.sources 2>/dev/null; \
    sed -i "s@http://.*ports.ubuntu.com@http://mirrors.aliyun.com@g" /etc/apt/sources.list.d/ubuntu.sources 2>/dev/null || true; \
    apt-get update && apt-get install -y --no-install-recommends     python3 python3-pip python3-venv     ffmpeg     curl ca-certificates wget     fonts-wqy-zenhei fonts-noto-cjk     libnss3 libnspr4 libatk-bridge2.0-0 libdrm2 libxkbcommon0     libgbm1 libasound2 libx11-xcb1 libxcomposite1 libxdamage1     libxrandr2 libgtk-3-0 libpango-1.0-0 libcairo2     && rm -rf /var/lib/apt/lists/*

# ---------- Node.js 22 ----------
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash -     && apt-get install -y nodejs     && rm -rf /var/lib/apt/lists/*

# ---------- lark-cli (飞书 CLI, 预编译二进制) ----------
RUN mkdir -p /root/go/bin     && ARCH=$(uname -m)     && case $ARCH in          x86_64)  BIN_ARCH="amd64" ;;          aarch64) BIN_ARCH="arm64" ;;          *)       BIN_ARCH="amd64" ;;        esac     && LARK_URL="https://github.com/larksuite/oapi-sdk-go/releases/latest/download/lark_cli_linux_${BIN_ARCH}"     && wget -q "$LARK_URL" -O /root/go/bin/cli 2>/dev/null || curl -fsSL "$LARK_URL" -o /root/go/bin/cli     && chmod +x /root/go/bin/cli     && echo "lark-cli installed: $(/root/go/bin/cli --version 2>&1 || echo done)"

# ---------- 工作目录 ----------
WORKDIR /app

# ---------- Python 依赖 ----------
COPY requirements.txt .
RUN pip3 install --break-system-packages -r requirements.txt

# ---------- Node 依赖 + Playwright ----------
COPY package.json package-lock.json ./
RUN npm install     && npx playwright install chromium     && npx playwright install-deps

# ---------- 应用代码 ----------
COPY . .

# ---------- 健康检查 ----------
HEALTHCHECK --interval=30s --timeout=5s --retries=3     CMD curl -f http://localhost:${PORT}/health || exit 1

# ---------- 启动 ----------
EXPOSE ${PORT}
CMD ["sh", "-c", "python3 api_server.py --port ${PORT:-9000}"]
