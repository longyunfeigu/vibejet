# Multi-stage Dockerfile for vibejet
# Optimized for production with minimal image size

# ============================================================================
# Stage 1: Builder - Install dependencies and compile
# ============================================================================
# Optional package mirrors (empty = official Debian / PyPI). Behind the GFW, e.g.:
#   DEBIAN_MIRROR=https://mirrors.tuna.tsinghua.edu.cn
#   PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
# docker-compose forwards both from the shell environment.
ARG DEBIAN_MIRROR=""
ARG PIP_INDEX_URL=""

FROM python:3.11-slim as builder
ARG DEBIAN_MIRROR
ARG PIP_INDEX_URL

WORKDIR /build

# Install build dependencies
RUN if [ -n "$DEBIAN_MIRROR" ]; then \
        sed -i "s|http://deb.debian.org|$DEBIAN_MIRROR|g" /etc/apt/sources.list.d/debian.sources; \
    fi && \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only dependency manifests first (for better layer caching).
# pyproject.toml + uv.lock are the single source of truth for dependencies.
COPY pyproject.toml uv.lock ./

# Install Python dependencies to a virtual environment.
# Optional integrations come in via the EXTRAS build arg (space-separated pyproject extras),
# e.g. `docker build --build-arg EXTRAS="grpc s3" ...`; docker-compose sets it per service.
ARG EXTRAS=""
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir ${PIP_INDEX_URL:+--index-url "$PIP_INDEX_URL"} --upgrade pip uv && \
    uv export --frozen --no-emit-project --no-dev \
        $(for extra in $EXTRAS; do printf -- '--extra %s ' "$extra"; done) \
        -o /tmp/requirements.txt && \
    pip install --no-cache-dir ${PIP_INDEX_URL:+--index-url "$PIP_INDEX_URL"} -r /tmp/requirements.txt

# ============================================================================
# Stage 2: Runtime - Minimal production image
# ============================================================================
FROM python:3.11-slim as runtime
ARG DEBIAN_MIRROR

WORKDIR /app

# Install only runtime dependencies
RUN if [ -n "$DEBIAN_MIRROR" ]; then \
        sed -i "s|http://deb.debian.org|$DEBIAN_MIRROR|g" /etc/apt/sources.list.d/debian.sources; \
    fi && \
    apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser && \
    mkdir -p /app/logs /app/storage && \
    chown -R appuser:appuser /app

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Set Python environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8010/health || exit 1

# Expose ports (HTTP + gRPC)
EXPOSE 8010 50051

# Compile translations if available (non-fatal when locales are missing)
RUN pybabel --version >/dev/null 2>&1 && pybabel compile -d locales || true

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8010", "--workers", "1"]

# ============================================================================
# Stage 3: Development - With dev tools
# ============================================================================
FROM runtime as development
ARG PIP_INDEX_URL

USER root

# Install development dependencies (dev extra from pyproject)
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir ${PIP_INDEX_URL:+--index-url "$PIP_INDEX_URL"} uv && \
    uv export --frozen --no-emit-project --extra dev -o /tmp/requirements-dev.txt && \
    pip install --no-cache-dir ${PIP_INDEX_URL:+--index-url "$PIP_INDEX_URL"} -r /tmp/requirements-dev.txt

# Install git for pre-commit
RUN if [ -n "$DEBIAN_MIRROR" ]; then \
        sed -i "s|http://deb.debian.org|$DEBIAN_MIRROR|g" /etc/apt/sources.list.d/debian.sources; \
    fi && \
    apt-get update && apt-get install -y --no-install-recommends \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

USER appuser

# Compile translations in development stage as well
RUN pybabel --version >/dev/null 2>&1 && pybabel compile -d locales || true

# Enable hot reload for development
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8010", "--reload"]
