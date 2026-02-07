WITH RECURSIVE
-- Resolve negative targets through sequences table
resolved_links AS (
    -- Simple links (positive target = direct word reference)
    SELECT source, target AS parent_ix, FALSE AS is_compound, type
    FROM links
    WHERE target > 0
    UNION ALL
    -- Compound links (negative target = sequence, resolve to parents)
    SELECT l.source, s.parent_ix, TRUE AS is_compound, l.type
    FROM links l
    JOIN sequences s ON s.seq_ix = l.target
    WHERE l.target < 0
),
traversal(child_ix, parent_ix, is_compound, type, lvl) AS (
    SELECT source, parent_ix, is_compound, type, 1
    FROM resolved_links
    WHERE source = ?
    UNION ALL
    -- Only follow FROM parents that have valid sense (non-NULL for English)
    -- This keeps sense=NULL entries as nodes but doesn't traverse their garbage links
    SELECT rl.source, rl.parent_ix, rl.is_compound, rl.type, lvl + 1
    FROM traversal t
    JOIN resolved_links rl ON rl.source = t.parent_ix
    JOIN words parent_word ON parent_word.word_ix = t.parent_ix
    WHERE lvl < ?
      AND (parent_word.lang != 'en' OR parent_word.sense IS NOT NULL)
)
SELECT
    child.word_ix AS child_ix,
    child.lexeme AS child_lexeme,
    child.lang AS child_lang,
    child.sense AS child_sense,
    parent.word_ix AS parent_ix,
    parent.lexeme AS parent_lexeme,
    parent.lang AS parent_lang,
    parent.sense AS parent_sense,
    tr.is_compound,
    tr.type
FROM traversal tr
JOIN words child ON child.word_ix = tr.child_ix
JOIN words parent ON parent.word_ix = tr.parent_ix
