import json

import requests
from pathlib import Path



class CachedJSONClient:
    BASE_URL = ""

    def __init__(self, cache_dir: Path = Path("data/raw")) -> None:
        self.session = requests.Session()
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get(self, path, params=None, cache_key=None, refresh=False) -> dict:
        cache_file = self.cache_dir / f"{cache_key}.json" if cache_key else None
        if cache_file and cache_file.exists() and not refresh:
            return json.loads(cache_file.read_text())
        raw = self._request(path, params)
        if cache_file:
            cache_file.write_text(json.dumps(raw, indent=2))
        return raw

    def _request(self, path, params=None) -> dict:
        resp = self.session.get(f"{self.BASE_URL}{path}", params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()