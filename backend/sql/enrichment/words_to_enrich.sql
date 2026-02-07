SELECT DISTINCT c.lexeme
FROM v_english_curated c
LEFT JOIN definitions_raw d ON c.lexeme = d.lexeme
WHERE d.lexeme IS NULL
ORDER BY c.lexeme
