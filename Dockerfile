# ==============================================================================
# OpcHub Backend — Microkernel Platform Server (FastAPI + Unified Gateway)
# Build: docker build -t opchub-backend:latest .
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Dependency Builder — install exact dependency set from pyproject.toml
# into an isolated virtualenv (includes asyncpg / pgvector / alembic / greenlet).
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build

# 构建期 PyPI 镜像源（国内网络直连官方源极慢，默认清华源，可 --build-arg 覆盖）
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV PIP_INDEX_URL=${PIP_INDEX_URL}

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY backend /build/backend
# Installing the project wheel also materializes every dependency declared in
# backend/pyproject.toml; the wheel itself is unused at runtime (source is
# re-copied into /app and imported via PYTHONPATH).
# 全部依赖均有 cp312 manylinux 预编译 wheel，无需 build-essential 编译环节。
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir /build/backend

# ------------------------------------------------------------------------------
# Stage 2: Runtime — non-root hardened image
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS runner

RUN groupadd -g 10001 opc && \
    useradd -u 10001 -g opc -s /bin/bash -m opc

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    OPCHUB_ENVIRONMENT=production \
    OPCHUB_SERVER_HOST=0.0.0.0 \
    OPCHUB_SERVER_PORT=8000 \
    PYTHONPATH="/app/backend:/app"

COPY backend /app/backend
# RAG 文书索引与流程文档的运行时只读依赖
COPY hs_dev_docs /app/hs_dev_docs

RUN mkdir -p /app/data && \
    chown -R opc:opc /app

USER opc

EXPOSE 8000

# Native Python healthcheck (zero external curl/wget dependencies)
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "/app/backend"]
