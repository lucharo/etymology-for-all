from pathlib import Path
import duckdb
import pandas as pd
try:
    from .download_data import download
except ImportError:  # fallback when run as script
    from download_data import download

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'data' / 'etymdb.duckdb'
VALUES_CSV = BASE_DIR / 'data' / 'etymdb_values.csv'
LINKS_CSV = BASE_DIR / 'data' / 'etymdb_links_info.csv'


def main():
    if not VALUES_CSV.exists() or not LINKS_CSV.exists():
        download()
    conn = duckdb.connect(DB_PATH.as_posix())
    # Drop existing tables for idempotency
    conn.execute("DROP TABLE IF EXISTS words")
    conn.execute("DROP TABLE IF EXISTS links")

    df_words = pd.read_csv(VALUES_CSV, sep='\t', header=None,
                           names=['word_ix', 'lang', 'dummy', 'lexeme', 'sense'])
    df_links = pd.read_csv(LINKS_CSV, sep='\t', header=None,
                           names=['type', 'source', 'target'])

    conn.register('df_words', df_words)
    conn.register('df_links', df_links)

    conn.execute('CREATE TABLE words AS SELECT * FROM df_words')
    conn.execute('CREATE TABLE links AS SELECT * FROM df_links')

    conn.execute('CREATE INDEX IF NOT EXISTS idx_word_ix ON words(word_ix)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_lexeme ON words(lexeme)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_links_source ON links(source)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_links_target ON links(target)')
    conn.close()


if __name__ == '__main__':
    main()
