"""GitHub scraper implementation."""

import logging
import os
from datetime import datetime
from typing import List, Optional
import httpx

from .base import BaseScraper
from ..models import ContentItem, SourceType, GitHubSourceConfig

logger = logging.getLogger(__name__)


class GitHubScraper(BaseScraper):
    """Scraper for GitHub events and releases."""

    def __init__(self, sources: List[GitHubSourceConfig], http_client: httpx.AsyncClient):
        """Initialize GitHub scraper.

        Args:
            sources: List of GitHub source configurations
            http_client: Shared async HTTP client
        """
        super().__init__({"sources": sources}, http_client)
        self.token = os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"

    def _get_headers(self) -> dict:
        """Get request headers with optional authentication.

        Returns:
            dict: HTTP headers
        """
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Horizon-Aggregator"
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers

    async def fetch(self, since: datetime) -> List[ContentItem]:
        """Fetch GitHub content items.

        Args:
            since: Only fetch items published after this time

        Returns:
            List[ContentItem]: Fetched content items
        """
        items = []
        sources = self.config["sources"]

        for source in sources:
            if not source.enabled:
                continue

            if source.type == "user_events" and source.username:
                user_items = await self._fetch_user_events(source.username, since)
                items.extend(user_items)
            elif source.type == "repo_releases" and source.owner and source.repo:
                release_items = await self._fetch_repo_releases(
                    source.owner, source.repo, since
                )
                items.extend(release_items)

        return items

    async def _fetch_user_events(
        self,
        username: str,
        since: datetime
    ) -> List[ContentItem]:
        """Fetch public events for a user.

        Args:
            username: GitHub username
            since: Only fetch events after this time

        Returns:
            List[ContentItem]: Event content items
        """
        url = f"{self.base_url}/users/{username}/events/public"
        items = []

        try:
            response = await self.client.get(url, headers=self._get_headers(), follow_redirects=True)
            response.raise_for_status()
            events = response.json()

            for event in events:
                created_at = datetime.fromisoformat(
                    event["created_at"].replace("Z", "+00:00")
                )

                if created_at < since:
                    continue

                # Filter interesting event types
                event_type = event["type"]
                if event_type not in [
                    "PushEvent", "CreateEvent", "ReleaseEvent",
                    "PublicEvent", "WatchEvent"
                ]:
                    continue

                item = self._parse_event(event, username)
                if item:
                    items.append(item)

        except httpx.HTTPError as e:
            logger.warning("Error fetching GitHub events for %s: %s", username, e)

        return items

    def _parse_event(self, event: dict, username: str) -> Optional[ContentItem]:
        """Parse GitHub event into ContentItem.

        Args:
            event: GitHub event data
            username: GitHub username

        Returns:
            Optional[ContentItem]: Parsed content item or None
        """
        event_type = event["type"]
        event_id = event["id"]
        created_at = datetime.fromisoformat(event["created_at"].replace("Z", "+00:00"))

        repo_name = event["repo"]["name"]
        repo_url = f"https://github.com/{repo_name}"

        # Generate title and content based on event type
        if event_type == "PushEvent":
            commits = event["payload"].get("commits", [])
            title = f"{username} pushed {len(commits)} commit(s) to {repo_name}"
            content = "\n".join([c.get("message", "") for c in commits[:3]])
        elif event_type == "CreateEvent":
            ref_type = event["payload"].get("ref_type", "repository")
            title = f"{username} created {ref_type} in {repo_name}"
            content = event["payload"].get("description", "")
        elif event_type == "ReleaseEvent":
            release = event["payload"].get("release", {})
            title = f"{username} released {release.get('tag_name', '')} in {repo_name}"
            content = release.get("body", "")
            repo_url = release.get("html_url", repo_url)
        elif event_type == "PublicEvent":
            title = f"{username} made {repo_name} public"
            content = ""
        elif event_type == "WatchEvent":
            title = f"{username} starred {repo_name}"
            content = ""
        else:
            return None

        return ContentItem(
            id=self._generate_id("github", "event", event_id),
            source_type=SourceType.GITHUB,
            title=title,
            url=repo_url,
            content=content,
            author=username,
            published_at=created_at,
            metadata={
                "event_type": event_type,
                "repo": repo_name,
            }
        )

    async def _fetch_repo_releases(
        self,
        owner: str,
        repo: str,
        since: datetime
    ) -> List[ContentItem]:
        """Fetch releases for a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            since: Only fetch releases after this time

        Returns:
            List[ContentItem]: Release content items
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/releases"
        items = []

        try:
            response = await self.client.get(url, headers=self._get_headers(), follow_redirects=True)
            response.raise_for_status()
            releases = response.json()

            for release in releases:
                published_at = datetime.fromisoformat(
                    release["published_at"].replace("Z", "+00:00")
                )

                if published_at < since:
                    continue

                item = ContentItem(
                    id=self._generate_id("github", "release", str(release["id"])),
                    source_type=SourceType.GITHUB,
                    title=f"{owner}/{repo} released {release['tag_name']}",
                    url=release["html_url"],
                    content=release.get("body", ""),
                    author=release["author"]["login"],
                    published_at=published_at,
                    metadata={
                        "repo": f"{owner}/{repo}",
                        "tag": release["tag_name"],
                        "prerelease": release.get("prerelease", False),
                    }
                )
                items.append(item)

        except httpx.HTTPError as e:
            logger.warning("Error fetching releases for %s/%s: %s", owner, repo, e)

        return items
