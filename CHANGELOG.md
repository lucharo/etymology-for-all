# Changelog

Human-readable history of the Etymology Graph Explorer.

---

## v0.10.0 - Compound Etymology Support (2024-12-25) 🎄

### Critical Discovery: "Broken Links" Were Compound Etymologies!

In v0.4.1, we documented "80,921 broken links pointing to non-existent word entries (negative `word_ix`)". **This was wrong!** After reading the [EtymDB 2.0 academic paper](https://aclanthology.org/2020.lrec-1.392/), we discovered:

- **Negative IDs are lexeme sequences** - references to compound etymologies involving multiple source words
- **80,265 lexeme sequences** exist in EtymDB for words derived from 2+ parent words
- Example: "encyclopedia" comes from Greek ἐγκύκλιος (enkyklios) + παιδείᾱ (paideia)
- Example: "memoriousness" = "memorious" + "-ness"

These aren't broken data - they're **rich compound etymologies** we weren't loading!

### Fixes

- **Added `etymdb_links_index.csv`** - third data file mapping sequence IDs to parent words
- **New `sequences` table** in DuckDB with normalized structure:
  - `seq_ix`: Negative sequence ID (e.g., -1, -2)
  - `position`: Order of parent (0 = first, 1 = second, etc.)
  - `parent_ix`: Positive word ID of parent word
- **Updated etymology traversal** to resolve negative targets through sequences
- **165,093 sequence entries** now properly loaded (80K sequences × ~2 parents each)

### Data Pipeline Changes

| File | Records | Purpose |
|------|---------|---------|
| `etymdb_values.csv` | 1.9M | Words (id, lang, lexeme, sense) |
| `etymdb_links_info.csv` | 700K | Etymology links (type, source, target) |
| `etymdb_links_index.csv` | 80K | **NEW**: Sequence definitions (seq_id → parents) |

### Impact

Words with compound etymologies now show their full ancestry instead of 404 errors. This significantly improves the random word feature and graph completeness.

### Files Modified
- `backend/download_data.py` - Downloads third CSV file
- `backend/ingest.py` - Creates normalized sequences table
- `backend/database.py` - Resolves compound etymologies in graph traversal
- `backend/tests/test_api.py` - Added sequences table to test fixtures

---

## v0.9.0 - Language Name Mappings (2024-12-23)

### Language Display
- **11,195 language code mappings** from combined sources
- **96.6% coverage** of EtymDB's 2,536 unique language codes (2,449 mapped)
- Proto-languages like `gem-pro` → "Proto-Germanic", `ine-pro` → "Proto-Indo-European"
- Historical languages like `ofs` → "Old Frisian", `xcl` → "Classical Armenian"

### Data Sources
Combined mappings from:
- ISO 639-3 official registry (SIL International)
- ISO 639-1 two-letter codes
- Wiktionary languages module (code_to_canonical_name.json)
- Wiktionary etymology languages module
- Wiktionary language families module (includes proto-languages)

### Files Added
- `backend/download_language_codes.py` - Script to fetch and combine language codes

---

## v0.8.0 - Graph Controls & ES Modules (2024-12-23)

### Graph Interaction
- **Depth controls** - Adjust graph depth with +/- buttons to explore more or fewer ancestors
- **Expand/minimize** - Full-screen graph view with backdrop overlay
- **Stats panel** - Toggle to see node count, edge count, language count, and graph depth

### Code Architecture
- **ES Modules refactor** - Split monolithic `app.js` (800+ lines) into focused modules:
  - `utils.js` - Language names, truncation, API error handling
  - `graph.js` - Cytoscape initialization, rendering, depth filtering with BFS
  - `search.js` - Search, autocomplete, suggestions
  - `ui.js` - State management, modals, expand/minimize handlers
  - `app.js` - Main entry point, DOM references, event wiring

### Frontend Error Handling
- User-friendly error messages for rate limiting (429), not found (404), server errors (5xx)
- Retry-After header displayed for rate limit errors

---

## v0.7.0 - HF Spaces Deployment (2024-12-21)

### Deployment Infrastructure
- **Hugging Face Spaces** hosting with Docker SDK
- **Makefile** with `hf-init` (one-time) and `hf-deploy` targets
- Git remote workflow: push code via git, upload DuckDB via HF API (handles large files)

### Custom Domain (Cloudflare Worker)
- **Cloudflare Worker** proxy in `cloudflare-worker/` for custom domain support
- `etymology.luischav.es` → proxies to `lucharo-etymology.hf.space`
- Deploy via `make cf-deploy`

### Simplified Architecture
- Removed CORS middleware (not needed with same-origin serving)
- Frontend uses relative URLs (FastAPI serves both API + static files)
- DuckDB baked into Docker image for instant cold starts

### Files Added
- `Makefile` - HF Spaces deployment automation
- `cloudflare-worker/worker.js` - Proxy worker (10 lines)
- `cloudflare-worker/wrangler.toml` - Worker config with custom domain

---

## v0.6.0 - Load Testing & Rate Limiting (2024-12-20)

### Load Testing Infrastructure
- **Locust load testing** in `research/load-testing/` for API performance analysis
- Documented per-IP rate limiting behavior and how it scales with concurrent users
- Comprehensive README explaining rate limiting concepts and test methodology

### Performance Optimization
- **3.6x faster `/graph` endpoint** (1900ms → 530ms median)
- Root cause: was loading ALL 40K definitions on every request
- Fix: query only the definitions needed for each graph (typically <20 vs 40K)

### API Rate Limiting
Rate limits calculated from 95th percentile latency (`limit ≈ 60s / p95_latency`):

| Endpoint | p95 Latency | Rate Limit |
|----------|-------------|------------|
| `/graph/{word}` | 3100ms | 20/min |
| `/random` | 1200ms | 50/min |
| `/search` | 520ms | 120/min |

### Dependencies
- `slowapi` for rate limiting
- `locust` (dev) for load testing

---

## v0.5.1 - Developer Tooling (2024-12-20)

- **Ruff linting/formatting** with modern Python type hints (`Dict` → `dict`, `Optional[X]` → `X | None`)
- **prek pre-commit hooks** (Rust-based, faster than pre-commit)
- Development section in README

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
