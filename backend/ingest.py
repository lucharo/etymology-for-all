"""Load EtymDB CSV files into a DuckDB database."""

from __future__ import annotations

import json
import os
from pathlib import Path

import duckdb

try:  # Local execution vs. package import
    from .download_data import DATA_DIR, download
except ImportError:  # pragma: no cover - fallback for direct execution
    from download_data import DATA_DIR, download

DEFAULT_DB_PATH = DATA_DIR / "etymdb.duckdb"
DEFAULT_VALUES = DATA_DIR / "etymdb_values.csv"
DEFAULT_LINKS = DATA_DIR / "etymdb_links_info.csv"

DB_PATH = Path(os.environ.get("ETYM_DB_PATH", DEFAULT_DB_PATH))
VALUES_CSV = Path(os.environ.get("ETYM_VALUES_CSV", DEFAULT_VALUES))
LINKS_CSV = Path(os.environ.get("ETYM_LINKS_CSV", DEFAULT_LINKS))

SQL_DIR = Path(__file__).parent / "sql"


def _ensure_csvs() -> None:
    if VALUES_CSV.exists() and LINKS_CSV.exists():
        return
    download()
    if not (VALUES_CSV.exists() and LINKS_CSV.exists()):  # pragma: no cover - defensive
        raise FileNotFoundError("Failed to download required CSV files")


def execute_sql_file(conn: duckdb.DuckDBPyConnection, filename: str, **params) -> None:
    """Execute a SQL file with optional parameters."""
    sql = (SQL_DIR / filename).read_text()
    if params:
        conn.execute(sql, params)
    else:
        conn.execute(sql)


def load_language_families(conn: duckdb.DuckDBPyConnection) -> None:
    """Load language families from JSON into the database."""
    language_codes_path = DATA_DIR / "language_codes.json"
    if not language_codes_path.exists():
        raise FileNotFoundError(
            f"Missing {language_codes_path}. "
            "Run `python -m backend.download_language_codes` first."
        )

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


def main() -> None:
    """Create or refresh the DuckDB database from the CSV files."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    _ensure_csvs()

    with duckdb.connect(DB_PATH.as_posix()) as conn:
        # Drop existing tables
        conn.execute("DROP TABLE IF EXISTS words")
        conn.execute("DROP TABLE IF EXISTS links")
        conn.execute("DROP TABLE IF EXISTS language_families")

        # Create base tables from CSVs
        execute_sql_file(conn, "01_create_words.sql", csv_path=VALUES_CSV.as_posix())
        execute_sql_file(conn, "02_create_links.sql", csv_path=LINKS_CSV.as_posix())

        # Create indexes
        execute_sql_file(conn, "03_create_indexes.sql")

        # Create macros and views
        execute_sql_file(conn, "04_create_macros.sql")
        execute_sql_file(conn, "05_create_views.sql")

        # Create and populate language families
        execute_sql_file(conn, "06_create_language_families.sql")
        load_language_families(conn)

        # Create definitions table (for enrichment)
        execute_sql_file(conn, "07_create_definitions_raw.sql")


if __name__ == "__main__":  # pragma: no cover - manual utility
    main()
