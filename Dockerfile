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

# Install zstd for decompression (only needed if DB is compressed)
RUN apt-get update && apt-get install -y --no-install-recommends zstd && rm -rf /var/lib/apt/lists/*

# Copy only what we need from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/backend /app/backend
COPY --from=builder /app/frontend /app/frontend
COPY --from=builder /app/pyproject.toml /app/pyproject.toml

# Copy database (compressed or uncompressed) and decompress if needed
COPY backend/data/etymdb.duckdb* /app/backend/data/
RUN if [ -f /app/backend/data/etymdb.duckdb.zst ]; then \
        echo "Decompressing database..." && \
        zstd -d /app/backend/data/etymdb.duckdb.zst -o /app/backend/data/etymdb.duckdb && \
        rm /app/backend/data/etymdb.duckdb.zst; \
    fi

# Use the virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Port configuration (HF Spaces uses 7860)
ENV PORT=7860
EXPOSE ${PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health')" || exit 1

CMD uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}
