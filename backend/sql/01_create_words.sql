-- Create words table from EtymDB values CSV
CREATE TABLE words AS
SELECT
    word_ix::BIGINT AS word_ix,
    lang,
    lexeme,
    sense
FROM read_csv_auto($csv_path, delim='\t', header=false, columns={
    'word_ix': 'BIGINT',
    'lang': 'VARCHAR',
    'dummy': 'INTEGER',
    'lexeme': 'VARCHAR',
    'sense': 'VARCHAR'
});
