SELECT w.word_ix, w.lang, w.lexeme, w.sense
FROM words w
LEFT JOIN links l ON l.source = w.word_ix
WHERE lower(w.lexeme) = lower(?)
GROUP BY w.word_ix, w.lang, w.lexeme, w.sense
ORDER BY
    CASE WHEN w.lang = 'en' THEN 0 ELSE 1 END,
    COUNT(l.target) DESC,
    w.word_ix
LIMIT 1
