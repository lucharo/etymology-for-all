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
