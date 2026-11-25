"""Fetch articles from Argentine economic news RSS feeds."""

import feedparser
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import List, Optional

import yaml

logger = logging.getLogger(__name__)

MAX_ARTICLE_AGE_HOURS = 96  # covers a Monday run reaching back to Friday
USER_AGENT = "24EcoNewsBot/1.0 (+https://www.24econews.com/contact)"


@dataclass
class Article:
    title: str
    url: str
    source: str
    published_at: datetime
    summary: str = ""        # Raw snippet from RSS
    content: str = ""        # Full text if available in feed
    full_summary: str = ""   # Claude-generated summary
    is_relevant: bool = False


def _parse_date(entry) -> Optional[datetime]:
    """Extract publication date from a feed entry, or None if it has none/unparseable."""
    for attr in ("published", "updated"):
        raw = getattr(entry, attr, None)
        if raw:
            try:
                return parsedate_to_datetime(raw)
            except Exception:
                pass
    return None


def fetch_feed(feed_config: dict) -> List[Article]:
    """Fetch and parse a single RSS feed, returning a list of Articles."""
    name = feed_config["name"]
    url = feed_config["url"]
    articles: List[Article] = []

    logger.info(f"Fetching {name} — {url}")
    now = datetime.now(timezone.utc)
    dropped_stale = 0
    no_date = 0
    try:
        feed = feedparser.parse(url, request_headers={"User-Agent": USER_AGENT})
        if feed.bozo:
            logger.warning(f"{name}: feed parse warning — {feed.bozo_exception}")

        for entry in feed.entries:
            link = getattr(entry, "link", None)
            title = getattr(entry, "title", "").strip()
            if not link or not title:
                continue

            published_at = _parse_date(entry)
            if published_at is None:
                no_date += 1
                logger.info(f"{name}: item with no publication date kept — {title!r}")
                published_at = now
            else:
                if published_at.tzinfo is None:
                    published_at = published_at.replace(tzinfo=timezone.utc)
                age = now - published_at
                if age > timedelta(hours=MAX_ARTICLE_AGE_HOURS):
                    dropped_stale += 1
                    continue

            # Prefer full content, fall back to summary/description
            content = ""
            if hasattr(entry, "content") and entry.content:
                content = entry.content[0].get("value", "")
            raw_summary = getattr(entry, "summary", "") or getattr(entry, "description", "")

            articles.append(Article(
                title=title,
                url=link,
                source=name,
                published_at=published_at,
                summary=raw_summary,
                content=content,
            ))
    except Exception as exc:
        logger.error(f"{name}: failed to fetch — {exc}")

    if dropped_stale:
        logger.info(f"{name}: dropped {dropped_stale} article(s) older than {MAX_ARTICLE_AGE_HOURS}h")
    if no_date:
        logger.info(f"{name}: kept {no_date} article(s) with no publication date")
    logger.info(f"{name}: {len(articles)} articles fetched")
    return articles


def fetch_all_feeds(config: dict) -> List[Article]:
    """Fetch all feeds listed in config and return combined article list."""
    all_articles: List[Article] = []
    for feed_config in config.get("rss_feeds", []):
        all_articles.extend(fetch_feed(feed_config))
    logger.info(f"Total articles fetched: {len(all_articles)}")
    return all_articles
