"""Load SQL files from the backend/sql/ directory."""

from __future__ import annotations

from functools import cache
from pathlib import Path

SQL_DIR = Path(__file__).parent / "sql"


@cache
def load_sql(filename: str) -> str:
    """Read and cache a SQL file from backend/sql/.

    Args:
        filename: Relative path within the sql/ directory,
                  e.g. "queries/find_start_word.sql"
    """
    return (SQL_DIR / filename).read_text()
