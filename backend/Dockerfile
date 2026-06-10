# Multi-stage Dockerfile for vibejet
# Optimized for production with minimal image size

# ============================================================================
# Stage 1: Builder - Install dependencies and compile
# ============================================================================
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only dependency manifests first (for better layer caching).
# pyproject.toml + uv.lock are the single source of truth for dependencies.
COPY pyproject.toml uv.lock ./

# Install Python dependencies to a virtual environment.
# Add optional integrations as extras, e.g. --extra s3 --extra celery
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip uv && \
    uv export --frozen --no-emit-project --no-dev -o /tmp/requirements.txt && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# ============================================================================
# Stage 2: Runtime - Minimal production image
# ============================================================================
FROM python:3.11-slim as runtime

WORKDIR /app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
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
    CMD curl -f http://localhost:8000/health || exit 1

# Expose ports (HTTP + gRPC)
EXPOSE 8000 50051

# Compile translations if available (non-fatal when locales are missing)
RUN pybabel --version >/dev/null 2>&1 && pybabel compile -d locales || true

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

# ============================================================================
# Stage 3: Development - With dev tools
# ============================================================================
FROM runtime as development

USER root

# Install development dependencies (dev extra from pyproject)
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && \
    uv export --frozen --no-emit-project --extra dev -o /tmp/requirements-dev.txt && \
    pip install --no-cache-dir -r /tmp/requirements-dev.txt

# Install git for pre-commit
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

USER appuser

# Compile translations in development stage as well
RUN pybabel --version >/dev/null 2>&1 && pybabel compile -d locales || true

# Enable hot reload for development
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
