DROP TABLE IF EXISTS language_families;

CREATE TABLE language_families (
    lang_code VARCHAR PRIMARY KEY,
    lang_name VARCHAR,
    family VARCHAR,
    branch VARCHAR
)
