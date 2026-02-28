"""Image search via Serper API with scoring, download, and caching."""

import asyncio
import hashlib
import logging
import os
from io import BytesIO
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger("gamed_ai.asset_gen.search")

SERPER_IMAGE_URL = "https://google.serper.dev/images"

# Domains to avoid (stock photos, paywalled, watermarked)
BLOCKED_DOMAINS = {
    "ftcdn.net", "shutterstock", "istockphoto", "gettyimages",
    "123rf.com", "dreamstime", "depositphotos", "adobe.com/stock",
    "canstockphoto", "bigstockphoto", "vectorstock", "alamy.com",
    "quizlet.com", "brainly.com", "chegg.com", "pinterest.com",
    "pinimg.com", "facebook.com", "fbcdn.net",
}

# Preferred educational sources
TRUSTED_DOMAINS = {
    "wikimedia.org", "wikipedia.org", "upload.wikimedia.org",
    "khanacademy.org", "nih.gov", "cdc.gov", "nasa.gov",
    "britannica.com", "nationalgeographic.com", "bbc.co.uk",
    "biologydictionary.net", "thoughtco.com",
}


class ImageSearcher:
    """Search for educational reference images using Serper API."""

    def __init__(self, api_key: str | None = None, cache_dir: Path | None = None):
        key = api_key or os.getenv("SERPER_API_KEY")
        if not key:
            raise ValueError("SERPER_API_KEY not set")
        self.api_key = key
        self.cache_dir = cache_dir or Path(__file__).parent.parent.parent.parent / "assets" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def search(
        self,
        query: str,
        num_results: int = 10,
    ) -> list[dict]:
        """Search Serper for images, return scored results.

        Args:
            query: Search query
            num_results: Number of results to fetch

        Returns:
            List of scored result dicts sorted by score descending:
            [{image_url, source_url, title, snippet, score, width, height}]
        """
        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }
        params = {
            "q": query,
            "num": num_results,
            "gl": "us",
            "hl": "en",
            "autocorrect": "true",
        }

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                SERPER_IMAGE_URL, params=params, headers=headers,
            )
            if response.status_code != 200:
                raise RuntimeError(f"Serper search failed: {response.status_code} {response.text}")
            data = response.json()

        raw_results = data.get("images", [])[:num_results]
        scored = []

        for r in raw_results:
            image_url = r.get("imageUrl") or r.get("image", "")
            source_url = r.get("link", "")
            if not image_url or not source_url:
                continue

            score = self._score_result(r)
            if score <= -5:
                continue  # Skip obviously bad results

            scored.append({
                "image_url": image_url,
                "source_url": source_url,
                "title": r.get("title") or r.get("source", ""),
                "snippet": r.get("snippet", ""),
                "score": score,
                "width": r.get("imageWidth", 0),
                "height": r.get("imageHeight", 0),
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        logger.info(f"Search '{query[:50]}' returned {len(scored)} scored results")
        return scored

    def _score_result(self, result: dict) -> float:
        """Score an image search result for educational diagram quality."""
        score = 0.0
        image_url = (result.get("imageUrl") or result.get("image", "")).lower()
        source_url = (result.get("link", "")).lower()
        title = (result.get("title") or result.get("source", "")).lower()
        snippet = (result.get("snippet", "")).lower()
        text = f"{title} {snippet}"

        # Blocked domains
        if any(d in source_url or d in image_url for d in BLOCKED_DOMAINS):
            return -10.0

        # Trusted sources
        if any(d in source_url or d in image_url for d in TRUSTED_DOMAINS):
            score += 3.0

        # Educational indicators
        if ".edu" in source_url:
            score += 2.0
        if "diagram" in text:
            score += 1.0
        if any(t in text for t in ["educational", "scientific", "anatomy"]):
            score += 1.0
        if any(t in text for t in ["labeled", "labelled", "annotated"]):
            score += 2.5  # Labeled refs are best for Gemini re-generation

        # Quality indicators
        if any(t in text for t in ["colorful", "detailed", "high quality", "illustration"]):
            score += 1.5

        # Resolution bonus
        w = result.get("imageWidth", 0) or 0
        h = result.get("imageHeight", 0) or 0
        if w >= 800 and h >= 600:
            score += 1.0
        elif w < 400 or h < 300:
            score -= 1.0

        # Negative indicators
        if any(t in text for t in ["clipart", "cartoon", "stock"]):
            score -= 2.0
        if any(t in image_url for t in ["watermark", "preview", "comp", "sample"]):
            score -= 5.0

        return score

    async def download(self, url: str, timeout: float = 30) -> bytes:
        """Download an image from URL, return raw bytes."""
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content

    async def search_and_download_best(
        self,
        query: str,
        num_results: int = 10,
        fallback_queries: list[str] | None = None,
    ) -> tuple[bytes, dict] | None:
        """Search, score, download the best result. Try fallback queries on failure.

        Returns:
            Tuple of (image_bytes, result_metadata) or None if all fail
        """
        queries = [query] + (fallback_queries or [])

        for q in queries:
            try:
                results = await self.search(q, num_results=num_results)
            except Exception as e:
                logger.warning(f"Search failed for '{q[:50]}': {e}")
                continue

            for result in results[:3]:  # Try top 3
                try:
                    data = await self.download(result["image_url"])
                    if len(data) < 1000:
                        continue  # Too small, likely error page
                    logger.info(f"Downloaded image ({len(data)} bytes) from {result['source_url'][:60]}")
                    return data, result
                except Exception as e:
                    logger.warning(f"Download failed for {result['image_url'][:60]}: {e}")
                    continue

        logger.error(f"All search queries failed for: {query[:50]}")
        return None

    async def search_multiple_items(
        self,
        items: list[str],
        query_template: str = "{item} educational illustration",
        num_results: int = 5,
    ) -> dict[str, tuple[bytes, dict] | None]:
        """Search and download images for multiple items concurrently.

        Args:
            items: List of item names
            query_template: Template with {item} placeholder
            num_results: Results per search

        Returns:
            Dict mapping item name to (image_bytes, metadata) or None
        """
        async def _fetch_one(item: str):
            query = query_template.format(item=item)
            return item, await self.search_and_download_best(query, num_results=num_results)

        # Run concurrently with a semaphore to respect rate limits
        sem = asyncio.Semaphore(3)

        async def _limited(item):
            async with sem:
                await asyncio.sleep(0.5)  # Rate limit spacing
                return await _fetch_one(item)

        tasks = [_limited(item) for item in items]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output = {}
        for r in results:
            if isinstance(r, Exception):
                logger.warning(f"Item search failed: {r}")
                continue
            item_name, item_result = r
            output[item_name] = item_result

        logger.info(f"Downloaded {sum(1 for v in output.values() if v)} of {len(items)} item images")
        return output

    def get_cache_path(self, url: str) -> Path:
        """Get a deterministic cache file path for a URL."""
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        return self.cache_dir / f"{url_hash}.png"

    async def download_cached(self, url: str) -> bytes:
        """Download with filesystem caching."""
        cache_path = self.get_cache_path(url)
        if cache_path.exists():
            logger.debug(f"Cache hit: {cache_path.name}")
            return cache_path.read_bytes()

        data = await self.download(url)
        cache_path.write_bytes(data)
        return data
