import feedparser
import httpx
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime


FEEDS = {
    "reuters": "https://www.reuters.com/arc/outboundfeeds/v3/all/rss.xml",
    "cnbc_economy": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258",
    "marketwatch": "https://feeds.marketwatch.com/marketwatch/topstories",
    "hankyung": "https://www.hankyung.com/feed/economy",
    "mk": "https://www.mk.co.kr/rss/30100041/",
}


def _parse_published(entry) -> str | None:
    """Parse published date from a feedparser entry, return ISO string or None."""
    # feedparser may provide published_parsed (struct_time in UTC)
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            return dt.isoformat()
        except Exception:
            pass

    # Fall back to raw published string
    raw = getattr(entry, "published", None) or getattr(entry, "updated", None)
    if raw:
        try:
            dt = parsedate_to_datetime(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except Exception:
            pass

    return None


def _is_within_24h(published_iso: str | None) -> bool:
    if not published_iso:
        return False
    try:
        dt = datetime.fromisoformat(published_iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        return dt >= cutoff
    except Exception:
        return False


class Sourcer:
    async def collect(self) -> list[dict]:
        """Fetch all RSS feeds and return deduplicated RawArticle dicts from last 24 hours."""
        articles: list[dict] = []
        seen_urls: set[str] = set()

        async with httpx.AsyncClient(timeout=15.0) as client:
            for source, url in FEEDS.items():
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    feed = feedparser.parse(response.text)

                    for entry in feed.entries:
                        article_url = getattr(entry, "link", None)
                        if not article_url or article_url in seen_urls:
                            continue

                        published = _parse_published(entry)
                        if not _is_within_24h(published):
                            continue

                        seen_urls.add(article_url)
                        snippet = (
                            getattr(entry, "summary", None)
                            or getattr(entry, "description", None)
                            or ""
                        )
                        articles.append({
                            "title": getattr(entry, "title", ""),
                            "url": article_url,
                            "source": source,
                            "published": published,
                            "snippet": snippet,
                        })

                except Exception:
                    # One feed failure should not break the whole collection
                    continue

        return articles
