"""FastAPI application exposing the etymology graph endpoints."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

try:  # Support execution via `python backend/main.py`
    from .database import fetch_etymology, fetch_random_word
except ImportError:  # pragma: no cover - fallback when run as a script
    from database import fetch_etymology, fetch_random_word

app = FastAPI(title="Etymology Graph API")

# Resolve frontend directory relative to this file
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/health")
def health_check():
    """Health check endpoint for container orchestration."""
    return {"status": "healthy"}


@app.get("/graph/{word}")
def get_graph(word: str):
    """Fetch etymology graph for a word."""
    graph = fetch_etymology(word)
    if not graph:
        raise HTTPException(status_code=404, detail="Word not found")
    return graph


@app.get("/random")
def get_random_word():
    """Return a random English word from the dataset."""
    return fetch_random_word()


# Serve frontend static files (must be after API routes)
if FRONTEND_DIR.exists():
    @app.get("/")
    def serve_index():
        """Serve the main HTML page."""
        return FileResponse(FRONTEND_DIR / "index.html")

    app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="frontend")
