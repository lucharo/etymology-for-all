DROP TABLE IF EXISTS definitions;
DROP VIEW IF EXISTS v_definitions;

CREATE TABLE definitions AS
WITH entries AS (
    SELECT
        lower(lexeme) as lexeme,
        unnest(from_json(api_response, '["json"]')) as entry,
        generate_subscripts(from_json(api_response, '["json"]'), 1) - 1 as entry_idx
    FROM definitions_raw
    WHERE status = 'success'
),
meanings AS (
    SELECT
        lexeme, entry_idx,
        unnest(from_json(json_extract(entry, '$.meanings'), '["json"]')) as meaning,
        generate_subscripts(from_json(json_extract(entry, '$.meanings'), '["json"]'), 1) - 1 as meaning_idx
    FROM entries
),
defs AS (
    SELECT
        lexeme, entry_idx, meaning_idx,
        json_extract_string(meaning, '$.partOfSpeech') as part_of_speech,
        unnest(from_json(json_extract(meaning, '$.definitions'), '["json"]')) as def,
        generate_subscripts(from_json(json_extract(meaning, '$.definitions'), '["json"]'), 1) - 1 as def_idx
    FROM meanings
)
SELECT
    lexeme,
    json_extract_string(def, '$.definition') as definition,
    part_of_speech,
    entry_idx,
    meaning_idx,
    def_idx
FROM defs
WHERE json_extract_string(def, '$.definition') IS NOT NULL
