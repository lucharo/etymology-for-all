# Changelog

Human-readable history of the Etymology Graph Explorer.

---

## v0.5.0 - Definition Enrichment & Mobile UI (2024-12-20)

### Definition Enrichment
- **21,268 definitions** fetched from Free Dictionary API (53% of curated words)
- Definitions display in detail panel when clicking graph nodes
- Truncation for long definitions (60 chars in autocomplete, 150 in detail panel)
- ELT pipeline: raw API responses stored in `definitions_raw` table, transformed via `v_definitions` view

### New Files
- `backend/enrich_definitions.py` - Async script to fetch definitions with retry logic and resume capability

### Mobile UI Improvements
- Search bar stays on one row with compact icon buttons
- Graph container takes more vertical space (50vh minimum)
- Detail panel slides up from bottom as a sheet on mobile
- Compact info bar, header, and footer spacing

### UI Enhancements
- Added hint text: "Click any word in the graph to see its definition"
- Updated footer with both data source credits
- Updated About modal with clearer data source documentation

---

## v0.4.1 - Data Quality & Search Enhancements (2024-12-19)

### Data Quality Discovery
Found significant data quality issues in EtymDB 2.1:
- **80,921 broken links** pointing to non-existent word entries (negative or missing `word_ix`)
- **9,501 "ghost" words** in the curated view that appeared to have etymology but only had broken links
- **895,288 pseudo-definitions** where "sense" field just repeats the word (e.g., "Cockaigne" for "cockaigne")

### Definition Coverage Analysis
| Dataset | Total | With Meaningful Definition | Coverage |
|---------|-------|---------------------------|----------|
| Full database (all languages) | 1,885,106 | 233,751 | 12.4% |
| Curated English words | 40,456 | 226 | **0.6%** |

Best coverage by language: Ancient Greek (55.3%), Latin (42.8%), German (20.5%)

### Fixes
- **Updated `v_english_curated` view** to require valid target words (JOIN on target existence)
- **Curated word count**: ~50K → ~40K (removed entries with only broken links)
- **Graph lookup prefers English** - prevents showing French/other language roots when English version exists
- **Case-insensitive definition filtering** - "Cockaigne" no longer shown as definition for "cockaigne"

### Search Enhancements
- **Ancestor count in autocomplete** - each suggestion shows "X ancestors" or "no etymology"
- Helps users identify words with rich vs sparse etymology trees before searching

---

## v0.4.0 - Polish & Accessibility (2024-12-19)

### Improvements
- **Garamond typography** - elegant serif font in graph nodes and detail panel
- **Accessible design** - removed color-coding (better for colorblind users)
- **Fuzzy search** - type to see autocomplete suggestions with meanings
- **Language breakdown** - info bar shows "Ancient Greek 4, Latin 2, English 1"
- **About modal** - explains the project philosophy and how it works
- **Info tooltips** - hover over "Family" to learn what it means
- **Fixed graph loops** - unique node IDs (`lexeme|lang`) prevent same-spelling cross-language words from creating visual loops
- **Direction indicator** - shows "Recent → Ancient" timeline orientation (adapts to horizontal/vertical layout)

### Node Display
- Language at top (uppercase for visual hierarchy)
- Word as main focus (Garamond serif)
- Meaning in quotes below

### Detail Panel Redesign
- Language name at top (smaller, uppercase)
- Word in bold Garamond
- Meaning in italics
- Family with tooltip explanation

### About Page Content
- **Philosophy**: "Etymology should be a public good"
- **How It Works**: Data pipeline explanation, graph reading guide, limitations

---

## v0.3.1 - Rich Node Information (2024-12-19)

### The Problem
Graph nodes were "so basic" - just showing words with color-coded language. Users couldn't learn anything meaningful about word meanings or language relationships.

### Solution: Enhanced API & Interactive UI
Updated `fetch_etymology()` to include:
- **Sense/definitions** from EtymDB (60% coverage)
- **Language names** (not just codes like "grc" → "Ancient Greek")
- **Language family & branch** (Indo-European → Hellenic)

Frontend improvements:
- **Multi-line node labels** showing word + language name
- **Click-to-inspect detail panel** with:
  - Word and full language name
  - Language family tree (e.g., "Indo-European → Germanic")
  - Meaning/definition when available
- **Visual indicator** for nodes with definitions (thicker border)

### Result
Searching "etymology" now teaches you:
- English → Middle English → Old French → Latin → Ancient Greek
- Greek root ἔτυμος means "true, real, actual"
- Every node is clickable with contextual information

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
