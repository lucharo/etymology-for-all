-- Table to store raw API responses from Free Dictionary API
-- After enrichment, run --materialize to create the definitions table
CREATE TABLE IF NOT EXISTS definitions_raw (
    lexeme VARCHAR PRIMARY KEY,
    api_response JSON,
    fetched_at TIMESTAMP,
    status VARCHAR
);
