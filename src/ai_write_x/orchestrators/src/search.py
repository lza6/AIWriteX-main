"""Search HN Algolia and Reddit for related stories."""

import asyncio
from typing import List, Dict

import httpx

from .models import ContentItem

HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"
REDDIT_SEARCH_URL = "https://www.reddit.com/search.json"

_reddit_semaphore = asyncio.Semaphore(5)


async def search_hn(query: str, client: httpx.AsyncClient) -> List[dict]:
    """Search HN Algolia. Returns list of {title, url, source, score, num_comments, date}."""
    params = {"query": query, "tags": "story", "hitsPerPage": 3}
    try:
        resp = await client.get(HN_SEARCH_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    results = []
    for hit in data.get("hits", []):
        results.append({
            "title": hit.get("title", ""),
            "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
            "source": "hackernews",
            "score": hit.get("points", 0),
            "num_comments": hit.get("num_comments", 0),
            "date": hit.get("created_at", ""),
        })
    return results


async def search_reddit(query: str, client: httpx.AsyncClient) -> List[dict]:
    """Search Reddit JSON API. Returns list of {title, url, source, score, num_comments, subreddit, date}."""
    params = {"q": query, "sort": "relevance", "limit": 3, "t": "year"}
    headers = {"User-Agent": "Horizon/1.0 (tech news aggregator)"}
    try:
        async with _reddit_semaphore:
            resp = await client.get(REDDIT_SEARCH_URL, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return []

    results = []
    for child in data.get("data", {}).get("children", []):
        post = child.get("data", {})
        results.append({
            "title": post.get("title", ""),
            "url": post.get("url", ""),
            "source": "reddit",
            "score": post.get("score", 0),
            "num_comments": post.get("num_comments", 0),
            "subreddit": post.get("subreddit", ""),
            "date": post.get("created_utc", ""),
        })
    return results


async def search_related(
    items: List[ContentItem], client: httpx.AsyncClient
) -> Dict[str, List[dict]]:
    """Search HN + Reddit for each item concurrently.

    Returns {item.id: [related_stories]}.
    Deduplicates by URL against each item's own URL.
    """

    async def _search_for_item(item: ContentItem) -> tuple:
        query = item.title
        hn_results, reddit_results = await asyncio.gather(
            search_hn(query, client),
            search_reddit(query, client),
            return_exceptions=True,
        )
        # Treat exceptions as empty results
        if isinstance(hn_results, Exception):
            hn_results = []
        if isinstance(reddit_results, Exception):
            reddit_results = []

        # Dedup: remove results whose URL matches the item's own URL
        item_url = str(item.url).rstrip("/")
        related = []
        for r in hn_results + reddit_results:
            if r["url"].rstrip("/") == item_url:
                continue
            related.append(r)
        return item.id, related

    tasks = [_search_for_item(item) for item in items]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    mapping: Dict[str, List[dict]] = {}
    for result in results:
        if isinstance(result, Exception):
            continue
        item_id, related = result
        mapping[item_id] = related
    return mapping
