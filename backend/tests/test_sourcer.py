import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.pipeline.sourcer import Sourcer, _parse_published, _is_within_24h


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rss_xml(entries: list[dict]) -> str:
    """Build a minimal RSS 2.0 feed XML string from a list of entry dicts."""
    items = ""
    for e in entries:
        items += f"""
        <item>
            <title>{e.get('title', 'Test Title')}</title>
            <link>{e.get('link', 'https://example.com/1')}</link>
            <description>{e.get('description', 'A snippet.')}</description>
            <pubDate>{e.get('pubDate', '')}</pubDate>
        </item>"""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <link>https://example.com</link>
    <description>Test</description>
    {items}
  </channel>
</rss>"""


def _recent_pubdate(hours_ago: float = 1) -> str:
    """Return an RFC-2822 formatted date string N hours in the past."""
    dt = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")


def _old_pubdate(hours_ago: float = 25) -> str:
    return _recent_pubdate(hours_ago)


def _mock_response(text: str, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.text = text
    resp.status_code = status_code
    resp.raise_for_status = MagicMock(
        side_effect=None if status_code < 400 else Exception(f"HTTP {status_code}")
    )
    return resp


# ---------------------------------------------------------------------------
# Unit tests for helper functions
# ---------------------------------------------------------------------------

def test_is_within_24h_recent():
    iso = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    assert _is_within_24h(iso) is True


def test_is_within_24h_old():
    iso = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
    assert _is_within_24h(iso) is False


def test_is_within_24h_none():
    assert _is_within_24h(None) is False


def test_parse_published_from_published_parsed():
    import time
    now = datetime.now(timezone.utc)
    entry = MagicMock()
    entry.published_parsed = now.timetuple()
    result = _parse_published(entry)
    assert result is not None
    parsed = datetime.fromisoformat(result)
    assert abs((parsed - now).total_seconds()) < 2


def test_parse_published_fallback_to_raw():
    entry = MagicMock()
    entry.published_parsed = None
    entry.published = _recent_pubdate(2)
    entry.updated = None
    result = _parse_published(entry)
    assert result is not None


def test_parse_published_no_date():
    entry = MagicMock()
    entry.published_parsed = None
    entry.published = None
    entry.updated = None
    result = _parse_published(entry)
    assert result is None


# ---------------------------------------------------------------------------
# Integration-style tests for Sourcer.collect()
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_collect_basic():
    """collect() returns articles from a valid feed."""
    xml = _rss_xml([
        {"title": "Rates Rise", "link": "https://reuters.com/1", "description": "Central bank hikes rates.", "pubDate": _recent_pubdate(1)},
        {"title": "Markets Up", "link": "https://reuters.com/2", "description": "Stocks climb.", "pubDate": _recent_pubdate(2)},
    ])
    mock_resp = _mock_response(xml)

    with patch("app.pipeline.sourcer.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(return_value=mock_resp)

        sourcer = Sourcer()
        articles = await sourcer.collect()

    assert len(articles) == 2
    urls = {a["url"] for a in articles}
    assert "https://reuters.com/1" in urls
    assert "https://reuters.com/2" in urls

    article = next(a for a in articles if a["url"] == "https://reuters.com/1")
    assert article["title"] == "Rates Rise"
    assert article["snippet"] == "Central bank hikes rates."
    assert article["published"] is not None


@pytest.mark.asyncio
async def test_collect_deduplication():
    """Duplicate URLs across feeds are collected only once."""
    shared_url = "https://example.com/shared"
    xml = _rss_xml([
        {"title": "Shared Article", "link": shared_url, "pubDate": _recent_pubdate(1)},
    ])
    mock_resp = _mock_response(xml)

    with patch("app.pipeline.sourcer.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(return_value=mock_resp)

        sourcer = Sourcer()
        articles = await sourcer.collect()

    # Five feeds all return the same URL — should deduplicate to 1
    assert len(articles) == 1
    assert articles[0]["url"] == shared_url


@pytest.mark.asyncio
async def test_collect_24h_filter():
    """Articles older than 24 hours are excluded."""
    xml = _rss_xml([
        {"title": "Fresh News", "link": "https://example.com/fresh", "pubDate": _recent_pubdate(1)},
        {"title": "Old News", "link": "https://example.com/old", "pubDate": _old_pubdate(30)},
    ])
    mock_resp = _mock_response(xml)

    with patch("app.pipeline.sourcer.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(return_value=mock_resp)

        sourcer = Sourcer()
        articles = await sourcer.collect()

    urls = {a["url"] for a in articles}
    assert "https://example.com/fresh" in urls
    assert "https://example.com/old" not in urls


@pytest.mark.asyncio
async def test_collect_failed_feed_continues():
    """A failed feed does not prevent other feeds from being collected."""
    bad_resp = _mock_response("", status_code=500)
    bad_resp.raise_for_status = MagicMock(side_effect=Exception("HTTP 500"))

    call_count = 0

    async def fake_get(url, **kwargs):
        nonlocal call_count
        call_count += 1
        # First call fails, subsequent succeed with unique URLs per call
        if call_count == 1:
            return bad_resp
        good_xml = _rss_xml([
            {"title": f"Good Article {call_count}", "link": f"https://good.com/{call_count}", "pubDate": _recent_pubdate(1)},
        ])
        return _mock_response(good_xml)

    with patch("app.pipeline.sourcer.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(side_effect=fake_get)

        sourcer = Sourcer()
        articles = await sourcer.collect()

    # 1 failed feed + 4 successful feeds with unique URLs = 4 articles
    assert len(articles) == 4


@pytest.mark.asyncio
async def test_collect_all_feeds_fail():
    """If all feeds fail, collect() returns an empty list."""
    with patch("app.pipeline.sourcer.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(side_effect=Exception("connection error"))

        sourcer = Sourcer()
        articles = await sourcer.collect()

    assert articles == []


@pytest.mark.asyncio
async def test_collect_article_has_required_fields():
    """Every returned article has the required RawArticle fields."""
    xml = _rss_xml([
        {"title": "Test", "link": "https://example.com/a", "description": "snippet", "pubDate": _recent_pubdate(1)},
    ])
    mock_resp = _mock_response(xml)

    with patch("app.pipeline.sourcer.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(return_value=mock_resp)

        sourcer = Sourcer()
        articles = await sourcer.collect()

    assert len(articles) >= 1
    for article in articles:
        for field in ("title", "url", "source", "published", "snippet"):
            assert field in article, f"Missing field: {field}"
