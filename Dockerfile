# Stage 1: Build stage with uv dependency installation
FROM python:3.12-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy workspace dependency definitions for efficient layer caching
COPY pyproject.toml uv.lock* ./
COPY backend/pyproject.toml backend/uv.lock* ./backend/

# Install workspace dependencies into virtual environment
RUN uv sync --no-dev --no-install-project

# Copy backend application source and complete sync
COPY backend/ ./backend/
RUN uv sync --no-dev


# Stage 2: Minimal production runtime image
FROM python:3.12-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend:/app \
    PATH="/app/.venv/bin:$PATH"

# Install minimal runtime libraries (libpq5 for PostgreSQL asyncpg, curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment and backend code from builder
COPY --from=builder /app/.venv /app/.venv
COPY backend/ /app/backend
COPY data/ /app/data

# Non-root application user for production security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Health check to ensure service readiness
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Change working directory to backend so relative paths and main:app resolve cleanly
WORKDIR /app/backend

# Launch uvicorn binding to Render's dynamic $PORT (falling back to 8000 locally)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
