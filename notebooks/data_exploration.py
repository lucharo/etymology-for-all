import marimo

__generated_with = "0.18.4"
app = marimo.App(width="medium")


@app.cell
def _():
    from pathlib import Path

    import altair as alt
    import duckdb
    import marimo as mo

    return Path, alt, duckdb, mo


@app.cell
def _(mo):
    mo.md("""
    # Etymology Database Exploration

    This notebook explores the EtymDB dataset to understand:
    - Total word count and coverage
    - Distribution of etymology tree sizes
    - Language distribution
    - Data quality issues (phrases, proper nouns, etc.)
    """)
    return


@app.cell
def _(Path, duckdb):
    DB_PATH = Path(__file__).parent.parent / "backend" / "data" / "etymdb.duckdb"
    conn = duckdb.connect(DB_PATH.as_posix(), read_only=True)
    return (conn,)


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
    return


@app.cell
def _(alt, conn, mo):
    lang_df = conn.execute("""
        SELECT lang, COUNT(*) as count
        FROM words
        GROUP BY lang
        ORDER BY count DESC
        LIMIT 20
    """).pl()

    lang_chart = (
        alt.Chart(lang_df)
        .mark_bar()
        .encode(
            x=alt.X("count:Q", title="Word Count"),
            y=alt.Y("lang:N", title="Language", sort="-x"),
            tooltip=["lang", "count"],
        )
        .properties(title="Top 20 Languages by Word Count", width=500, height=400)
    )

    mo.vstack([mo.md("## Top 20 Languages by Word Count"), lang_chart])
    return


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
    return


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
    return


@app.cell
def _(conn, mo):
    no_etym_df = conn.execute("""
        SELECT w.lexeme as word
        FROM words w
        LEFT JOIN links l ON w.word_ix = l.source
        WHERE w.lang = 'en' AND l.source IS NULL
        ORDER BY RANDOM()
        LIMIT 50
    """).pl()

    mo.vstack(
        [
            mo.md("""
        ## Sample English Words WITHOUT Etymology Links

        These might be phrases, proper nouns, or just missing data:
        """),
            mo.ui.table(no_etym_df, selection=None),
        ]
    )
    return


@app.cell
def _(alt, conn, mo):
    rich_etym_df = conn.execute("""
        WITH tree_sizes AS (
            SELECT w.lexeme, w.word_ix, COUNT(DISTINCT l.target) as link_count
            FROM words w
            JOIN links l ON w.word_ix = l.source
            WHERE w.lang = 'en'
            GROUP BY w.lexeme, w.word_ix
            HAVING COUNT(DISTINCT l.target) >= 3
        )
        SELECT lexeme as word, link_count
        FROM tree_sizes
        ORDER BY link_count DESC
        LIMIT 50
    """).pl()

    rich_chart = (
        alt.Chart(rich_etym_df.head(20))
        .mark_bar()
        .encode(
            x=alt.X("link_count:Q", title="Direct Etymology Links"),
            y=alt.Y("word:N", title="Word", sort="-x"),
            tooltip=["word", "link_count"],
            color=alt.Color("link_count:Q", scale=alt.Scale(scheme="blues"), legend=None),
        )
        .properties(title="Top 20 English Words by Etymology Richness", width=400, height=400)
    )

    mo.vstack(
        [
            mo.md("## English Words with Rich Etymology (3+ direct links)"),
            mo.hstack(
                [rich_chart, mo.ui.table(rich_etym_df, selection=None)], justify="start", gap=2
            ),
        ]
    )
    return


@app.cell
def _(conn, mo):
    phrases_count = conn.execute("""
        SELECT COUNT(*)
        FROM words
        WHERE lang = 'en' AND lexeme LIKE '% %'
    """).fetchone()[0]

    phrase_samples_df = conn.execute("""
        SELECT lexeme as phrase
        FROM words
        WHERE lang = 'en' AND lexeme LIKE '% %'
        ORDER BY RANDOM()
        LIMIT 30
    """).pl()

    mo.vstack(
        [
            mo.md(f"""
        ## Potential Data Quality Issues

        ### Phrases (contain spaces): {phrases_count:,} total
        """),
            mo.ui.table(phrase_samples_df, selection=None),
        ]
    )
    return


@app.cell
def _(conn, mo):
    proper_count = conn.execute("""
        SELECT COUNT(*)
        FROM words
        WHERE lang = 'en'
        AND regexp_matches(lexeme, '^[A-Z][a-z]')
    """).fetchone()[0]

    proper_samples_df = conn.execute("""
        SELECT lexeme as word
        FROM words
        WHERE lang = 'en'
        AND regexp_matches(lexeme, '^[A-Z][a-z]')
        ORDER BY RANDOM()
        LIMIT 30
    """).pl()

    mo.vstack(
        [
            mo.md(f"### Potential Proper Nouns (capitalized): {proper_count:,} total"),
            mo.ui.table(proper_samples_df, selection=None),
        ]
    )
    return


@app.cell
def _(alt, conn, mo):
    link_types_df = conn.execute("""
        SELECT type, COUNT(*) as count
        FROM links
        GROUP BY type
        ORDER BY count DESC
    """).pl()

    link_types_chart = (
        alt.Chart(link_types_df)
        .mark_bar()
        .encode(
            x=alt.X("count:Q", title="Count"),
            y=alt.Y("type:N", title="Link Type", sort="-x"),
            tooltip=["type", "count"],
            color=alt.Color("type:N", legend=None),
        )
        .properties(title="Etymology Link Types Distribution", width=500, height=300)
    )

    mo.vstack([mo.md("## Etymology Link Types"), link_types_chart])
    return


@app.cell
def _(mo):
    mo.md("""
    ## Recommendations

    Based on this analysis:

    1. **Random should filter**: Only return English words that have etymology links
    2. **Consider filtering phrases**: Words with spaces are likely not useful
    3. **Highlight rich words**: Surface words with 3+ links as "interesting"
    4. **Stats page**: Show coverage and language distribution to users
    """)
    return


if __name__ == "__main__":
    app.run()
