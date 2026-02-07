SELECT w.lexeme, w.sense, d.definition, d.part_of_speech, dc.def_count
FROM v_english_curated w
LEFT JOIN definitions d ON d.lexeme = lower(w.lexeme)
    AND d.entry_idx = 0 AND d.meaning_idx = 0 AND d.def_idx = 0
LEFT JOIN (
    SELECT lexeme, COUNT(*) as def_count
    FROM definitions
    GROUP BY lexeme
) dc ON dc.lexeme = lower(w.lexeme)
WHERE lower(w.lexeme) LIKE lower(?) || '%'
ORDER BY
    CASE WHEN lower(w.lexeme) = lower(?) THEN 0 ELSE 1 END,
    length(w.lexeme),
    w.lexeme,
    w.word_ix
