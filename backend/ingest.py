"""Load EtymDB CSV files into a DuckDB database."""
from __future__ import annotations

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


def _ensure_csvs() -> None:
    if VALUES_CSV.exists() and LINKS_CSV.exists():
        return
    download()
    if not (VALUES_CSV.exists() and LINKS_CSV.exists()):  # pragma: no cover - defensive
        raise FileNotFoundError("Failed to download required CSV files")


def main() -> None:
    """Create or refresh the DuckDB database from the CSV files."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    _ensure_csvs()

    with duckdb.connect(DB_PATH.as_posix()) as conn:
        conn.execute("DROP TABLE IF EXISTS words")
        conn.execute("DROP TABLE IF EXISTS links")

        conn.execute(
            """
            CREATE TABLE words AS
            SELECT
                word_ix::BIGINT AS word_ix,
                lang,
                lexeme,
                sense
            FROM read_csv_auto(?, delim='\t', header=false, columns={
                'word_ix': 'BIGINT',
                'lang': 'VARCHAR',
                'dummy': 'INTEGER',
                'lexeme': 'VARCHAR',
                'sense': 'VARCHAR'
            })
            """,
            [VALUES_CSV.as_posix()],
        )

        conn.execute(
            """
            CREATE TABLE links AS
            SELECT
                type,
                source::BIGINT AS source,
                target::BIGINT AS target
            FROM read_csv_auto(?, delim='\t', header=false, columns={
                'type': 'VARCHAR',
                'source': 'BIGINT',
                'target': 'BIGINT'
            })
            """,
            [LINKS_CSV.as_posix()],
        )

        conn.execute("CREATE INDEX idx_words_word_ix ON words(word_ix)")
        conn.execute("CREATE INDEX idx_words_lexeme ON words(lexeme)")
        conn.execute("CREATE INDEX idx_links_source ON links(source)")
        conn.execute("CREATE INDEX idx_links_target ON links(target)")


if __name__ == "__main__":  # pragma: no cover - manual utility
    main()
