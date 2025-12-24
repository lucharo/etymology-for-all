-- Create links table from EtymDB links CSV
CREATE TABLE links AS
SELECT
    type,
    source::BIGINT AS source,
    target::BIGINT AS target
FROM read_csv_auto($csv_path, delim='\t', header=false, columns={
    'type': 'VARCHAR',
    'source': 'BIGINT',
    'target': 'BIGINT'
});
