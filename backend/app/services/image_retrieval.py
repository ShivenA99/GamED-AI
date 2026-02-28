"""
Image retrieval service with basic licensing inference.

Supports multi-strategy search that prioritizes unlabeled diagrams to avoid
the need for text removal when possible.

Includes retry logic with exponential backoff for resilient API calls.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.services.web_search import get_serper_client

logger = logging.getLogger("gamed_ai.services.image_retrieval")


# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1.0
MAX_BACKOFF_SECONDS = 10.0
BACKOFF_MULTIPLIER = 2.0

# Image quality thresholds
MIN_IMAGE_WIDTH = 400
MIN_IMAGE_HEIGHT = 300


async def _retry_with_backoff(
    func,
    *args,
    max_retries: int = MAX_RETRIES,
    initial_backoff: float = INITIAL_BACKOFF_SECONDS,
    **kwargs
):
    """
    Execute an async function with exponential backoff retry.

    Args:
        func: Async function to execute
        *args: Positional arguments for func
        max_retries: Maximum number of retry attempts
        initial_backoff: Initial backoff duration in seconds
        **kwargs: Keyword arguments for func

    Returns:
        Result of the function call

    Raises:
        Last exception if all retries fail
    """
    last_exception = None
    backoff = initial_backoff

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                # Check for rate limit indicators
                error_msg = str(e).lower()
                is_rate_limit = any(
                    indicator in error_msg
                    for indicator in ["rate limit", "429", "too many requests", "quota"]
                )

                if is_rate_limit:
                    wait_time = min(backoff * (BACKOFF_MULTIPLIER ** attempt), MAX_BACKOFF_SECONDS)
                else:
                    wait_time = backoff

                logger.warning(
                    f"Image retrieval attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                    f"Retrying in {wait_time:.1f}s..."
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(
                    f"Image retrieval failed after {max_retries + 1} attempts: {e}"
                )

    raise last_exception


def _infer_license(snippet: str, source: str) -> str:
    text = f"{snippet} {source}".lower()
    if "creative commons" in text or "cc-" in text or "cc by" in text:
        return "creative-commons"
    if "public domain" in text:
        return "public-domain"
    if "license" in text or "licensed" in text:
        return "licensed"
    return "unknown"


def _normalize_attribution(title: str, link: str) -> str:
    title = title.strip() or "Source"
    return f"{title} ({link})"


def _validate_image_quality(result: Dict[str, Any]) -> bool:
    """
    Validate that an image meets minimum quality requirements.

    Args:
        result: Image search result dict

    Returns:
        True if image meets quality requirements
    """
    # Check for minimum resolution if dimensions are available
    width = result.get("imageWidth", 0) or result.get("width", 0)
    height = result.get("imageHeight", 0) or result.get("height", 0)

    # If dimensions are provided and below threshold, reject
    if width > 0 and height > 0:
        if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT:
            logger.debug(f"Rejecting low-res image: {width}x{height}")
            return False

    # Check for valid image URL
    image_url = result.get("imageUrl") or result.get("image", "")
    if not image_url or not image_url.startswith(("http://", "https://")):
        return False

    # Check for problematic file types (exclude tiny icons, etc.)
    url_lower = image_url.lower()
    if any(ext in url_lower for ext in [".ico", ".gif", ".webp"]):
        # GIF and WebP might be acceptable for some use cases, but prefer PNG/JPG
        pass

    return True


async def _search_with_retry(client, query: str) -> List[Dict[str, Any]]:
    """
    Search for images with retry logic.

    Args:
        client: Serper client instance
        query: Search query

    Returns:
        List of image results
    """
    return await _retry_with_backoff(client.search_images, query)


async def search_diagram_images(
    query: str,
    max_results: int = 5,
    validate_quality: bool = True
) -> List[Dict[str, Any]]:
    """
    Search for diagram images with retry and quality validation.

    Args:
        query: Search query string
        max_results: Maximum number of results to return
        validate_quality: Whether to filter out low-quality images

    Returns:
        List of image search results
    """
    client = get_serper_client()

    try:
        results = await _search_with_retry(client, query)
    except Exception as e:
        logger.error(f"Image search failed for query '{query}': {e}")
        return []

    # Filter by quality if enabled
    if validate_quality:
        results = [r for r in results if _validate_image_quality(r)]

    return results[:max_results]


def select_best_image(results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Legacy function - use select_best_image_scored for new code."""
    for result in results:
        # Serper API returns 'imageUrl', not 'image'
        image_url = result.get("imageUrl") or result.get("image")
        source_url = result.get("link")
        title = result.get("source") or result.get("title") or ""
        snippet = result.get("snippet") or ""
        if not image_url or not source_url:
            continue
        license_type = _infer_license(snippet, source_url)
        return {
            "image_url": image_url,
            "source_url": source_url,
            "title": title,
            "snippet": snippet,
            "license": license_type,
            "attribution": _normalize_attribution(title or "Source", source_url),
        }
    return None


def select_top_images_scored(
    results: List[Dict[str, Any]],
    prefer_unlabeled: bool = False,
    top_n: int = 3
) -> List[Dict[str, Any]]:
    """
    Score and select top N images for educational diagrams.
    Returns multiple images for fallback purposes if primary download fails.

    Args:
        results: List of image search results
        prefer_unlabeled: If True, add bonus for unlabeled diagrams
        top_n: Number of top images to return

    Returns:
        List of top scoring images, sorted by score
    """
    all_scored = _score_images(results, prefer_unlabeled)
    return all_scored[:top_n]


def _score_images(
    results: List[Dict[str, Any]],
    prefer_unlabeled: bool = False
) -> List[Dict[str, Any]]:
    """
    Internal function to score all images.

    Returns:
        List of formatted images with scores, sorted by score descending
    """
    scored: List[Tuple[float, Dict[str, Any]]] = []

    for result in results:
        image_url = result.get("imageUrl") or result.get("image")
        source_url = result.get("link")

        if not image_url or not source_url:
            continue

        # Skip SVG files — they can't be processed by Gemini image gen or zone detection
        if image_url.lower().endswith(".svg") or ".svg?" in image_url.lower():
            logger.debug(f"Skipping SVG image: {image_url[:80]}")
            continue

        score = 0.0
        title = (result.get("title") or result.get("source") or "").lower()
        snippet = (result.get("snippet") or "").lower()
        url = source_url.lower()
        combined_text = f"{title} {snippet}"

        # Educational source bonus
        edu_sources = [".edu", "khan", "biology", "science", "anatomy", "wikipedia"]
        if any(edu in url for edu in edu_sources):
            score += 2.0

        # Quality indicators
        if "diagram" in combined_text:
            score += 1.0
        if "educational" in combined_text or "scientific" in combined_text:
            score += 1.0
        if "illustration" in combined_text:
            score += 0.5

        # Colorful/detailed/high-quality diagrams
        colorful_terms = ["colorful", "detailed", "high quality", "color", "coloured", "colored"]
        if any(term in combined_text for term in colorful_terms):
            score += 1.5

        # PREFER well-labeled diagrams - they provide better reference for image generation
        # The generator will create a clean version from the labeled reference
        labeled_terms = ["labeled", "labelled", "with labels", "annotated", "parts labeled"]
        if any(term in combined_text for term in labeled_terms):
            score += 2.5  # Bonus for labeled diagrams
            logger.debug(f"Labeled diagram bonus for: {title[:50]}")

        # Unlabeled preference scoring (optional, usually off)
        if prefer_unlabeled:
            unlabeled_terms = ["blank", "unlabeled", "worksheet", "quiz", "empty", "without labels"]
            if any(term in combined_text for term in unlabeled_terms):
                score += 3.0

        # Negative indicators
        if "clipart" in combined_text or "cartoon" in combined_text:
            score -= 1.0
        if "stock" in combined_text:
            score -= 2.0

        # STRONG penalty for stock image domains (watermarked images) and blocked domains (403)
        stock_domains = [
            "ftcdn.net", "shutterstock", "istockphoto", "gettyimages",
            "123rf.com", "dreamstime", "depositphotos", "adobe.com/stock",
            "canstockphoto", "bigstockphoto", "vectorstock", "alamy.com",
            # Blocked domains that return 403 Forbidden or require auth
            "quizlet.com", "o.quizlet.com", "brainly.com", "chegg.com",
            "researchgate.net", "academia.edu", "sciencedirect.com",
            "springer.com", "wiley.com", "elsevier.com", "jstor.org",
            "facebook.com", "fbcdn.net", "lookaside.fbsbx.com",
            "pinterest.com", "pinimg.com",
            "slideshare.net", "scribd.com",
        ]

        # BONUS for reliable educational sources that typically allow downloads
        reliable_sources = [
            "wikimedia.org", "wikipedia.org", "upload.wikimedia.org",
            "khanacademy.org", "nationalgeographic.com", "nasa.gov",
            "nih.gov", "cdc.gov", "britannica.com", "bbc.co.uk",
            "thoughtco.com", "biologydictionary.net", "visible-body.com",
        ]
        if any(source in url or source in image_url.lower() for source in reliable_sources):
            score += 3.0

        if any(domain in url or domain in image_url.lower() for domain in stock_domains):
            score -= 10.0

        # Penalty for watermark indicators
        watermark_terms = ["watermark", "preview", "comp", "sample"]
        if any(term in combined_text or term in image_url.lower() for term in watermark_terms):
            score -= 5.0

        # Format the result
        license_type = _infer_license(snippet, source_url)
        formatted_result = {
            "image_url": image_url,
            "source_url": source_url,
            "title": result.get("source") or result.get("title") or "",
            "snippet": snippet,
            "license": license_type,
            "attribution": _normalize_attribution(
                result.get("source") or result.get("title") or "Source",
                source_url
            ),
            "selection_score": score,
        }

        scored.append((score, formatted_result))

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    return [item[1] for item in scored]


def select_best_image_scored(
    results: List[Dict[str, Any]],
    prefer_unlabeled: bool = False  # Changed: now accepts labeled diagrams
) -> Optional[Dict[str, Any]]:
    """
    Score and select best image for educational diagrams.

    Scoring priorities:
    1. Reliable sources (wikimedia, nih.gov, etc.) +3.0
    2. Educational sources (.edu, wikipedia, etc.) +2.0
    3. Colorful/detailed/high-quality diagrams +1.5
    4. Scientific illustrations +1.0
    5. Avoid stock images (watermarks) -10.0
    6. Avoid clipart/cartoon -1.0

    Args:
        results: List of image search results
        prefer_unlabeled: If True, add bonus for unlabeled diagrams (default False)

    Returns:
        Best scoring image result formatted for use, or None
    """
    scored_images = _score_images(results, prefer_unlabeled)

    if scored_images:
        best = scored_images[0]
        logger.info(f"Selected image with score {best.get('selection_score', 0):.1f}: {best.get('title', '')[:60]}")
        return best

    return None


def build_image_query(question_text: str, canonical_labels: List[str]) -> str:
    """Legacy function - builds a single query for labeled diagrams."""
    # Ensure canonical_labels is a proper list before slicing
    label_list = list(canonical_labels) if canonical_labels else []
    labels = ", ".join(label_list[:4]) if label_list else ""
    base = question_text.strip().rstrip(".")
    suffix = f" diagram labeled {labels}" if labels else " diagram labeled"
    return f"{base}{suffix}"


def build_image_queries(question_text: str, canonical_labels: List[str]) -> List[str]:
    """
    Generate multiple search queries prioritizing colorful educational diagrams.

    Returns queries in priority order:
    1. Colorful labeled educational diagrams (best for VLM processing)
    2. Scientific illustrations with labels
    3. Generic educational diagrams

    Args:
        question_text: The original question text
        canonical_labels: List of expected labels for the diagram

    Returns:
        List of search queries in priority order
    """
    base = question_text.strip().rstrip(".")
    label_list = list(canonical_labels) if canonical_labels else []
    labels_str = ", ".join(label_list[:3]) if label_list else ""

    # Extract subject from question (e.g., "flower" from "What are the parts of a flower?")
    subject = _extract_subject(base)

    queries = [
        # Priority 1: Well-labeled educational diagrams (best for reference)
        f"{subject} labeled diagram educational high quality",
        f"{subject} anatomy diagram labeled parts illustration",
        f"{subject} parts labeled scientific diagram detailed",

        # Priority 2: Labeled diagrams from reliable sources
        f"{subject} labeled diagram wikipedia",
        f"{subject} labeled anatomy illustration educational",

        # Priority 3: Fallback - any labeled educational diagram
        f"{subject} diagram labeled parts",
    ]

    # Filter out empty or duplicate queries
    seen = set()
    unique_queries = []
    for q in queries:
        q_clean = " ".join(q.split())  # Normalize whitespace
        if q_clean and q_clean not in seen:
            seen.add(q_clean)
            unique_queries.append(q_clean)

    logger.info(f"Generated {len(unique_queries)} search queries for: {base[:50]}")
    return unique_queries


def _extract_subject(question_text: str) -> str:
    """
    Extract the main subject from a question for simpler queries.

    Examples:
        "What are the parts of a flower?" -> "flower"
        "Label the parts of the human heart" -> "human heart"
    """
    text = question_text.lower()

    # Common patterns
    patterns = [
        r"parts of (?:a |the )?(.+?)(?:\?|$)",
        r"label (?:a |the )?(.+?)(?:\?|$)",
        r"diagram of (?:a |the )?(.+?)(?:\?|$)",
        r"structure of (?:a |the )?(.+?)(?:\?|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            subject = match.group(1).strip()
            # Clean up common trailing words
            subject = re.sub(r"\s+(diagram|image|picture|parts)$", "", subject)
            return subject

    # Fallback: return cleaned question text
    return text.replace("what are the", "").replace("?", "").strip()


async def search_diagram_images_multi(
    queries: List[str],
    max_results: int = 5,
    max_queries: int = 4,
    validate_quality: bool = True
) -> List[Dict[str, Any]]:
    """
    Search with multiple queries, combine and dedupe results.

    Includes retry logic with exponential backoff for each query,
    and alternative query fallback if initial queries fail.

    Args:
        queries: List of search queries in priority order
        max_results: Maximum total results to return
        max_queries: Maximum number of queries to execute
        validate_quality: Whether to filter out low-quality images

    Returns:
        Combined, deduplicated list of image results
    """
    client = get_serper_client()
    all_results: List[Dict[str, Any]] = []
    seen_urls: set = set()
    failed_queries = 0

    for i, query in enumerate(queries[:max_queries]):
        try:
            logger.debug(f"Executing query {i+1}: {query[:60]}")

            # Use retry with backoff for each query
            results = await _search_with_retry(client, query)

            for result in results:
                url = result.get("imageUrl") or result.get("image")
                if url and url not in seen_urls:
                    # Quality validation
                    if validate_quality and not _validate_image_quality(result):
                        continue

                    seen_urls.add(url)
                    result["_query_index"] = i  # Track which query found this
                    all_results.append(result)

            # Stop if we have enough results
            if len(all_results) >= max_results * 2:
                break

        except Exception as e:
            logger.warning(f"Query {i+1} failed after retries: {e}")
            failed_queries += 1
            continue

    # If we got very few results and most queries failed, try fallback queries
    if len(all_results) < 3 and failed_queries >= max_queries // 2:
        logger.info("Attempting fallback queries due to insufficient results")
        fallback_queries = _generate_fallback_queries(queries[0] if queries else "")

        for query in fallback_queries[:2]:  # Try up to 2 fallback queries
            try:
                results = await _search_with_retry(client, query)
                for result in results:
                    url = result.get("imageUrl") or result.get("image")
                    if url and url not in seen_urls:
                        if validate_quality and not _validate_image_quality(result):
                            continue
                        seen_urls.add(url)
                        result["_query_index"] = max_queries  # Mark as fallback
                        all_results.append(result)

                if len(all_results) >= max_results:
                    break
            except Exception as e:
                logger.warning(f"Fallback query failed: {e}")
                continue

    logger.info(
        f"Multi-query search found {len(all_results)} unique images "
        f"from {min(len(queries), max_queries)} queries "
        f"({failed_queries} failures)"
    )
    return all_results


def _generate_fallback_queries(original_query: str) -> List[str]:
    """
    Generate fallback queries when primary queries fail.

    Uses simpler, more generic search terms.

    Args:
        original_query: The original search query

    Returns:
        List of fallback query strings
    """
    # Extract key subject from original query
    subject = _extract_subject(original_query) if original_query else "diagram"

    # Simple, generic fallback queries
    return [
        f"{subject} diagram educational",
        f"{subject} labeled anatomy",
        f"parts of {subject} diagram",
    ]
