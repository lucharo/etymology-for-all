from pathlib import Path
import requests

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / 'data'
DATA_DIR.mkdir(exist_ok=True)

FILES = {
    'etymdb_values.csv': 'https://raw.githubusercontent.com/clefourrier/EtymDB-2.0/master/etymdb_values.csv',
    'etymdb_links_info.csv': 'https://raw.githubusercontent.com/clefourrier/EtymDB-2.0/master/etymdb_links_info.csv'
}

def download():
    for name, url in FILES.items():
        dest = DATA_DIR / name
        if dest.exists():
            print(f'{dest} already exists, skipping')
            continue
        print(f'Downloading {url} -> {dest}')
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        dest.write_bytes(resp.content)

if __name__ == '__main__':
    download()
