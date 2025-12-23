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
        conn.execute("""
            CREATE OR REPLACE VIEW v_english_curated AS
            SELECT DISTINCT w.*
            FROM words w
            JOIN links l ON w.word_ix = l.source
            WHERE w.lang = 'en'
              AND is_clean_word(w.lexeme)
        """)

        # Language families reference table
        conn.execute("DROP TABLE IF EXISTS language_families")
        conn.execute("""
            CREATE TABLE language_families (
                lang_code VARCHAR PRIMARY KEY,
                lang_name VARCHAR,
                family VARCHAR,
                branch VARCHAR
            )
        """)
        conn.execute("""
            INSERT INTO language_families VALUES
            -- Modern languages
            ('en', 'English', 'Indo-European', 'Germanic'),
            ('de', 'German', 'Indo-European', 'Germanic'),
            ('nl', 'Dutch', 'Indo-European', 'Germanic'),
            ('sv', 'Swedish', 'Indo-European', 'Germanic'),
            ('da', 'Danish', 'Indo-European', 'Germanic'),
            ('no', 'Norwegian', 'Indo-European', 'Germanic'),
            ('is', 'Icelandic', 'Indo-European', 'Germanic'),
            ('fr', 'French', 'Indo-European', 'Romance'),
            ('es', 'Spanish', 'Indo-European', 'Romance'),
            ('it', 'Italian', 'Indo-European', 'Romance'),
            ('pt', 'Portuguese', 'Indo-European', 'Romance'),
            ('ro', 'Romanian', 'Indo-European', 'Romance'),
            ('la', 'Latin', 'Indo-European', 'Italic'),
            ('grc', 'Ancient Greek', 'Indo-European', 'Hellenic'),
            ('el', 'Modern Greek', 'Indo-European', 'Hellenic'),
            ('ru', 'Russian', 'Indo-European', 'Slavic'),
            ('pl', 'Polish', 'Indo-European', 'Slavic'),
            ('cs', 'Czech', 'Indo-European', 'Slavic'),
            ('sa', 'Sanskrit', 'Indo-European', 'Indo-Iranian'),
            ('fa', 'Persian', 'Indo-European', 'Indo-Iranian'),
            ('hi', 'Hindi', 'Indo-European', 'Indo-Iranian'),
            ('ga', 'Irish', 'Indo-European', 'Celtic'),
            ('cy', 'Welsh', 'Indo-European', 'Celtic'),
            ('hy', 'Armenian', 'Indo-European', 'Armenian'),
            ('sq', 'Albanian', 'Indo-European', 'Albanian'),
            ('lt', 'Lithuanian', 'Indo-European', 'Baltic'),
            ('lv', 'Latvian', 'Indo-European', 'Baltic'),
            -- Historical/Proto languages
            ('ang', 'Old English', 'Indo-European', 'Germanic'),
            ('enm', 'Middle English', 'Indo-European', 'Germanic'),
            ('goh', 'Old High German', 'Indo-European', 'Germanic'),
            ('gmh', 'Middle High German', 'Indo-European', 'Germanic'),
            ('osx', 'Old Saxon', 'Indo-European', 'Germanic'),
            ('non', 'Old Norse', 'Indo-European', 'Germanic'),
            ('got', 'Gothic', 'Indo-European', 'Germanic'),
            ('gem-pro', 'Proto-Germanic', 'Indo-European', 'Germanic'),
            ('gmw-pro', 'Proto-West-Germanic', 'Indo-European', 'Germanic'),
            ('ine-pro', 'Proto-Indo-European', 'Indo-European', 'Proto'),
            ('fro', 'Old French', 'Indo-European', 'Romance'),
            ('frm', 'Middle French', 'Indo-European', 'Romance'),
            ('VL.', 'Vulgar Latin', 'Indo-European', 'Italic'),
            ('sla-pro', 'Proto-Slavic', 'Indo-European', 'Slavic'),
            ('cel-pro', 'Proto-Celtic', 'Indo-European', 'Celtic'),
            ('grk-pro', 'Proto-Greek', 'Indo-European', 'Hellenic'),
            ('iir-pro', 'Proto-Indo-Iranian', 'Indo-European', 'Indo-Iranian'),
            -- Non-Indo-European
            ('ar', 'Arabic', 'Afro-Asiatic', 'Semitic'),
            ('he', 'Hebrew', 'Afro-Asiatic', 'Semitic'),
            ('fi', 'Finnish', 'Uralic', 'Finnic'),
            ('hu', 'Hungarian', 'Uralic', 'Ugric'),
            ('tr', 'Turkish', 'Turkic', 'Oghuz'),
            ('ja', 'Japanese', 'Japonic', 'Japanese'),
            ('ko', 'Korean', 'Koreanic', 'Korean'),
            ('zh', 'Chinese', 'Sino-Tibetan', 'Sinitic'),
            ('vi', 'Vietnamese', 'Austroasiatic', 'Vietic')
        """)

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
