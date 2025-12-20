"""Utilities to download the EtymDB CSV files on demand."""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

import httpx

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = BASE_DIR / "data"

DATA_DIR = Path(os.environ.get("ETYM_DATA_DIR", DEFAULT_DATA_DIR))
DATA_DIR.mkdir(parents=True, exist_ok=True)

FILES: dict[str, str] = {
    "etymdb_values.csv": "https://raw.githubusercontent.com/clefourrier/EtymDB/master/data/split_etymdb/etymdb_values.csv",
    "etymdb_links_info.csv": "https://raw.githubusercontent.com/clefourrier/EtymDB/master/data/split_etymdb/etymdb_links_info.csv",
}

_CHUNK_SIZE = 1 << 20  # 1 MiB


def _iter_download(client: httpx.Client, url: str) -> Iterable[bytes]:
    """Stream a download from *url* yielding binary chunks."""
    with client.stream("GET", url) as response:
        response.raise_for_status()
        for chunk in response.iter_bytes(_CHUNK_SIZE):
            if chunk:
                yield chunk


def download() -> None:
    """Download the EtymDB CSVs into :data:`DATA_DIR` if missing."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with httpx.Client(follow_redirects=True, timeout=httpx.Timeout(60.0)) as client:
        for name, url in FILES.items():
            destination = DATA_DIR / name
            if destination.exists():
                continue
            destination_tmp = destination.with_suffix(destination.suffix + ".tmp")
            destination_tmp.parent.mkdir(parents=True, exist_ok=True)
            with destination_tmp.open("wb") as fh:
                for chunk in _iter_download(client, url):
                    fh.write(chunk)
            destination_tmp.replace(destination)


if __name__ == "__main__":  # pragma: no cover - manual utility
    download()
