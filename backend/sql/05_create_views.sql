-- Curated view: English words with etymology, no phrases/proper nouns
CREATE OR REPLACE VIEW v_english_curated AS
SELECT DISTINCT w.*
FROM words w
JOIN links l ON w.word_ix = l.source
WHERE w.lang = 'en'
  AND is_clean_word(w.lexeme);
