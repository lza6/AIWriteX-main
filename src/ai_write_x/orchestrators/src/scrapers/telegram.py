"""Telegram public channel scraper implementation."""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import List, Optional

import httpx
from bs4 import BeautifulSoup

from .base import BaseScraper
from ..models import ContentItem, TelegramConfig, TelegramChannelConfig, SourceType

logger = logging.getLogger(__name__)

TELEGRAM_WEB_BASE = "https://t.me/s"
USER_AGENT = "Mozilla/5.0 (compatible; Horizon/1.0; +https://github.com/thysrael/horizon)"


class TelegramScraper(BaseScraper):
    """Scraper for Telegram public channels via web preview."""

    def __init__(self, config: TelegramConfig, http_client: httpx.AsyncClient):
        super().__init__(config.model_dump(), http_client)
        self.telegram_config = config

    async def fetch(self, since: datetime) -> List[ContentItem]:
        if not self.config.get("enabled", True):
            return []

        tasks = []
        for channel_cfg in self.telegram_config.channels:
            if channel_cfg.enabled:
                tasks.append(self._fetch_channel(channel_cfg, since))

        if not tasks:
            return []

        results = await asyncio.gather(*tasks, return_exceptions=True)
        items = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning("Error fetching Telegram channel: %s", result)
            elif isinstance(result, list):
                items.extend(result)
        return items

    async def _fetch_channel(self, cfg: TelegramChannelConfig, since: datetime) -> List[ContentItem]:
        url = f"{TELEGRAM_WEB_BASE}/{cfg.channel}"
        headers = {"User-Agent": USER_AGENT}
        try:
            response = await self.client.get(url, headers=headers, follow_redirects=True, timeout=120.0)
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 5))
                logger.warning("Telegram rate limited for %s, retrying after %ds", cfg.channel, retry_after)
                await asyncio.sleep(retry_after)
                response = await self.client.get(url, headers=headers, follow_redirects=True, timeout=120.0)
            response.raise_for_status()
        except Exception as e:
            logger.warning("Telegram request failed for %s: [%s] %r", cfg.channel, type(e).__name__, e)
            return []

        return self._parse_channel_html(response.text, cfg, since)

    def _parse_channel_html(
        self, html: str, cfg: TelegramChannelConfig, since: datetime
    ) -> List[ContentItem]:
        soup = BeautifulSoup(html, "html.parser")
        messages = soup.select("div.tgme_widget_message[data-post]")

        items = []
        for msg in messages[-cfg.fetch_limit:]:
            item = self._parse_message(msg, cfg.channel, since)
            if item:
                items.append(item)
        return items

    def _parse_message(
        self, msg_el, channel: str, since: datetime
    ) -> Optional[ContentItem]:
        # Extract message ID
        data_post = msg_el.get("data-post", "")
        msg_id = data_post.split("/")[-1] if "/" in data_post else data_post
        if not msg_id:
            return None

        # Extract timestamp
        time_el = msg_el.select_one("time[datetime]")
        if not time_el:
            return None
        try:
            published_at = datetime.fromisoformat(time_el["datetime"].replace("Z", "+00:00"))
        except (ValueError, KeyError):
            return None

        if published_at < since:
            return None

        # Extract message text
        text_el = msg_el.select_one("div.tgme_widget_message_text")
        if not text_el:
            return None

        # Convert <br> to newlines, then strip tags
        for br in text_el.find_all("br"):
            br.replace_with("\n")
        raw_text = text_el.get_text(separator="")
        text = raw_text.strip()

        if not text:
            return None

        # Generate title from first paragraph
        title = self._make_title(text)

        # Find first external link as canonical URL; fallback to message URL
        msg_url = f"https://t.me/{channel}/{msg_id}"
        canonical_url = msg_url
        for a in text_el.find_all("a", href=True):
            href = a["href"]
            if href.startswith("http") and "t.me" not in href:
                canonical_url = href
                break

        return ContentItem(
            id=self._generate_id("telegram", channel, msg_id),
            source_type=SourceType.TELEGRAM,
            title=title,
            url=canonical_url,
            content=text,
            author=channel,
            published_at=published_at,
            metadata={"msg_url": msg_url, "channel": channel},
        )

    @staticmethod
    def _make_title(text: str) -> str:
        # Take first paragraph (split on double newline)
        first_para = text.split("\n\n")[0].replace("\n", " ").strip()

        if len(first_para) <= 80:
            return first_para

        # Try to break at a Chinese sentence-ending punctuation within first 80 chars
        match = re.search(r"[。！？]", first_para[:80])
        if match:
            return first_para[: match.end()]

        # Fallback: hard truncate
        return first_para[:80]
