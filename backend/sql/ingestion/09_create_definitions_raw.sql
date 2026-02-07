CREATE TABLE IF NOT EXISTS definitions_raw (
    lexeme VARCHAR PRIMARY KEY,
    api_response JSON,
    fetched_at TIMESTAMP,
    status VARCHAR
)
