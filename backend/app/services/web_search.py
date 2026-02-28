"""
Web search service for domain knowledge retrieval.
Uses Serper API with in-memory TTL cache.
"""

from __future__ import annotations

import os
import time
import threading
from typing import Any, Dict, List, Optional

import httpx


SERPER_API_URL = "https://google.serper.dev/search"
SERPER_IMAGE_URL = "https://google.serper.dev/images"


class WebSearchError(RuntimeError):
    pass


class _TTLCache:
    def __init__(self, ttl_seconds: int):
        self.ttl_seconds = ttl_seconds
        self._store: Dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        now = time.time()
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            expires_at, value = entry
            if expires_at < now:
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        expires_at = time.time() + self.ttl_seconds
        with self._lock:
            self._store[key] = (expires_at, value)


class SerperSearchClient:
    def __init__(self, api_key: str, ttl_seconds: int = 3600, max_results: int = 5):
        self.api_key = api_key
        self.max_results = max_results
        self._cache = _TTLCache(ttl_seconds=ttl_seconds)

    async def search(self, query: str) -> List[Dict[str, Any]]:
        cache_key = query.strip().lower()
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "q": query,
            "num": self.max_results,
        }

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(SERPER_API_URL, json=payload, headers=headers)
            if response.status_code != 200:
                raise WebSearchError(
                    f"Serper search failed: {response.status_code} {response.text}"
                )
            data = response.json()

        results = data.get("organic", [])[: self.max_results]
        self._cache.set(cache_key, results)
        return results

    async def search_images(self, query: str) -> List[Dict[str, Any]]:
        cache_key = f"images:{query.strip().lower()}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }
        params = {
            "q": query,
            "num": self.max_results,
            "gl": "us",
            "hl": "en",
            "autocorrect": "true",
        }

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(SERPER_IMAGE_URL, params=params, headers=headers)
            if response.status_code != 200:
                raise WebSearchError(
                    f"Serper image search failed: {response.status_code} {response.text}"
                )
            data = response.json()

        results = data.get("images", [])[: self.max_results]
        self._cache.set(cache_key, results)
        return results


def get_serper_client() -> SerperSearchClient:
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        raise WebSearchError("SERPER_API_KEY not set")
    ttl_seconds = int(os.getenv("SERPER_CACHE_TTL_SECONDS", "3600"))
    max_results = int(os.getenv("SERPER_MAX_RESULTS", "5"))
    return SerperSearchClient(api_key=api_key, ttl_seconds=ttl_seconds, max_results=max_results)
