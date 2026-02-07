"""Integration tests for the FastAPI application.

NOTE: These tests use a real (ephemeral) DuckDB database rather than mocking.
This is not best practice for unit tests in a team/CI environment, but works
well for a single-developer project without CI. The tradeoff: we test that
our SQL actually works against the real schema, at the cost of coupling tests
to the database implementation.
"""

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
                # Meta-lexeme test: word with sense appears in search
                (200, "en", "friend", "companion"),  # English word with real sense
                (201, "de", "Freund", "friend"),  # German cognate
                (202, "proto-germanic", "frijōndz", "friend"),  # Proto-Germanic ancestor
                # Compound word test: sense=NULL entries with garbage links
                (300, "en", "uplander", "highland dweller"),  # Compound word
                (301, "en", "upland", "elevated land"),  # Regular part
                (302, "en", "-er", None),  # Morpheme with sense=NULL (garbage links)
                (303, "en", "garbage1", "unrelated word 1"),  # Garbage target
                (304, "en", "garbage2", "unrelated word 2"),  # Garbage target
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
                # Meta-lexeme: cognates point TO it (incoming links)
                ("cog", 201, 200),  # German "Freund" -> English "friend" (meta-lexeme)
                # Meta-lexeme also has outgoing etymology
                ("inh", 200, 202),  # friend inherited from Proto-Germanic
                # Compound: uplander -> sequence -> [upland, -er]
                ("der", 300, -1),  # uplander links to sequence -1
                # Garbage links FROM -er (sense=NULL) - should NOT be traversed
                ("der", 302, 303),  # -er -> garbage1
                ("der", 302, 304),  # -er -> garbage2
            ],
        )

        # Sequences table (maps negative IDs to compound etymologies)
        # Must be created before inserting sequence data
        conn.execute("""
            CREATE TABLE sequences (
                seq_ix BIGINT,
                position INT,
                parent_ix BIGINT
            )
        """)
        # Add sequence for compound word
        conn.executemany(
            "INSERT INTO sequences VALUES (?, ?, ?)",
            [
                (-1, 0, 301),  # sequence -1, position 0 -> upland
                (-1, 1, 302),  # sequence -1, position 1 -> -er
            ],
        )

        conn.execute("CREATE INDEX idx_words_word_ix ON words(word_ix)")
        conn.execute("CREATE INDEX idx_words_lexeme ON words(lexeme)")
        conn.execute("CREATE INDEX idx_links_source ON links(source)")
        conn.execute("CREATE INDEX idx_links_target ON links(target)")
        conn.execute("CREATE INDEX idx_sequences_seq_ix ON sequences(seq_ix)")

        # Gold layer: macros and views
        conn.execute("CREATE MACRO is_phrase(lexeme) AS lexeme LIKE '% %'")
        conn.execute("CREATE MACRO is_proper_noun(lexeme) AS regexp_matches(lexeme, '^[A-Z][a-z]')")
        conn.execute(
            "CREATE MACRO is_clean_word(lexeme) AS NOT is_phrase(lexeme) AND NOT is_proper_noun(lexeme)"
        )
        # Filter out sense=NULL entries which have garbage etymology links
        conn.execute("""
            CREATE VIEW v_english_curated AS
            SELECT DISTINCT w.*
            FROM words w
            JOIN links l ON w.word_ix = l.source
            WHERE w.lang = 'en' AND is_clean_word(w.lexeme) AND w.sense IS NOT NULL
        """)
        # View for words with "deep" etymology (at least one positive target)
        conn.execute("""
            CREATE VIEW v_english_deep AS
            SELECT DISTINCT w.*
            FROM words w
            JOIN links l ON w.word_ix = l.source
            WHERE w.lang = 'en' AND is_clean_word(w.lexeme) AND w.sense IS NOT NULL AND l.target > 0
        """)
        conn.execute("""
            CREATE TABLE language_families (
                lang_code VARCHAR PRIMARY KEY, lang_name VARCHAR, family VARCHAR, branch VARCHAR
            )
        """)

        # Definitions table with all definitions (not just first)
        # Schema matches materialize_definitions() in enrich_definitions.py
        conn.execute("""
            CREATE TABLE definitions (
                lexeme VARCHAR,
                definition VARCHAR,
                part_of_speech VARCHAR,
                entry_idx INT,
                meaning_idx INT,
                def_idx INT
            )
        """)
        conn.execute("CREATE INDEX idx_definitions_lexeme ON definitions(lexeme)")
        conn.execute(
            "CREATE INDEX idx_definitions_primary ON definitions(lexeme, entry_idx, meaning_idx, def_idx)"
        )
        # Insert test definitions - primary definition (entry=0, meaning=0, def=0)
        conn.execute("""
            INSERT INTO definitions VALUES ('mother', 'A female parent', 'noun', 0, 0, 0)
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


def test_graph_endpoint_returns_404_for_missing_word():
    """Test that graph returns 404 for words not in the database."""
    response = client.get("/graph/unknownword")
    assert response.status_code == 404


def test_graph_endpoint_returns_no_etymology_for_loneword():
    """Test that graph returns 200 with no_etymology flag for words without links."""
    response = client.get("/graph/loneword")
    assert response.status_code == 200
    payload = response.json()
    assert payload["no_etymology"] is True
    assert payload["lexeme"] == "loneword"
    assert len(payload["nodes"]) == 1
    assert payload["edges"] == []


def test_random_endpoint_returns_word():
    response = client.get("/random")
    assert response.status_code == 200
    # "mother", "twin", "friend", and "uplander" are in v_english_curated (has etymology, is clean)
    # "loneword" has no etymology links so it's excluded
    assert response.json()["word"] in ["mother", "twin", "friend", "uplander"]


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


def test_search_shows_etymdb_sense():
    """Test that search returns EtymDB sense when available.

    Words with meaningful senses (not NULL, not equal to lexeme) show that sense.
    """
    response = client.get("/search?q=friend")
    assert response.status_code == 200
    results = response.json()["results"]

    # Should find the "friend" entry
    friend_results = [r for r in results if r["word"] == "friend"]
    assert len(friend_results) == 1

    # Should show the EtymDB sense
    assert friend_results[0]["sense"] == "companion"


def test_compound_includes_morpheme_but_not_garbage_links():
    """Test that compound words include sense=NULL morphemes but don't traverse their garbage links.

    Regression test for PR #41: -er, -al, -ic etc. with sense=NULL had garbage etymology
    links to unrelated words. Fix: include morphemes as nodes but don't follow their links.
    """
    response = client.get("/graph/uplander")
    assert response.status_code == 200
    payload = response.json()

    lexemes = {n["lexeme"] for n in payload["nodes"]}

    # Should include the compound parts
    assert "uplander" in lexemes, "Main word should be in graph"
    assert "upland" in lexemes, "Regular compound part should be in graph"
    assert "-er" in lexemes, "Morpheme with sense=NULL should still be in graph"

    # Should NOT include garbage words linked FROM sense=NULL entry
    assert "garbage1" not in lexemes, "Should not traverse links FROM sense=NULL entries"
    assert "garbage2" not in lexemes, "Should not traverse links FROM sense=NULL entries"

    # Verify we have the expected number of nodes (uplander, upland, -er = 3)
    assert len(payload["nodes"]) == 3


def test_health_check_returns_db_stats():
    """Test that health check verifies database connectivity."""
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert "db" in payload
    assert payload["db"]["words"] >= 1
    assert payload["db"]["definitions"] >= 1


def test_version_endpoint():
    """Test that version endpoint returns version and db_stats."""
    response = client.get("/version")
    assert response.status_code == 200
    payload = response.json()
    assert "version" in payload
    assert "db_stats" in payload
    assert payload["db_stats"]["words"] >= 1


def test_edges_include_link_type():
    """Test that edges include the link type from the database."""
    response = client.get("/graph/mother")
    assert response.status_code == 200
    payload = response.json()
    # mother -> mōdēr is an "inh" (inherited) link
    for edge in payload["edges"]:
        assert "type" in edge, f"Edge {edge} missing 'type' field"
    inh_edges = [e for e in payload["edges"] if e["type"] == "inh"]
    assert len(inh_edges) >= 1


def test_edges_include_compound_and_type():
    """Test that compound edges have both compound flag and link type."""
    response = client.get("/graph/uplander")
    assert response.status_code == 200
    payload = response.json()
    compound_edges = [e for e in payload["edges"] if e.get("compound")]
    assert len(compound_edges) >= 1
    for edge in compound_edges:
        assert "type" in edge
