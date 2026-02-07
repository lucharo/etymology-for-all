"""FastAPI application exposing the etymology graph endpoints."""

from __future__ import annotations

import importlib.metadata
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

try:  # Support execution via `python backend/main.py`
    from .database import (
        fetch_etymology,
        fetch_random_word,
        get_db_stats,
        search_words,
    )
except ImportError:  # pragma: no cover - fallback when run as a script
    from database import fetch_etymology, fetch_random_word, get_db_stats, search_words

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Etymology Graph API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Resolve frontend directory relative to this file
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/health")
def health_check():
    """Health check endpoint for container orchestration."""
    try:
        stats = get_db_stats()
        return {"status": "healthy", "db": stats}
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "reason": str(exc)},
        )


def _get_version() -> str:
    """Read version from package metadata, falling back to pyproject.toml."""
    try:
        return importlib.metadata.version("etymology-for-all")
    except importlib.metadata.PackageNotFoundError:
        # Fallback: parse pyproject.toml directly
        toml_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
        for line in toml_path.read_text().splitlines():
            if line.strip().startswith("version"):
                return line.split("=", 1)[1].strip().strip('"')
        return "unknown"


@app.get("/version")
def version():
    """Return the application version and database statistics."""
    return {"version": _get_version(), "db_stats": get_db_stats()}


@app.get("/graph/{word}")
@limiter.limit("20/minute")
def get_graph(request: Request, word: str, depth: int = 5):
    """Fetch etymology graph for a word."""
    # Clamp depth to reasonable bounds
    depth = max(1, min(depth, 10))
    graph = fetch_etymology(word, depth=depth)
    if graph is None:
        raise HTTPException(status_code=404, detail="Word not found in the database")
    return graph


@app.get("/random")
@limiter.limit("50/minute")
def get_random_word(request: Request, include_compound: bool = True):
    """Return a random English word from the dataset.

    Args:
        include_compound: If True (default), include compound-only words.
                         If False, only return words with deep etymology chains.
    """
    return fetch_random_word(include_compound=include_compound)


@app.get("/search")
@limiter.limit("120/minute")
def search(request: Request, q: str = "", limit: int = 10):
    """Search for words matching the query (autocomplete)."""
    if len(q) < 2:
        return {"results": []}
    results = search_words(q, min(limit, 20))  # Cap at 20
    return {"results": results}


# Serve frontend static files (must be after API routes)
if FRONTEND_DIR.exists():

    @app.get("/")
    def serve_index():
        """Serve the main HTML page."""
        return FileResponse(FRONTEND_DIR / "index.html")

    app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="frontend")
