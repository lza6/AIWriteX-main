"""Reddit scraper implementation."""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import List, Optional

import httpx

from .base import BaseScraper
from ..models import ContentItem, RedditConfig, RedditSubredditConfig, RedditUserConfig, SourceType

logger = logging.getLogger(__name__)

REDDIT_BASE = "https://www.reddit.com"
USER_AGENT = "Horizon/1.0 (content aggregator; +https://github.com/thysrael/horizon)"


class RedditScraper(BaseScraper):
    """Scraper for Reddit posts and comments."""

    def __init__(self, config: RedditConfig, http_client: httpx.AsyncClient):
        super().__init__(config.model_dump(), http_client)
        self.reddit_config = config

    async def fetch(self, since: datetime) -> List[ContentItem]:
        if not self.config.get("enabled", True):
            return []

        tasks = []
        for sub_cfg in self.reddit_config.subreddits:
            if sub_cfg.enabled:
                tasks.append(self._fetch_subreddit(sub_cfg, since))
        for user_cfg in self.reddit_config.users:
            if user_cfg.enabled:
                tasks.append(self._fetch_user(user_cfg, since))

        if not tasks:
            return []

        results = await asyncio.gather(*tasks, return_exceptions=True)
        items = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning("Error fetching Reddit source: %s", result)
            elif isinstance(result, list):
                items.extend(result)
        return items

    async def _fetch_subreddit(self, cfg: RedditSubredditConfig, since: datetime) -> List[ContentItem]:
        params = {"limit": min(cfg.fetch_limit, 100), "raw_json": 1}
        if cfg.sort in ("top", "controversial"):
            params["t"] = cfg.time_filter

        url = f"{REDDIT_BASE}/r/{cfg.subreddit}/{cfg.sort}.json"
        data = await self._reddit_get(url, params)
        if not data:
            return []

        posts = [child["data"] for child in data.get("data", {}).get("children", [])
                 if child.get("kind") == "t3"]
        return await self._process_posts(
            posts, since, "subreddit", cfg.subreddit, cfg.min_score
        )

    async def _fetch_user(self, cfg: RedditUserConfig, since: datetime) -> List[ContentItem]:
        params = {"limit": min(cfg.fetch_limit, 100), "sort": cfg.sort, "raw_json": 1}
        url = f"{REDDIT_BASE}/user/{cfg.username}/submitted.json"
        data = await self._reddit_get(url, params)
        if not data:
            return []

        posts = [child["data"] for child in data.get("data", {}).get("children", [])
                 if child.get("kind") == "t3"]
        return await self._process_posts(
            posts, since, "user", cfg.username, min_score=0
        )

    async def _process_posts(
        self,
        posts: list,
        since: datetime,
        subtype: str,
        source_name: str,
        min_score: int,
    ) -> List[ContentItem]:
        valid_posts = []
        comment_tasks = []
        fetch_comments = self.reddit_config.fetch_comments

        for post in posts:
            created = datetime.fromtimestamp(post.get("created_utc", 0), tz=timezone.utc)
            if created < since:
                continue
            if post.get("score", 0) < min_score:
                continue
            valid_posts.append(post)
            if fetch_comments > 0:
                comment_tasks.append(
                    self._fetch_comments(post.get("subreddit", ""), post["id"])
                )
            else:
                comment_tasks.append(self._empty_comments())

        if not valid_posts:
            return []

        all_comments = await asyncio.gather(*comment_tasks, return_exceptions=True)

        items = []
        for post, comments in zip(valid_posts, all_comments):
            if isinstance(comments, Exception):
                comments = []
            item = self._parse_post(post, comments, subtype)
            if item:
                items.append(item)
        return items

    @staticmethod
    async def _empty_comments() -> List[dict]:
        return []

    async def _fetch_comments(self, subreddit: str, post_id: str) -> List[dict]:
        fetch_limit = self.reddit_config.fetch_comments
        url = f"{REDDIT_BASE}/r/{subreddit}/comments/{post_id}.json"
        params = {"limit": fetch_limit, "depth": 1, "sort": "top", "raw_json": 1}

        data = await self._reddit_get(url, params)
        if not data or not isinstance(data, list) or len(data) < 2:
            return []

        comments = []
        for child in data[1].get("data", {}).get("children", []):
            if child.get("kind") != "t1":
                continue
            c = child["data"]
            if c.get("body") and not c.get("distinguished") == "moderator":
                comments.append(c)

        comments.sort(key=lambda c: c.get("score", 0), reverse=True)
        return comments[:fetch_limit]

    def _parse_post(self, post: dict, comments: List[dict], subtype: str) -> Optional[ContentItem]:
        post_id = post["id"]
        title = post.get("title", "")
        is_self = post.get("is_self", False)
        subreddit = post.get("subreddit", "")
        discussion_url = f"https://www.reddit.com{post.get('permalink', '')}"

        # For link posts, use the external URL; for self posts, use the discussion URL
        url = discussion_url if is_self else post.get("url", discussion_url)

        author = post.get("author", "unknown")
        created = datetime.fromtimestamp(post.get("created_utc", 0), tz=timezone.utc)

        # Build content
        parts = []
        if post.get("selftext"):
            text = post["selftext"]
            if len(text) > 1500:
                text = text[:1497] + "..."
            parts.append(text)

        if comments:
            parts.append("\n--- Top Comments ---")
            for c in comments:
                commenter = c.get("author", "anon")
                body = c.get("body", "")
                body = body.strip()
                if len(body) > 500:
                    body = body[:497] + "..."
                score = c.get("score", 0)
                parts.append(f"[{commenter} ({score} pts)]: {body}")

        content = "\n\n".join(parts)

        return ContentItem(
            id=self._generate_id("reddit", subtype, post_id),
            source_type=SourceType.REDDIT,
            title=title,
            url=url,
            content=content,
            author=author,
            published_at=created,
            metadata={
                "score": post.get("score", 0),
                "upvote_ratio": post.get("upvote_ratio"),
                "num_comments": post.get("num_comments", 0),
                "subreddit": subreddit,
                "is_self": is_self,
                "flair": post.get("link_flair_text"),
                "discussion_url": discussion_url,
            },
        )

    async def _reddit_get(self, url: str, params: dict) -> Optional[dict]:
        headers = {"User-Agent": USER_AGENT}
        try:
            response = await self.client.get(url, params=params, headers=headers, follow_redirects=True)
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 5))
                logger.warning("Reddit rate limited, retrying after %ds", retry_after)
                await asyncio.sleep(retry_after)
                response = await self.client.get(url, params=params, headers=headers, follow_redirects=True)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.warning("Reddit request failed for %s: %s", url, e)
            return None
