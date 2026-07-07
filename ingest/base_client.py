import json
import time

import requests
from pathlib import Path



class CachedJSONClient:
    BASE_URL = ""
    MIN_INTERVAL = 1.0
    MAX_RETRIES = 5
    BACKOFF_CAP = 30.0
    _RETRY_STATUS = {429, 500, 502, 503, 504}

    def __init__(self, cache_dir: Path = Path("data/raw")) -> None:
        self.session = requests.Session()
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._last_request = 0.0


    def _get(self, path, params=None, cache_key=None, refresh=False) -> dict:
        cache_file = self.cache_dir / f"{cache_key}.json" if cache_key else None
        if cache_file and cache_file.exists() and not refresh:
            return json.loads(cache_file.read_text())
        raw = self._request(path, params)
        if cache_file:
            cache_file.write_text(json.dumps(raw, indent=2))
        return raw
    
    def _throttle(self) -> None:
        if self.MIN_INTERVAL <= 0:
            return
        
        elapsed = time.monotonic() - self._last_request

        if elapsed < self.MIN_INTERVAL:
            time.sleep(self.MIN_INTERVAL - elapsed)

    def _retry_wait(self, resp, attempt: int) -> float:
        retry_after = resp.headers.get("Retry-After")

        if retry_after:
            try:
                return float(retry_after)
            except ValueError:
                pass 
        return min((2 ** attempt), self.BACKOFF_CAP)

    def _request(self, path, params=None) -> dict:
        
        for attempt in range(self.MAX_RETRIES + 1):
            self._throttle()
            resp = self.session.get(f"{self.BASE_URL}{path}", params=params, timeout=30)
            self._last_request = time.monotonic()

            if resp.status_code in self._RETRY_STATUS and attempt < self.MAX_RETRIES:
                wait = self._retry_wait(resp, attempt)
                print(f"[base_client] {resp.status_code} on {path}; "
                      f"retry {attempt + 1}/{self.MAX_RETRIES} in {wait:.1f}s")
                time.sleep(wait)
                continue
           
            resp.raise_for_status()
            return resp.json()