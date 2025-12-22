"""Integration tests for the FastAPI application."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import duckdb
from fastapi.testclient import TestClient

TEMP_DIR = Path(tempfile.mkdtemp(prefix="etymdb-test-"))
os.environ["ETYM_DATA_DIR"] = str(TEMP_DIR)
os.environ["ETYM_DB_PATH"] = str(TEMP_DIR / "etymdb.duckdb")


def _prepare_test_database() -> None:
    db_path = Path(os.environ["ETYM_DB_PATH"])
    if db_path.exists():
        db_path.unlink()
    with duckdb.connect(db_path.as_posix()) as conn:
        conn.execute(
            "CREATE TABLE words (word_ix BIGINT, lang VARCHAR, lexeme VARCHAR, sense VARCHAR)"
        )
        conn.execute("CREATE TABLE links (type VARCHAR, source BIGINT, target BIGINT)")
        conn.executemany(
            "INSERT INTO words VALUES (?, ?, ?, ?)",
            [
                (1, "en", "mother", "mother"),
                (2, "proto-germanic", "mōdēr", "mother"),
                (3, "proto-indo-european", "méh₂tēr", "mother"),
                (4, "en", "loneword", "a word with no etymology links"),
                # Multiple entries for "twin" with different senses - both shown in search
                (100, "en", "twin", "twin sense A"),  # 1 link
                (101, "en", "twin", "twin sense B"),  # 3 links (graph uses richest)
                (102, "proto-germanic", "twinjaz", "twin"),
                (103, "proto-indo-european", "dwóh₁", "two"),
                (104, "la", "geminus", "twin"),
            ],
        )
        conn.executemany(
            "INSERT INTO links VALUES (?, ?, ?)",
            [
                ("inh", 1, 2),
                ("inh", 2, 3),
                # twin entry 100 has 1 link
                ("inh", 100, 102),
                # twin entry 101 has 3 links (richer etymology)
                ("inh", 101, 102),
                ("cog", 101, 103),
                ("cog", 101, 104),
                # Continue the chain
                ("inh", 102, 103),
            ],
        )
        conn.execute("CREATE INDEX idx_words_word_ix ON words(word_ix)")
        conn.execute("CREATE INDEX idx_words_lexeme ON words(lexeme)")
        conn.execute("CREATE INDEX idx_links_source ON links(source)")
        conn.execute("CREATE INDEX idx_links_target ON links(target)")

        # Gold layer: macros and views
        conn.execute("CREATE MACRO is_phrase(lexeme) AS lexeme LIKE '% %'")
        conn.execute("CREATE MACRO is_proper_noun(lexeme) AS regexp_matches(lexeme, '^[A-Z][a-z]')")
        conn.execute(
            "CREATE MACRO is_clean_word(lexeme) AS NOT is_phrase(lexeme) AND NOT is_proper_noun(lexeme)"
        )
        conn.execute("""
            CREATE VIEW v_english_curated AS
            SELECT DISTINCT w.*
            FROM words w
            JOIN links l ON w.word_ix = l.source
            WHERE w.lang = 'en' AND is_clean_word(w.lexeme)
        """)
        conn.execute("""
            CREATE TABLE language_families (
                lang_code VARCHAR PRIMARY KEY, lang_name VARCHAR, family VARCHAR, branch VARCHAR
            )
        """)

        # Definitions table (lexeme is lowercase for fast equality joins)
        conn.execute("""
            CREATE TABLE definitions (
                lexeme VARCHAR PRIMARY KEY,
                definition VARCHAR,
                part_of_speech VARCHAR,
                phonetic VARCHAR
            )
        """)
        conn.execute("""
            INSERT INTO definitions VALUES ('mother', 'A female parent', 'noun', NULL)
        """)


_prepare_test_database()

from backend.main import app  # noqa: E402  (import after DB creation)

client = TestClient(app)


def test_graph_endpoint_returns_nodes_and_edges():
    response = client.get("/graph/mother")
    assert response.status_code == 200
    payload = response.json()
    assert payload["nodes"]
    assert payload["edges"]
    # Node ID is now lexeme|lang format
    assert any(node["lexeme"] == "mother" for node in payload["nodes"])


def test_graph_endpoint_missing_word():
    response = client.get("/graph/unknownword")
    assert response.status_code == 404


def test_graph_endpoint_word_without_etymology():
    """Test that words with no etymology links return 404."""
    # "loneword" exists in DB but has no links, so it should return 404
    response = client.get("/graph/loneword")
    assert response.status_code == 404


def test_random_endpoint_returns_word():
    response = client.get("/random")
    assert response.status_code == 200
    # "mother" and "twin" are in v_english_curated (has etymology, is clean)
    # "loneword" has no etymology links so it's excluded
    assert response.json()["word"] in ["mother", "twin"]


def test_graph_picks_entry_with_most_links():
    """Test that when duplicate entries exist, we pick the one with most etymology links."""
    response = client.get("/graph/twin")
    assert response.status_code == 200
    payload = response.json()

    # twin entry 101 has 3 links, entry 100 has 1 link
    # We should get the richer graph (4 nodes: twin, twinjaz, dwóh₁, geminus)
    assert len(payload["nodes"]) == 4
    assert len(payload["edges"]) >= 3

    # Verify we have all expected nodes
    lexemes = {n["lexeme"] for n in payload["nodes"]}
    assert "twin" in lexemes
    assert "twinjaz" in lexemes
    assert "dwóh₁" in lexemes
    assert "geminus" in lexemes


def test_search_shows_all_valid_senses():
    """Test that search returns all entries with valid senses."""
    response = client.get("/search?q=twin")
    assert response.status_code == 200
    results = response.json()["results"]

    # Should show both "twin" entries since they have different senses
    twin_results = [r for r in results if r["word"] == "twin"]
    assert len(twin_results) == 2

    # Each should have its sense
    senses = {r["sense"] for r in twin_results}
    assert "twin sense A" in senses
    assert "twin sense B" in senses


def test_enriched_definition_used_for_english_words():
    """Test that enriched definitions from Free Dictionary API are used."""
    response = client.get("/graph/mother")
    assert response.status_code == 200
    payload = response.json()

    # Find the English "mother" node
    mother_node = next(
        (n for n in payload["nodes"] if n["lexeme"] == "mother" and n["lang"] == "en"), None
    )
    assert mother_node is not None

    # Should use enriched definition instead of EtymDB sense
    assert "sense" in mother_node
    assert mother_node["sense"] == "A female parent"
