# Etymology Graph Explorer
# Multi-stage build: uv for building, plain Python for runtime

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install production dependencies only (no dev, no project yet)
RUN uv sync --locked --no-install-project --no-dev

# Copy application code
COPY backend/ backend/
COPY frontend/ frontend/

# Production stage - plain Python, no uv needed at runtime
FROM python:3.12-slim-bookworm

WORKDIR /app

# Copy only what we need from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/backend /app/backend
COPY --from=builder /app/frontend /app/frontend

# Use the virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Create data directory for DuckDB
RUN mkdir -p /app/backend/data

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
