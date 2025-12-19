"""Database helpers for the FastAPI application."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

import duckdb

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = BASE_DIR / "data"


def _resolve_path(env_var: str, default: Path) -> Path:
    value = os.environ.get(env_var)
    return Path(value) if value else default


def _data_dir() -> Path:
    return _resolve_path("ETYM_DATA_DIR", DEFAULT_DATA_DIR)


@lru_cache(maxsize=1)
def database_path() -> Path:
    """Return the configured DuckDB path, creating parent directories."""
    path = _resolve_path("ETYM_DB_PATH", _data_dir() / "etymdb.duckdb")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _ensure_database() -> Path:
    db_path = database_path()
    if db_path.exists():
        return db_path

    try:
        from . import ingest  # type: ignore[attr-defined]
    except ImportError:  # pragma: no cover - fallback for direct execution
        import ingest

    try:
        ingest.main()
    except Exception as exc:  # pragma: no cover - propagation with context
        raise RuntimeError("Failed to ingest the EtymDB dataset") from exc

    if not db_path.exists():
        raise RuntimeError(f"Expected DuckDB database at {db_path} after ingestion")
    return db_path


class _ConnectionManager:
    """Lazily open DuckDB connections when required."""

    def __init__(self) -> None:
        self._conn: duckdb.DuckDBPyConnection | None = None

    def __enter__(self) -> duckdb.DuckDBPyConnection:
        db_path = _ensure_database()
        self._conn = duckdb.connect(db_path.as_posix(), read_only=True)
        return self._conn

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._conn is not None:
            self._conn.close()


def _normalize_depth(depth: int) -> int:
    return max(depth, 0)


def fetch_etymology(word: str, depth: int = 5) -> Optional[Dict]:
    """Return an etymology graph for *word* or ``None`` if absent."""
    if not word:
        return None

    depth = _normalize_depth(depth)
    with _ConnectionManager() as conn:
        start = conn.execute(
            "SELECT word_ix, lang, lexeme FROM words WHERE lower(lexeme) = lower(?) LIMIT 1",
            [word],
        ).fetchone()
        if not start:
            return None

        start_ix, start_lang, start_lexeme = start
        nodes: Dict[int, Dict[str, str]] = {
            start_ix: {"id": start_lexeme, "lang": start_lang},
        }
        edges = []
        seen_edges = set()

        if depth > 0:
            records = conn.execute(
                """
                WITH RECURSIVE traversal(child_ix, parent_ix, lvl) AS (
                    SELECT source, target, 1
                    FROM links
                    WHERE source = ?
                    UNION ALL
                    SELECT l.source, l.target, lvl + 1
                    FROM traversal t
                    JOIN links l ON l.source = t.parent_ix
                    WHERE lvl < ?
                )
                SELECT
                    child.word_ix AS child_ix,
                    child.lexeme AS child_lexeme,
                    child.lang AS child_lang,
                    parent.word_ix AS parent_ix,
                    parent.lexeme AS parent_lexeme,
                    parent.lang AS parent_lang
                FROM traversal tr
                JOIN words child ON child.word_ix = tr.child_ix
                JOIN words parent ON parent.word_ix = tr.parent_ix
                """,
                [start_ix, depth],
            ).fetchall()

            for child_ix, child_lexeme, child_lang, parent_ix, parent_lexeme, parent_lang in records:
                nodes.setdefault(child_ix, {"id": child_lexeme, "lang": child_lang})
                nodes.setdefault(parent_ix, {"id": parent_lexeme, "lang": parent_lang})
                edge_key = (child_lexeme, parent_lexeme)
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edges.append({"source": child_lexeme, "target": parent_lexeme})

        return {"nodes": list(nodes.values()), "edges": edges}


def fetch_random_word() -> Dict[str, Optional[str]]:
    """Return a random curated English word (has etymology, no phrases/proper nouns)."""
    with _ConnectionManager() as conn:
        row = conn.execute(
            "SELECT lexeme FROM v_english_curated ORDER BY random() LIMIT 1"
        ).fetchone()
        return {"word": row[0] if row else None}


def fetch_language_info(lang_code: str) -> Optional[Dict[str, str]]:
    """Return language family info for a language code."""
    with _ConnectionManager() as conn:
        row = conn.execute(
            "SELECT lang_name, family, branch FROM language_families WHERE lang_code = ?",
            [lang_code],
        ).fetchone()
        if row:
            return {"name": row[0], "family": row[1], "branch": row[2]}
        return None


def fetch_all_language_families() -> Dict[str, Dict[str, str]]:
    """Return all language family mappings."""
    with _ConnectionManager() as conn:
        rows = conn.execute(
            "SELECT lang_code, lang_name, family, branch FROM language_families"
        ).fetchall()
        return {
            row[0]: {"name": row[1], "family": row[2], "branch": row[3]}
            for row in rows
        }
