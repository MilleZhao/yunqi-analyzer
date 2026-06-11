# ============================================================
# Dockerfile - Alibaba Cloud FC deployment
# ============================================================
FROM docker.m.daocloud.io/library/ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 PORT=9000

# System deps (Aliyun mirrors for China)
RUN sed -i "s@http://.*archive.ubuntu.com@http://mirrors.aliyun.com@g" /etc/apt/sources.list.d/ubuntu.sources 2>/dev/null; \
    sed -i "s@http://.*ports.ubuntu.com@http://mirrors.aliyun.com@g" /etc/apt/sources.list.d/ubuntu.sources 2>/dev/null || true; \
    apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv ffmpeg \
    curl ca-certificates wget \
    fonts-wqy-zenhei fonts-noto-cjk \
    libnss3 libnspr4 libatk-bridge2.0-0 libdrm2 libxkbcommon0 \
    libgbm1 libasound2t64 libx11-xcb1 libxcomposite1 libxdamage1 \
    libxrandr2 libgtk-3-0 libpango-1.0-0 libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# Node.js 22
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps
COPY requirements.txt .
RUN pip3 install --break-system-packages -r requirements.txt

# Node deps + Playwright (use npm mirror for China)
COPY package.json package-lock.json ./
RUN npm config set registry https://registry.npmmirror.com \
    && npm install \
    && npx playwright install chromium \
    && npx playwright install-deps

# App code
COPY . .

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:$${PORT}/health || exit 1

EXPOSE $${PORT}
CMD python3 api_server.py --port $${PORT:-9000}
