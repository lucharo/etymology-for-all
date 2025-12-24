-- Language families reference table
-- Data is loaded from language_codes.json by Python
CREATE TABLE language_families (
    lang_code VARCHAR PRIMARY KEY,
    lang_name VARCHAR,
    family VARCHAR,
    branch VARCHAR
);
