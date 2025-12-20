"""FastAPI application exposing the etymology graph endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

try:  # Support execution via `python backend/main.py`
    from .database import fetch_etymology, fetch_random_word, search_words
except ImportError:  # pragma: no cover - fallback when run as a script
    from database import fetch_etymology, fetch_random_word, search_words

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Etymology Graph API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS for frontend hosted on different domain (e.g., Cloudflare Pages)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://etymology.luischav.es",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Resolve frontend directory relative to this file
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/health")
def health_check():
    """Health check endpoint for container orchestration."""
    return {"status": "healthy"}


@app.get("/graph/{word}")
@limiter.limit("20/minute")
def get_graph(request: Request, word: str):
    """Fetch etymology graph for a word."""
    graph = fetch_etymology(word)
    if not graph:
        raise HTTPException(status_code=404, detail="Word not found")
    return graph


@app.get("/random")
@limiter.limit("50/minute")
def get_random_word(request: Request):
    """Return a random English word from the dataset."""
    return fetch_random_word()


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
