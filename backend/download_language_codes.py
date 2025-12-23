"""Download language code mappings from ISO 639-3 and Wiktionary.

Sources:
- ISO 639-3: https://iso639-3.sil.org/code_tables/download_tables
- Wiktionary: etymology languages and families modules

Usage:
    python -m backend.download_language_codes
"""

from __future__ import annotations

import csv
import json
import re
from io import StringIO
from pathlib import Path
from urllib.request import Request, urlopen

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_FILE = DATA_DIR / "language_codes.json"


def fetch(url: str) -> str:
    """Fetch URL content."""
    req = Request(url, headers={"User-Agent": "etymology-for-all/1.0"})
    with urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def main() -> None:
    """Download and combine language codes into JSON."""
    codes: dict[str, str] = {}

    # 1. ISO 639-3 (official registry - ~8000 codes)
    print("Fetching ISO 639-3...")
    content = fetch("https://iso639-3.sil.org/sites/iso639-3/files/downloads/iso-639-3.tab")
    for row in csv.DictReader(StringIO(content), delimiter="\t"):
        codes[row["Id"]] = row["Ref_Name"]

    # 2. ISO 639-1 (two-letter codes)
    print("Fetching ISO 639-1...")
    content = fetch(
        "https://raw.githubusercontent.com/datasets/language-codes/master/data/language-codes.csv"
    )
    for row in csv.DictReader(StringIO(content)):
        codes[row["alpha2"]] = row["English"]

    # 3. Wiktionary etymology languages (dialects, variants)
    print("Fetching Wiktionary etymology codes...")
    content = fetch(
        "https://en.wiktionary.org/w/index.php?title=Module:etymology_languages/data&action=raw"
    )
    for m in re.finditer(r'm\["([^"]+)"\]\s*=\s*\{\s*\n\s*"([^"]+)"', content):
        codes[m.group(1)] = m.group(2)

    # 4. Wiktionary families -> proto-languages
    print("Fetching Wiktionary families...")
    content = fetch("https://en.wiktionary.org/w/index.php?title=Module:families/data&action=raw")
    for m in re.finditer(r'm\["([^"]+)"\]\s*=\s*\{\s*\n\s*"([^"]+)"', content):
        codes[m.group(1)] = m.group(2)
        codes[f"{m.group(1)}-pro"] = f"Proto-{m.group(2)}"

    # Write output
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data = [
        {"code": c, "name": n, "family": None, "branch": None} for c, n in sorted(codes.items())
    ]
    OUTPUT_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"Wrote {len(data)} codes to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
