-- Curated view: English words with etymology, no phrases/proper nouns
-- Filter out sense=NULL entries which are often garbage (e.g., suffix entries
-- like "-er" with corrupted links to unrelated words like "asteroid belt")
-- Paper notes 40% of EtymDB lacks glosses; our curated set is 99% with sense
CREATE OR REPLACE VIEW v_english_curated AS
SELECT DISTINCT w.*
FROM words w
JOIN links l ON w.word_ix = l.source
WHERE w.lang = 'en'
  AND is_clean_word(w.lexeme)
  AND w.sense IS NOT NULL;

-- View for words with "deep" etymology (at least one link to a real word)
-- Excludes compound-only words where all links point to sequences (negative IDs)
-- Also excludes sense=NULL entries (same rationale as v_english_curated)
CREATE OR REPLACE VIEW v_english_deep AS
SELECT DISTINCT w.*
FROM words w
JOIN links l ON w.word_ix = l.source
WHERE w.lang = 'en'
  AND is_clean_word(w.lexeme)
  AND w.sense IS NOT NULL
  AND l.target > 0;
