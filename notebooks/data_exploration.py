import marimo

__generated_with = "0.18.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _(mo):
    mo.md(
        """
        # Etymology Database Exploration

        This notebook explores the EtymDB dataset to understand:
        - Total word count and coverage
        - Distribution of etymology tree sizes
        - Language distribution
        - Data quality issues (phrases, proper nouns, etc.)
        """
    )
    return


@app.cell
def _():
    import duckdb
    from pathlib import Path

    # Connect to the database
    DB_PATH = Path(__file__).parent.parent / "backend" / "data" / "etymdb.duckdb"
    conn = duckdb.connect(DB_PATH.as_posix(), read_only=True)
    return DB_PATH, Path, conn, duckdb


@app.cell
def _(conn, mo):
    # Basic counts
    total_words = conn.execute("SELECT COUNT(*) FROM words").fetchone()[0]
    total_links = conn.execute("SELECT COUNT(*) FROM links").fetchone()[0]
    unique_langs = conn.execute("SELECT COUNT(DISTINCT lang) FROM words").fetchone()[0]
    english_words = conn.execute("SELECT COUNT(*) FROM words WHERE lang = 'en'").fetchone()[0]

    mo.md(
        f"""
        ## Database Overview

        | Metric | Count |
        |--------|-------|
        | Total words | {total_words:,} |
        | Total etymology links | {total_links:,} |
        | Unique languages | {unique_langs:,} |
        | English words | {english_words:,} |
        """
    )
    return english_words, total_links, total_words, unique_langs


@app.cell
def _(conn, mo):
    # Language distribution (top 20)
    lang_dist = conn.execute("""
        SELECT lang, COUNT(*) as count
        FROM words
        GROUP BY lang
        ORDER BY count DESC
        LIMIT 20
    """).fetchall()

    lang_table = "| Language | Word Count |\n|----------|------------|\n"
    for _lang, _count in lang_dist:
        lang_table += f"| {_lang} | {_count:,} |\n"

    mo.md(
        f"""
        ## Top 20 Languages by Word Count

        {lang_table}
        """
    )
    return (lang_dist,)


@app.cell
def _(conn, mo):
    # Words with etymology links vs without
    words_with_links = conn.execute("""
        SELECT COUNT(DISTINCT source) FROM links
    """).fetchone()[0]

    words_as_targets = conn.execute("""
        SELECT COUNT(DISTINCT target) FROM links
    """).fetchone()[0]

    mo.md(
        f"""
        ## Etymology Link Coverage

        | Metric | Count |
        |--------|-------|
        | Words that have etymology (are sources) | {words_with_links:,} |
        | Words that are ancestors (are targets) | {words_as_targets:,} |
        """
    )
    return words_as_targets, words_with_links


@app.cell
def _(conn, mo):
    # English words with etymology trees
    en_with_links = conn.execute("""
        SELECT COUNT(DISTINCT w.word_ix)
        FROM words w
        JOIN links l ON w.word_ix = l.source
        WHERE w.lang = 'en'
    """).fetchone()[0]

    en_total = conn.execute("SELECT COUNT(*) FROM words WHERE lang = 'en'").fetchone()[0]
    coverage_pct = (en_with_links / en_total * 100) if en_total > 0 else 0

    mo.md(
        f"""
        ## English Word Etymology Coverage

        | Metric | Value |
        |--------|-------|
        | English words with etymology links | {en_with_links:,} |
        | Total English words | {en_total:,} |
        | **Coverage** | **{coverage_pct:.1f}%** |
        """
    )
    return coverage_pct, en_total, en_with_links


@app.cell
def _(conn, mo):
    # Sample words WITHOUT etymology (potential junk)
    no_etym_samples = conn.execute("""
        SELECT w.lexeme
        FROM words w
        LEFT JOIN links l ON w.word_ix = l.source
        WHERE w.lang = 'en' AND l.source IS NULL
        ORDER BY RANDOM()
        LIMIT 30
    """).fetchall()

    samples = [row[0] for row in no_etym_samples]

    mo.md(
        f"""
        ## Sample English Words WITHOUT Etymology Links

        These might be phrases, proper nouns, or just missing data:

        {', '.join(samples)}
        """
    )
    return no_etym_samples, samples


@app.cell
def _(conn, mo):
    # Sample words WITH rich etymology trees
    rich_etym = conn.execute("""
        WITH tree_sizes AS (
            SELECT w.lexeme, w.word_ix, COUNT(DISTINCT l.target) as link_count
            FROM words w
            JOIN links l ON w.word_ix = l.source
            WHERE w.lang = 'en'
            GROUP BY w.lexeme, w.word_ix
            HAVING COUNT(DISTINCT l.target) >= 3
        )
        SELECT lexeme, link_count
        FROM tree_sizes
        ORDER BY link_count DESC
        LIMIT 30
    """).fetchall()

    rich_table = "| Word | Direct Links |\n|------|-------------|\n"
    for _word, _count in rich_etym:
        rich_table += f"| {_word} | {_count} |\n"

    mo.md(
        f"""
        ## English Words with Rich Etymology (3+ direct links)

        {rich_table}
        """
    )
    return (rich_etym,)


@app.cell
def _(conn, mo):
    # Detect potential phrases (contain spaces)
    phrases = conn.execute("""
        SELECT COUNT(*)
        FROM words
        WHERE lang = 'en' AND lexeme LIKE '% %'
    """).fetchone()[0]

    phrase_samples = conn.execute("""
        SELECT lexeme
        FROM words
        WHERE lang = 'en' AND lexeme LIKE '% %'
        ORDER BY RANDOM()
        LIMIT 20
    """).fetchall()

    mo.md(
        f"""
        ## Potential Data Quality Issues

        ### Phrases (contain spaces)
        - Count: {phrases:,}
        - Samples: {', '.join([p[0] for p in phrase_samples])}
        """
    )
    return phrase_samples, phrases


@app.cell
def _(conn, mo):
    # Detect potential proper nouns (start with capital)
    proper_nouns = conn.execute("""
        SELECT COUNT(*)
        FROM words
        WHERE lang = 'en'
        AND lexeme GLOB '[A-Z]*'
        AND lexeme NOT GLOB '[A-Z][A-Z]*'
    """).fetchone()[0]

    proper_samples = conn.execute("""
        SELECT lexeme
        FROM words
        WHERE lang = 'en'
        AND lexeme GLOB '[A-Z]*'
        AND lexeme NOT GLOB '[A-Z][A-Z]*'
        ORDER BY RANDOM()
        LIMIT 20
    """).fetchall()

    mo.md(
        f"""
        ### Potential Proper Nouns (capitalized)
        - Count: {proper_nouns:,}
        - Samples: {', '.join([p[0] for p in proper_samples])}
        """
    )
    return proper_nouns, proper_samples


@app.cell
def _(conn, mo):
    # Link types distribution
    link_types = conn.execute("""
        SELECT type, COUNT(*) as count
        FROM links
        GROUP BY type
        ORDER BY count DESC
    """).fetchall()

    type_table = "| Link Type | Count |\n|-----------|-------|\n"
    for _ltype, _count in link_types:
        type_table += f"| {_ltype} | {_count:,} |\n"

    mo.md(
        f"""
        ## Etymology Link Types

        {type_table}
        """
    )
    return (link_types,)


@app.cell
def _(mo):
    mo.md(
        """
        ## Recommendations

        Based on this analysis:

        1. **Random should filter**: Only return English words that have etymology links
        2. **Consider filtering phrases**: Words with spaces are likely not useful
        3. **Highlight rich words**: Surface words with 3+ links as "interesting"
        4. **Stats page**: Show coverage and language distribution to users
        """
    )
    return


if __name__ == "__main__":
    app.run()
