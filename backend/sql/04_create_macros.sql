-- Macros for reusable filtering conditions
CREATE OR REPLACE MACRO is_phrase(lexeme) AS
    lexeme LIKE '% %';

CREATE OR REPLACE MACRO is_proper_noun(lexeme) AS
    regexp_matches(lexeme, '^[A-Z][a-z]');

CREATE OR REPLACE MACRO is_clean_word(lexeme) AS
    NOT is_phrase(lexeme) AND NOT is_proper_noun(lexeme);

CREATE OR REPLACE MACRO has_etymology(word_ix) AS
    word_ix IN (SELECT DISTINCT source FROM links);
