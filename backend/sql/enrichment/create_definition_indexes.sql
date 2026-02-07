CREATE INDEX idx_definitions_lexeme ON definitions(lexeme);
CREATE INDEX idx_definitions_primary ON definitions(lexeme, entry_idx, meaning_idx, def_idx);
