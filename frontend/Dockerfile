# ==============================================================================
# OpcHub Frontend — Vue 3 + Vite production build, served by the FastAPI static
# server with transparent /api reverse proxy to the backend unified gateway.
# Build: docker build -t opchub-frontend:latest -f frontend/Dockerfile .
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build the Vue 3 production bundle (dist/)
# ------------------------------------------------------------------------------
FROM node:20-slim AS builder

WORKDIR /build

# 构建期 npm 镜像源（国内网络直连官方源极慢，默认 npmmirror，可 --build-arg 覆盖）
ARG NPM_REGISTRY=https://registry.npmmirror.com
ENV npm_config_registry=${NPM_REGISTRY}

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN node node_modules/vite/bin/vite.js build

# ------------------------------------------------------------------------------
# Stage 2: Static server + gateway proxy (reuses frontend/server.py)
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS runner

RUN groupadd -g 10001 opc && \
    useradd -u 10001 -g opc -s /bin/bash -m opc

ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV PIP_INDEX_URL=${PIP_INDEX_URL}
RUN pip install --no-cache-dir \
    "fastapi>=0.110.0" \
    "uvicorn[standard]>=0.28.0" \
    "httpx>=0.27.0"

WORKDIR /app
COPY frontend/server.py /app/server.py
COPY --from=builder /build/dist /app/dist

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    OPCHUB_ENVIRONMENT=production \
    OPCHUB_BACKEND_URL=http://backend:8000

RUN chown -R opc:opc /app
USER opc

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:3000/health')" || exit 1

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "3000"]
