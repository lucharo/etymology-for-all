"""Enrich etymology database with definitions from Free Dictionary API.

Usage:
    uv run python -m backend.enrich_definitions          # Run full enrichment
    uv run python -m backend.enrich_definitions --stats  # Check progress
    uv run python -m backend.enrich_definitions --test 50  # Test with 50 words
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime

import duckdb

try:
    import aiohttp
except ImportError:
    print("aiohttp is required. Install with: uv add aiohttp")
    sys.exit(1)

try:
    from .database import database_path
except ImportError:
    from database import database_path

API_BASE = "https://api.dictionaryapi.dev/api/v2/entries/en"
DELAY_MS = 300  # Delay between requests
COMMIT_EVERY = 100  # Commit to DB every N words


async def fetch_definition(session: aiohttp.ClientSession, word: str) -> tuple[str, str, str | None]:
    """Fetch definition for a single word with retry logic."""
    url = f"{API_BASE}/{word}"

    for attempt in range(3):
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return (word, "success", json.dumps(data))
                elif resp.status == 404:
                    return (word, "not_found", None)
                elif resp.status == 429:  # Rate limited
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    if attempt < 2:
                        await asyncio.sleep(1)
                        continue
                    return (word, "error", None)
        except Exception as e:
            if attempt < 2:
                await asyncio.sleep(1)
                continue
            print(f"  Error fetching '{word}': {e}")
            return (word, "error", None)

    return (word, "error", None)


def get_words_to_enrich(conn: duckdb.DuckDBPyConnection) -> list[str]:
    """Get curated English words that haven't been enriched yet."""
    tables = conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_name = 'definitions_raw'"
    ).fetchall()

    if not tables:
        rows = conn.execute(
            "SELECT DISTINCT lexeme FROM v_english_curated ORDER BY lexeme"
        ).fetchall()
    else:
        rows = conn.execute("""
            SELECT DISTINCT c.lexeme
            FROM v_english_curated c
            LEFT JOIN definitions_raw d ON c.lexeme = d.lexeme
            WHERE d.lexeme IS NULL
            ORDER BY c.lexeme
        """).fetchall()

    return [row[0] for row in rows]


def ensure_definitions_table(conn: duckdb.DuckDBPyConnection) -> None:
    """Create definitions_raw table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS definitions_raw (
            lexeme VARCHAR PRIMARY KEY,
            api_response JSON,
            fetched_at TIMESTAMP,
            status VARCHAR
        )
    """)
    conn.execute("""
        CREATE OR REPLACE VIEW v_definitions AS
        SELECT
            lexeme,
            CAST(api_response->'$[0]'->'meanings'->'$[0]'->'definitions'->'$[0]'->'definition' AS VARCHAR) as definition,
            CAST(api_response->'$[0]'->'meanings'->'$[0]'->'partOfSpeech' AS VARCHAR) as part_of_speech,
            CAST(api_response->'$[0]'->'phonetic' AS VARCHAR) as phonetic
        FROM definitions_raw
        WHERE status = 'success'
    """)


def store_result(conn: duckdb.DuckDBPyConnection, word: str, status: str, api_response: str | None) -> None:
    """Store a single result in the database."""
    conn.execute(
        "INSERT OR REPLACE INTO definitions_raw (lexeme, api_response, fetched_at, status) VALUES (?, ?::JSON, ?, ?)",
        [word, api_response, datetime.now().isoformat(), status],
    )


async def enrich_definitions(max_words: int | None = None) -> None:
    """Fetch definitions for all curated English words."""
    db_path = database_path()
    print(f"Database: {db_path}\n")

    # Get words to enrich
    with duckdb.connect(db_path.as_posix(), read_only=True) as conn:
        words = get_words_to_enrich(conn)

    if max_words:
        words = words[:max_words]

    total = len(words)
    if total == 0:
        print("All words already enriched!")
        return

    print(f"Words to enrich: {total:,}")
    print(f"Estimated time: {(total * DELAY_MS) / 1000 / 60:.1f} minutes\n")

    stats = {"success": 0, "not_found": 0, "error": 0}
    start_time = time.time()

    with duckdb.connect(db_path.as_posix()) as conn:
        ensure_definitions_table(conn)

        async with aiohttp.ClientSession() as session:
            for i, word in enumerate(words):
                result = await fetch_definition(session, word)
                _, status, api_response = result
                stats[status] += 1
                store_result(conn, word, status, api_response)

                # Progress every 50 words
                if (i + 1) % 50 == 0 or i + 1 == total:
                    elapsed = time.time() - start_time
                    rate = (i + 1) / elapsed if elapsed > 0 else 0
                    remaining = (total - i - 1) / rate if rate > 0 else 0
                    print(f"[{i+1:,}/{total:,}] {100*(i+1)/total:.1f}% - {rate:.1f}/sec - ETA: {remaining/60:.1f}m")

                # Commit periodically
                if (i + 1) % COMMIT_EVERY == 0:
                    conn.commit()

                # Rate limiting
                if i < total - 1:
                    await asyncio.sleep(DELAY_MS / 1000)

            conn.commit()

    elapsed = time.time() - start_time
    print(f"\nDone! {total:,} words in {elapsed/60:.1f}m ({total/elapsed:.1f}/sec)")
    print(f"  Success: {stats['success']:,}, Not found: {stats['not_found']:,}, Errors: {stats['error']:,}")


def get_stats() -> None:
    """Show current enrichment statistics."""
    db_path = database_path()

    with duckdb.connect(db_path.as_posix(), read_only=True) as conn:
        tables = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_name = 'definitions_raw'"
        ).fetchall()

        if not tables:
            print("No definitions_raw table yet. Run enrichment first.")
            return

        total_curated = conn.execute("SELECT COUNT(DISTINCT lexeme) FROM v_english_curated").fetchone()[0]
        stats = conn.execute("SELECT status, COUNT(*) FROM definitions_raw GROUP BY status").fetchall()

        total_enriched = sum(s[1] for s in stats)
        remaining = total_curated - total_enriched

        print(f"Curated English words: {total_curated:,}")
        print(f"Enriched: {total_enriched:,} ({100*total_enriched/total_curated:.1f}%)")
        print(f"Remaining: {remaining:,}\n")
        print("By status:")
        for status, count in stats:
            print(f"  {status}: {count:,}")


def main():
    parser = argparse.ArgumentParser(description="Enrich etymology database with definitions")
    parser.add_argument("--stats", action="store_true", help="Show enrichment statistics")
    parser.add_argument("--test", type=int, metavar="N", help="Test mode: only process N words")
    args = parser.parse_args()

    if args.stats:
        get_stats()
    else:
        asyncio.run(enrich_definitions(max_words=args.test))


if __name__ == "__main__":
    main()
