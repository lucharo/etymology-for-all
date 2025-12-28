---
title: Etymology Graph Explorer
emoji: 🌳
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
---

# Etymology Graph Explorer

A visual tool for exploring the origins and historical relationships between words. Search for any word and see its etymological journey through time, from modern usage back to ancient roots.

## Quick Start

### Using uv (recommended for development)

```bash
# Install dependencies
uv sync

# Run the server
uv run uvicorn backend.main:app --reload

# Open http://localhost:8000 in your browser
```

### Using Docker

```bash
# Build the image
docker build -t etymology .

# Run the container
docker run -p 7860:7860 etymology

# Open http://localhost:7860 in your browser
```

## Features

- **Search any word** to see its etymological tree
- **Random word** button for exploration and discovery
- **Interactive graph** - zoom, pan, and click on nodes
- **Color-coded languages** to visualize word evolution across language families
- **Mobile-friendly** responsive design

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Web interface |
| `GET /graph/{word}` | Etymology graph for a word (JSON) |
| `GET /random` | Random English word |
| `GET /health` | Health check |

## Data Source

Etymology data comes from [EtymDB 2.1](https://github.com/clefourrier/EtymDB), an open etymological database derived from Wiktionary.

> Fourrier & Sagot (2020), "Methodological Aspects of Developing and Managing an Etymological Lexical Resource: Introducing EtymDB-2.0", Proceedings of the LREC Conference.

## Tech Stack

- **Backend**: FastAPI + DuckDB
- **Frontend**: Vanilla JS + Cytoscape.js
- **Data**: EtymDB 2.1 (auto-downloaded on first run)

## Development

```bash
uv sync                        # Install dependencies
uv run prek install            # Set up pre-commit hooks
uv run pytest backend/tests -q # Run tests
```

Linting (ruff) runs automatically on commit via prek.

## Deploy

```bash
make hf-deploy  # Deploy to HF Spaces (stages, pushes, squashes history)
make cf-deploy  # Deploy Cloudflare Worker (custom domain proxy)
```

## License

GPL-3.0 - see [LICENSE](LICENSE)
