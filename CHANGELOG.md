# Changelog

Human-readable history of the Etymology Graph Explorer.

---

## v0.3.0 - Gold Layer & Data Curation (2024-12-19)

### The Problem
Random word feature was nearly useless - only 6.7% of English words had etymology trees. Users would hit "random" and see single-node dead ends 93% of the time.

### Analysis (Marimo Notebook)
Explored the EtymDB dataset and found:
- **1.9M total words** across 2,536 languages
- **911K English words**, but only **61K (6.7%)** have etymology links
- **160K English entries are phrases** (with spaces) - not real words
- Many proper nouns polluting the dataset

### Solution: DuckDB "Gold Layer"
Added semantic macros for readable SQL:
```sql
is_phrase(lexeme)       -- contains spaces
is_proper_noun(lexeme)  -- starts with capital
is_clean_word(lexeme)   -- neither of above
```

Created curated view:
```sql
v_english_curated  -- 50K clean English words with etymology
```

Added reference data:
- `language_families` table mapping codes to names/families (en → English, Germanic, Indo-European)

### Result
- Random now returns **only words with etymology trees**
- Every random word leads to an interesting graph
- Foundation for richer language metadata in UI

---

## v0.2.0 - Frontend & Docker (2024-12-15)

### Added
- **Interactive frontend** with Cytoscape.js graph visualization
  - Search any word
  - Random word button
  - Color-coded language nodes
  - Hierarchical layout (modern → ancient)
- **FastAPI serves everything** - single process, no separate frontend server
- **Dockerfile** using official `uv` image (213MB)
- **Health check** endpoint at `/health`
- **README** with quick start instructions

### Architecture Decision
Chose single-process over Docker Compose:
- Simpler deployment
- FastAPI serves static files directly
- Good enough for personal/home server use
- Can add nginx later if needed

---

## v0.1.0 - Backend Foundation (2024-09-16)

### From PR #2
Merged the improved backend implementation:
- **FastAPI** with `/graph/{word}` and `/random` endpoints
- **DuckDB** for embedded database (no server needed)
- **EtymDB 2.1** dataset - auto-downloads on first run
- **Lazy initialization** - DB created when first accessed
- **Modern Python packaging** with `uv` and `pyproject.toml`

### Data Source
[EtymDB 2.1](https://github.com/clefourrier/EtymDB-2.0) - open etymological database derived from Wiktionary.

> Fourrier & Sagot (2020), "Methodological Aspects of Developing and Managing an Etymological Lexical Resource"

---

## Backlog

Open issues for future iterations:
- **#5** - Stats/about page showing database coverage
- **#6** - Consider filtering phrases from raw data
- **#7** - Compound word splitting (inter+nasal)
- **#8** - Language family metadata in graph UI
- **#3** - Hugging Face Space deployment
