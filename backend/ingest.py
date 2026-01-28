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
        conn.execute("DROP TABLE IF EXISTS words")
        conn.execute("DROP TABLE IF EXISTS links")
        conn.execute("DROP TABLE IF EXISTS sequences")

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

        # Lexeme sequences table: maps negative IDs to compound etymologies
        # Each sequence links a negative ID to one or more parent words
        # Some compounds have 3+ components, so we normalize to (seq_ix, position, parent_ix)
        conn.execute("""
            CREATE TABLE sequences (
                seq_ix BIGINT,
                position INT,
                parent_ix BIGINT
            )
        """)

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

        conn.execute("CREATE INDEX idx_words_word_ix ON words(word_ix)")
        conn.execute("CREATE INDEX idx_words_lexeme ON words(lexeme)")
        conn.execute("CREATE INDEX idx_links_source ON links(source)")
        conn.execute("CREATE INDEX idx_links_target ON links(target)")
        conn.execute("CREATE INDEX idx_sequences_seq_ix ON sequences(seq_ix)")
        conn.execute("CREATE INDEX idx_sequences_parent_ix ON sequences(parent_ix)")

        # ============================================================
        # Gold Layer: Macros, Views, and Reference Tables
        # ============================================================

        # Macros for reusable filtering conditions
        conn.execute("""
            CREATE OR REPLACE MACRO is_phrase(lexeme) AS
                lexeme LIKE '% %'
        """)
        conn.execute("""
            CREATE OR REPLACE MACRO is_proper_noun(lexeme) AS
                regexp_matches(lexeme, '^[A-Z][a-z]')
        """)
        conn.execute("""
            CREATE OR REPLACE MACRO is_clean_word(lexeme) AS
                NOT is_phrase(lexeme) AND NOT is_proper_noun(lexeme)
        """)
        conn.execute("""
            CREATE OR REPLACE MACRO has_etymology(word_ix) AS
                word_ix IN (SELECT DISTINCT source FROM links)
        """)

        # Curated view: English words with etymology, no phrases/proper nouns
        # Filter out sense=NULL entries which are often garbage (e.g., suffix entries
        # like "-er" with corrupted links to unrelated words like "asteroid belt")
        # Paper notes 40% of EtymDB lacks glosses; our curated set is 99% with sense
        conn.execute("""
            CREATE OR REPLACE VIEW v_english_curated AS
            SELECT DISTINCT w.*
            FROM words w
            JOIN links l ON w.word_ix = l.source
            WHERE w.lang = 'en'
              AND is_clean_word(w.lexeme)
              AND w.sense IS NOT NULL
        """)

        # View for words with "deep" etymology (at least one link to a real word)
        # Excludes compound-only words where all links point to sequences (negative IDs)
        # Also excludes sense=NULL entries (same rationale as v_english_curated)
        conn.execute("""
            CREATE OR REPLACE VIEW v_english_deep AS
            SELECT DISTINCT w.*
            FROM words w
            JOIN links l ON w.word_ix = l.source
            WHERE w.lang = 'en'
              AND is_clean_word(w.lexeme)
              AND w.sense IS NOT NULL
              AND l.target > 0
        """)

        # Language families reference table
        # Load from language_codes.json (2400+ language code mappings)
        # Run `python -m backend.download_language_codes` to generate this file
        language_codes_path = DATA_DIR / "language_codes.json"
        if not language_codes_path.exists():
            raise FileNotFoundError(
                f"Missing {language_codes_path}. "
                "Run `python -m backend.download_language_codes` first."
            )

        conn.execute("DROP TABLE IF EXISTS language_families")
        conn.execute("""
            CREATE TABLE language_families (
                lang_code VARCHAR PRIMARY KEY,
                lang_name VARCHAR,
                family VARCHAR,
                branch VARCHAR
            )
        """)

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

        # ============================================================
        # Definition Enrichment Tables
        # ============================================================

        # Table to store raw API responses from Free Dictionary API
        # After enrichment, run --materialize to create the `definitions` table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS definitions_raw (
                lexeme VARCHAR PRIMARY KEY,
                api_response JSON,
                fetched_at TIMESTAMP,
                status VARCHAR
            )
        """)


if __name__ == "__main__":  # pragma: no cover - manual utility
    main()
