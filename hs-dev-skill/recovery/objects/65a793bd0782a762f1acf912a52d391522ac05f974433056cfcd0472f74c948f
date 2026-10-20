# ==============================================================================
# Stage 1: Build Environment & Dependencies
# ==============================================================================
FROM python:3.12-slim AS builder

WORKDIR /build

# Install basic build tooling
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy package definitions and install production dependencies
COPY backend/pyproject.toml /build/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    "fastapi>=0.110.0" \
    "uvicorn[standard]>=0.28.0" \
    "pydantic>=2.6.0" \
    "pydantic-settings>=2.2.0" \
    "sqlalchemy>=2.0.28" \
    "python-multipart>=0.0.9" \
    "pyyaml>=6.0" \
    "httpx>=0.27.0"

# ==============================================================================
# Stage 2: Production Distroless / Hardened Runtime
# ==============================================================================
FROM python:3.12-slim AS runner

# Create dedicated non-root execution user for Solo Maker security
RUN groupadd -g 10001 opc && \
    useradd -u 10001 -g opc -s /bin/bash -m opc

WORKDIR /app

# Copy isolated virtualenv from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    OPCHUB_ENVIRONMENT=production \
    OPCHUB_SERVER_HOST=0.0.0.0 \
    OPCHUB_SERVER_PORT=8000 \
    PYTHONPATH="/app/backend:/app"

# Copy backend source & configurations
COPY backend /app/backend

# Copy visual console html & doc foundations
COPY hs_dev_docs /app/hs_dev_docs

# Create runtime data directory with proper ownership
RUN mkdir -p /app/data && \
    chown -R opc:opc /app

# Switch to non-root execution
USER opc

# Expose default HTTP port
EXPOSE 8000

# Native Python container healthcheck (zero external curl/wget dependencies)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

# Launch microkernel platform via Uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "/app/backend"]
