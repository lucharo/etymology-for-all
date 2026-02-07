"""Load EtymDB CSV files into a DuckDB database."""

from __future__ import annotations

import json
import os
from pathlib import Path

import duckdb

try:  # Local execution vs. package import
    from .download_data import DATA_DIR, download
    from .sql_loader import load_sql
except ImportError:  # pragma: no cover - fallback for direct execution
    from download_data import DATA_DIR, download
    from sql_loader import load_sql

DEFAULT_DB_PATH = DATA_DIR / "etymdb.duckdb"
DEFAULT_VALUES = DATA_DIR / "etymdb_values.csv"
DEFAULT_LINKS = DATA_DIR / "etymdb_links_info.csv"
DEFAULT_LINKS_INDEX = DATA_DIR / "etymdb_links_index.csv"

DB_PATH = Path(os.environ.get("ETYM_DB_PATH", DEFAULT_DB_PATH))
VALUES_CSV = Path(os.environ.get("ETYM_VALUES_CSV", DEFAULT_VALUES))
LINKS_CSV = Path(os.environ.get("ETYM_LINKS_CSV", DEFAULT_LINKS))
LINKS_INDEX_CSV = Path(os.environ.get("ETYM_LINKS_INDEX_CSV", DEFAULT_LINKS_INDEX))


def _ensure_csvs() -> None:
    required = [VALUES_CSV, LINKS_CSV, LINKS_INDEX_CSV]
    if all(f.exists() for f in required):
        return
    download()
    if not all(f.exists() for f in required):  # pragma: no cover - defensive
        raise FileNotFoundError("Failed to download required CSV files")


def main() -> None:
    """Create or refresh the DuckDB database from the CSV files."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    _ensure_csvs()

    with duckdb.connect(DB_PATH.as_posix()) as conn:
        # Drop and recreate core tables
        for stmt in load_sql("ingestion/01_drop_tables.sql").strip().split(";"):
            if stmt.strip():
                conn.execute(stmt)

        conn.execute(load_sql("ingestion/02_create_words.sql"), [VALUES_CSV.as_posix()])
        conn.execute(load_sql("ingestion/03_create_links.sql"), [LINKS_CSV.as_posix()])
        conn.execute(load_sql("ingestion/04_create_sequences.sql"))

        # Parse and insert sequences (handles variable-length rows)
        with open(LINKS_INDEX_CSV, encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) < 2:
                    continue
                seq_ix = int(parts[0])
                for position, parent in enumerate(parts[1:]):
                    if parent:
                        conn.execute(
                            "INSERT INTO sequences VALUES (?, ?, ?)",
                            [seq_ix, position, int(parent)],
                        )

        # Create indexes
        for stmt in load_sql("ingestion/05_create_indexes.sql").strip().split(";"):
            if stmt.strip():
                conn.execute(stmt)

        # Gold Layer: Macros, Views, and Reference Tables
        for stmt in load_sql("ingestion/06_create_macros.sql").strip().split(";"):
            if stmt.strip():
                conn.execute(stmt)

        for stmt in load_sql("ingestion/07_create_views.sql").strip().split(";"):
            if stmt.strip():
                conn.execute(stmt)

        # Language families reference table
        language_codes_path = DATA_DIR / "language_codes.json"
        if not language_codes_path.exists():
            raise FileNotFoundError(
                f"Missing {language_codes_path}. "
                "Run `python -m backend.download_language_codes` first."
            )

        for stmt in load_sql("ingestion/08_create_language_families.sql").strip().split(";"):
            if stmt.strip():
                conn.execute(stmt)

        with open(language_codes_path, encoding="utf-8") as f:
            language_data = json.load(f)
        for entry in language_data:
            conn.execute(
                "INSERT INTO language_families VALUES (?, ?, ?, ?)",
                [
                    entry["code"],
                    entry["name"],
                    entry.get("family"),
                    entry.get("branch"),
                ],
            )

        # Definition enrichment tables
        conn.execute(load_sql("ingestion/09_create_definitions_raw.sql"))


if __name__ == "__main__":  # pragma: no cover - manual utility
    main()
