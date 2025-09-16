"""FastAPI application exposing the etymology graph endpoints."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException

try:  # Support execution via `python backend/main.py`
    from .database import fetch_etymology, fetch_random_word
except ImportError:  # pragma: no cover - fallback when run as a script
    from database import fetch_etymology, fetch_random_word

app = FastAPI(title="Etymology Graph API")


@app.get("/graph/{word}")
def get_graph(word: str):
    graph = fetch_etymology(word)
    if not graph:
        raise HTTPException(status_code=404, detail="Word not found")
    return graph


@app.get("/random")
def get_random_word():
    return fetch_random_word()
