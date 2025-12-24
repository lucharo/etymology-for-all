-- Create indexes for efficient queries
CREATE INDEX idx_words_word_ix ON words(word_ix);
CREATE INDEX idx_words_lexeme ON words(lexeme);
CREATE INDEX idx_links_source ON links(source);
CREATE INDEX idx_links_target ON links(target);
