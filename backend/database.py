from pathlib import Path
import duckdb
from typing import Dict, Optional

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'data' / 'etymdb.duckdb'

# open connection read-only
conn = duckdb.connect(DB_PATH.as_posix(), read_only=True)


def fetch_etymology(word: str, depth: int = 5) -> Optional[Dict]:
    """Return etymology graph for word or None if not found."""
    query_nodes = """
    WITH RECURSIVE search(child, parent, lvl) AS (
        SELECT w.word_ix, l.target, 1
        FROM words w
        JOIN links l ON w.word_ix = l.source
        WHERE lower(w.lexeme) = lower(? )
        UNION ALL
        SELECT l.source, l.target, lvl + 1
        FROM search s
        JOIN links l ON l.source = s.parent
        WHERE lvl < ?
    )
    SELECT DISTINCT word_ix FROM (
        SELECT child AS word_ix FROM search
        UNION
        SELECT parent AS word_ix FROM search
    )
    """
    ids = [r[0] for r in conn.execute(query_nodes, [word, depth]).fetchall()]
    if not ids:
        # check existence of starting word
        row = conn.execute("SELECT word_ix FROM words WHERE lower(lexeme)=lower(?)", [word]).fetchone()
        if not row:
            return None
        ids = [row[0]]

    placeholders = ','.join('?' for _ in ids)
    nodes_df = conn.execute(f"SELECT word_ix, lang, lexeme FROM words WHERE word_ix IN ({placeholders})", ids).fetchdf()
    nodes = [{"id": row.lexeme, "lang": row.lang} for row in nodes_df.itertuples(index=False)]

    query_edges = """
    WITH RECURSIVE search(child, parent, lvl) AS (
        SELECT w.word_ix, l.target, 1
        FROM words w
        JOIN links l ON w.word_ix = l.source
        WHERE lower(w.lexeme) = lower(? )
        UNION ALL
        SELECT l.source, l.target, lvl + 1
        FROM search s
        JOIN links l ON l.source = s.parent
        WHERE lvl < ?
    )
    SELECT child, parent FROM search
    """
    edges_df = conn.execute(query_edges, [word, depth]).fetchdf()
    edges = []
    for row in edges_df.itertuples(index=False):
        src = conn.execute("SELECT lexeme FROM words WHERE word_ix=?", [row.child]).fetchone()[0]
        dst = conn.execute("SELECT lexeme FROM words WHERE word_ix=?", [row.parent]).fetchone()[0]
        edges.append({"source": src, "target": dst})

    return {"nodes": nodes, "edges": edges}


def fetch_random_word() -> Dict[str, str]:
    row = conn.execute("SELECT lexeme FROM words WHERE lang='en' ORDER BY random() LIMIT 1").fetchone()
    return {"word": row[0] if row else None}
