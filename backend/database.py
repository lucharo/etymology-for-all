"""Database helpers for the FastAPI application."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

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


def _get_language_families(conn) -> dict[str, dict[str, str]]:
    """Load language families into a lookup dict."""
    rows = conn.execute(
        "SELECT lang_code, lang_name, family, branch FROM language_families"
    ).fetchall()
    return {row[0]: {"name": row[1], "family": row[2], "branch": row[3]} for row in rows}


def _get_definitions_for_lexemes(conn, lexemes: list[str]) -> dict[str, str]:
    """Fetch definitions only for the specified lexemes.

    Returns dict mapping lowercase lexeme -> definition string.
    """
    if not lexemes:
        return {}
    try:
        # Query only the specific lexemes we need
        placeholders = ",".join(["?" for _ in lexemes])
        rows = conn.execute(
            f"""
            SELECT lower(lexeme), definition
            FROM v_definitions
            WHERE lower(lexeme) IN ({placeholders}) AND definition IS NOT NULL
            """,
            [lex.lower() for lex in lexemes],
        ).fetchall()
        return {row[0]: row[1].strip('"') if row[1] else None for row in rows}
    except Exception:
        return {}


def _make_node_id(lexeme: str, lang: str) -> str:
    """Create a unique node ID combining lexeme and language."""
    return f"{lexeme}|{lang}"


def _build_node(
    lexeme: str,
    lang: str,
    sense: str,
    lang_families: dict,
    enriched_defs: dict[str, str] | None = None,
) -> dict:
    """Build a rich node with all available metadata.

    Args:
        lexeme: The word
        lang: Language code
        sense: EtymDB sense/definition
        lang_families: Language family lookup dict
        enriched_defs: Optional dict of enriched definitions from Free Dictionary API
    """
    node = {
        "id": _make_node_id(lexeme, lang),  # Unique ID includes language
        "lexeme": lexeme,  # Display name
        "lang": lang,
    }

    # Determine best definition to use
    # Priority: enriched definition (for English) > EtymDB sense
    definition = None
    if enriched_defs and lang == "en" and lexeme.lower() in enriched_defs:
        definition = enriched_defs[lexeme.lower()]
    elif sense and sense.lower() != lexeme.lower():
        definition = sense

    if definition:
        node["sense"] = definition

    # Add language metadata if available
    lang_info = lang_families.get(lang)
    if lang_info:
        node["lang_name"] = lang_info["name"]
        node["family"] = lang_info["family"]
        node["branch"] = lang_info["branch"]
    else:
        # Fallback: use lang code as name
        node["lang_name"] = lang
    return node


def fetch_etymology(word: str, depth: int = 5) -> dict | None:
    """Return an etymology graph for *word* or ``None`` if absent."""
    if not word:
        return None

    depth = _normalize_depth(depth)
    with _ConnectionManager() as conn:
        # Load language families (small table, 53 rows)
        lang_families = _get_language_families(conn)

        # Find starting word (prefer English, then most etymology links)
        start = conn.execute(
            """
            SELECT w.word_ix, w.lang, w.lexeme, w.sense
            FROM words w
            LEFT JOIN links l ON l.source = w.word_ix
            WHERE lower(w.lexeme) = lower(?)
            GROUP BY w.word_ix, w.lang, w.lexeme, w.sense
            ORDER BY
                CASE WHEN w.lang = 'en' THEN 0 ELSE 1 END,
                COUNT(l.target) DESC,
                w.word_ix
            LIMIT 1
            """,
            [word],
        ).fetchone()
        if not start:
            return None

        start_ix, start_lang, start_lexeme, start_sense = start

        # Collect all node data first (without definitions)
        raw_nodes: dict[int, tuple] = {start_ix: (start_lexeme, start_lang, start_sense)}
        edges = []
        seen_edges: set[tuple[str, str]] = set()

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
                    child.sense AS child_sense,
                    parent.word_ix AS parent_ix,
                    parent.lexeme AS parent_lexeme,
                    parent.lang AS parent_lang,
                    parent.sense AS parent_sense
                FROM traversal tr
                JOIN words child ON child.word_ix = tr.child_ix
                JOIN words parent ON parent.word_ix = tr.parent_ix
                """,
                [start_ix, depth],
            ).fetchall()

            for row in records:
                child_ix, child_lexeme, child_lang, child_sense = row[:4]
                parent_ix, parent_lexeme, parent_lang, parent_sense = row[4:]

                raw_nodes.setdefault(child_ix, (child_lexeme, child_lang, child_sense))
                raw_nodes.setdefault(parent_ix, (parent_lexeme, parent_lang, parent_sense))

                # Build edges
                child_id = _make_node_id(child_lexeme, child_lang)
                parent_id = _make_node_id(parent_lexeme, parent_lang)
                if child_id != parent_id:
                    edge_key = (child_id, parent_id)
                    if edge_key not in seen_edges:
                        seen_edges.add(edge_key)
                        edges.append({"source": child_id, "target": parent_id})

        # Fetch definitions only for English lexemes in this graph
        english_lexemes = [lex for lex, lang, _ in raw_nodes.values() if lang == "en"]
        enriched_defs = _get_definitions_for_lexemes(conn, english_lexemes)

        # Build final nodes with all metadata
        nodes = {
            ix: _build_node(lexeme, lang, sense, lang_families, enriched_defs)
            for ix, (lexeme, lang, sense) in raw_nodes.items()
        }

        # Return None if word has no etymology (single node, no edges)
        if not edges:
            return None

        return {"nodes": list(nodes.values()), "edges": edges}


def fetch_random_word() -> dict[str, str | None]:
    """Return a random curated English word (has etymology, no phrases/proper nouns)."""
    with _ConnectionManager() as conn:
        row = conn.execute(
            "SELECT lexeme FROM v_english_curated ORDER BY random() LIMIT 1"
        ).fetchone()
        return {"word": row[0] if row else None}


def fetch_language_info(lang_code: str) -> dict[str, str] | None:
    """Return language family info for a language code."""
    with _ConnectionManager() as conn:
        row = conn.execute(
            "SELECT lang_name, family, branch FROM language_families WHERE lang_code = ?",
            [lang_code],
        ).fetchone()
        if row:
            return {"name": row[0], "family": row[1], "branch": row[2]}
        return None


def fetch_all_language_families() -> dict[str, dict[str, str]]:
    """Return all language family mappings."""
    with _ConnectionManager() as conn:
        rows = conn.execute(
            "SELECT lang_code, lang_name, family, branch FROM language_families"
        ).fetchall()
        return {row[0]: {"name": row[1], "family": row[2], "branch": row[3]} for row in rows}


def _is_useful_sense(sense: str | None, lexeme: str) -> bool:
    """Check if a sense provides useful information beyond the lexeme itself."""
    if not sense:
        return False
    sense_lower = sense.lower().strip('"')
    lexeme_lower = lexeme.lower()
    # Not useful: NULL, empty, 'None', or equals lexeme
    return sense_lower not in ("", "none") and sense_lower != lexeme_lower


def search_words(query: str, limit: int = 10) -> list[dict[str, str]]:
    """Search for English words matching the query (fuzzy prefix search).

    Returns words with etymology data. Shows EtymDB sense when it differs
    from lexeme, otherwise falls back to Free Dictionary definition.
    When multiple senses exist for a word, shows all of them.
    """
    if not query or len(query) < 2:
        return []

    with _ConnectionManager() as conn:
        # Get all entries, then decide what sense/definition to show
        rows = conn.execute(
            """
            SELECT w.word_ix, w.lexeme, w.sense, d.definition
            FROM v_english_curated w
            LEFT JOIN v_definitions d ON lower(d.lexeme) = lower(w.lexeme)
            WHERE lower(w.lexeme) LIKE lower(?) || '%'
            ORDER BY
                CASE WHEN lower(w.lexeme) = lower(?) THEN 0 ELSE 1 END,
                length(w.lexeme),
                w.lexeme,
                w.word_ix
            """,
            [query, query],
        ).fetchall()

        # Build results: show all entries with useful different senses,
        # or deduplicate if senses are all the same/unhelpful
        results = []
        seen_lexemes: dict[str, list] = {}  # lexeme -> list of (sense, definition)

        for _word_ix, lexeme, sense, definition in rows:
            if lexeme not in seen_lexemes:
                seen_lexemes[lexeme] = []
            seen_lexemes[lexeme].append((sense, definition))

        for lexeme, entries in seen_lexemes.items():
            # Check if any entry has a useful different sense
            useful_senses = [(s, d) for s, d in entries if _is_useful_sense(s, lexeme)]

            if useful_senses:
                # Show all entries with useful senses
                for sense, _definition in useful_senses:
                    display = sense.strip('"') if sense else None
                    results.append({"word": lexeme, "sense": display})
            else:
                # No useful senses - show one entry with Free Dictionary definition
                definition = entries[0][1]  # First entry's definition
                display = definition.strip('"') if definition else None
                results.append({"word": lexeme, "sense": display})

            if len(results) >= limit:
                break

        return results[:limit]
