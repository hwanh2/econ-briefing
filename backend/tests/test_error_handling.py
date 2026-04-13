"""Error handling / resilience tests.

Verifies that each pipeline component degrades gracefully:
- RSS feed timeout → Sourcer returns partial results
- All feeds fail → Sourcer returns empty list
- LLM API timeout on Curator → returns empty list
- LLM API error on Translator → returns original text (fallback)
- Publisher with no API key → skips gracefully
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import openai as _openai


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rss_xml(entries: list[dict]) -> str:
    """Build a minimal RSS 2.0 feed XML string."""
    from datetime import datetime, timezone, timedelta

    items = ""
    for e in entries:
        dt = datetime.now(timezone.utc) - timedelta(hours=1)
        pub_date = e.get("pubDate", dt.strftime("%a, %d %b %Y %H:%M:%S +0000"))
        items += f"""
        <item>
            <title>{e.get('title', 'Title')}</title>
            <link>{e.get('link', 'https://example.com/1')}</link>
            <description>{e.get('description', 'Snippet.')}</description>
            <pubDate>{pub_date}</pubDate>
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


def _mock_resp(xml: str, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.text = xml
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    return resp


def _mock_openai_response(content: str) -> MagicMock:
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


# ---------------------------------------------------------------------------
# Sourcer error handling
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sourcer_feed_timeout_returns_partial():
    """One feed timing out still returns results from the other feeds."""
    import httpx
    from app.pipeline.sourcer import Sourcer

    call_count = 0

    async def fake_get(url, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise httpx.TimeoutException("connect timeout")
        good_xml = _rss_xml([
            {"title": f"Article {call_count}", "link": f"https://good.com/{call_count}"},
        ])
        return _mock_resp(good_xml)

    with patch("app.pipeline.sourcer.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(side_effect=fake_get)

        articles = await Sourcer().collect()

    # First feed timed out, remaining 4 succeed
    assert len(articles) == 4


@pytest.mark.asyncio
async def test_sourcer_all_feeds_fail_returns_empty():
    """If every feed raises an exception, collect() returns an empty list."""
    from app.pipeline.sourcer import Sourcer

    with patch("app.pipeline.sourcer.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(side_effect=Exception("network unreachable"))

        articles = await Sourcer().collect()

    assert articles == []


@pytest.mark.asyncio
async def test_sourcer_http_error_returns_partial():
    """HTTP 500 from one feed does not stop other feeds from returning results."""
    from app.pipeline.sourcer import Sourcer

    call_count = 0

    async def fake_get(url, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            bad = MagicMock()
            bad.raise_for_status = MagicMock(side_effect=Exception("HTTP 500"))
            bad.text = ""
            bad.status_code = 500
            return bad
        good_xml = _rss_xml([
            {"title": f"Good {call_count}", "link": f"https://good.com/{call_count}"},
        ])
        return _mock_resp(good_xml)

    with patch("app.pipeline.sourcer.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(side_effect=fake_get)

        articles = await Sourcer().collect()

    assert len(articles) == 4


# ---------------------------------------------------------------------------
# Curator error handling
# ---------------------------------------------------------------------------

def _curator_patch(side_effect):
    mock_completion = AsyncMock(side_effect=side_effect)
    mock_chat = MagicMock()
    mock_chat.completions.create = mock_completion
    mock_client = MagicMock()
    mock_client.chat = mock_chat
    return patch("app.pipeline.curator.openai.AsyncOpenAI", return_value=mock_client), mock_completion


@pytest.mark.asyncio
async def test_curator_llm_timeout_returns_empty():
    """LLM API timeout causes Curator.select() to return an empty list."""
    from app.pipeline.curator import Curator

    articles = [
        {"title": f"Article {i}", "url": f"https://example.com/{i}",
         "source": "reuters", "published": "2026-04-13", "snippet": f"Snippet {i}"}
        for i in range(5)
    ]

    patcher, _ = _curator_patch(side_effect=_openai.APITimeoutError("request timed out"))
    with patcher:
        result = await Curator().select(articles, ["macro"])

    assert result == []


@pytest.mark.asyncio
async def test_curator_api_error_returns_empty():
    """Any OpenAI API error causes Curator.select() to return an empty list."""
    from app.pipeline.curator import Curator

    articles = [
        {"title": "Test", "url": "https://example.com/1",
         "source": "cnbc", "published": "2026-04-13", "snippet": "Test snippet"}
    ]

    patcher, mock_create = _curator_patch(side_effect=_openai.OpenAIError("service unavailable"))
    with patcher:
        result = await Curator().select(articles, ["macro"])

    assert result == []
    # Retries once then gives up
    assert mock_create.call_count == 2


@pytest.mark.asyncio
async def test_curator_malformed_json_returns_empty():
    """Malformed LLM JSON response causes Curator to return empty list after retry."""
    import json
    from app.pipeline.curator import Curator

    articles = [
        {"title": "Test", "url": "https://example.com/1",
         "source": "reuters", "published": "2026-04-13", "snippet": "Snippet"}
    ]

    response = _mock_openai_response("{invalid json[[")

    mock_completion = AsyncMock(return_value=response)
    mock_chat = MagicMock()
    mock_chat.completions.create = mock_completion
    mock_client = MagicMock()
    mock_client.chat = mock_chat

    with patch("app.pipeline.curator.openai.AsyncOpenAI", return_value=mock_client):
        result = await Curator().select(articles, ["macro"])

    assert result == []
    assert mock_completion.call_count == 2


# ---------------------------------------------------------------------------
# Translator error handling
# ---------------------------------------------------------------------------

def _translator_patch(side_effect=None, return_value=None):
    mock_completion = AsyncMock(return_value=return_value, side_effect=side_effect)
    mock_chat = MagicMock()
    mock_chat.completions.create = mock_completion
    mock_client = MagicMock()
    mock_client.chat = mock_chat
    return patch("app.pipeline.translator.openai.AsyncOpenAI", return_value=mock_client), mock_completion


@pytest.mark.asyncio
async def test_translator_api_timeout_returns_original_text():
    """LLM API timeout causes Translator to fall back to original title/snippet."""
    from app.pipeline.translator import Translator

    article = {
        "title": "Fed raises rates",
        "url": "https://example.com/1",
        "source": "reuters",
        "published": "2026-04-13",
        "snippet": "The Fed raised rates by 25bps.",
    }

    patcher, _ = _translator_patch(side_effect=_openai.APITimeoutError("timeout"))
    with patcher:
        result = await Translator().translate(article)

    assert result["title_ko"] == "Fed raises rates"
    assert result["content_ko"] == "The Fed raised rates by 25bps."
    assert result["url"] == "https://example.com/1"


@pytest.mark.asyncio
async def test_translator_api_error_returns_original_text():
    """Any OpenAI error in translate() falls back to the original text."""
    from app.pipeline.translator import Translator

    article = {
        "title": "Market crash",
        "url": "https://example.com/2",
        "source": "cnbc",
        "published": "2026-04-13",
        "snippet": "Markets dropped 3%.",
    }

    patcher, _ = _translator_patch(side_effect=_openai.OpenAIError("quota exceeded"))
    with patcher:
        result = await Translator().translate(article)

    assert result["title_ko"] == "Market crash"
    assert result["content_ko"] == "Markets dropped 3%."


@pytest.mark.asyncio
async def test_translator_batch_partial_failure():
    """If one article fails translation, others still succeed."""
    import json
    from app.pipeline.translator import Translator

    ok_content = json.dumps({"title_ko": "번역된 제목", "content_ko": "번역된 내용"})
    ok_response = _mock_openai_response(ok_content)

    articles = [
        {"title": "Article 1", "url": "https://example.com/1", "source": "reuters",
         "published": "2026-04-13", "snippet": "Snippet 1"},
        {"title": "Article 2", "url": "https://example.com/2", "source": "cnbc",
         "published": "2026-04-13", "snippet": "Snippet 2"},
    ]

    call_count = 0

    async def fake_create(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise _openai.OpenAIError("first call fails")
        return ok_response

    mock_chat = MagicMock()
    mock_chat.completions.create = AsyncMock(side_effect=fake_create)
    mock_client = MagicMock()
    mock_client.chat = mock_chat

    with patch("app.pipeline.translator.openai.AsyncOpenAI", return_value=mock_client):
        results = await Translator().translate_batch(articles)

    assert len(results) == 2
    # First article falls back to original
    assert results[0]["title_ko"] == "Article 1"
    assert results[0]["content_ko"] == "Snippet 1"
    # Second article translated successfully
    assert results[1]["title_ko"] == "번역된 제목"
    assert results[1]["content_ko"] == "번역된 내용"


# ---------------------------------------------------------------------------
# Publisher error handling
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_publisher_no_api_key_skips_all():
    """Publisher with no RESEND_API_KEY skips all subscribers gracefully."""
    from app.pipeline.publisher import Publisher

    subscribers = [
        {"id": 1, "email": "alice@test.com", "name": "Alice"},
        {"id": 2, "email": "bob@test.com", "name": "Bob"},
    ]

    with patch("app.pipeline.publisher.settings") as mock_settings:
        mock_settings.resend_api_key = ""
        result = await Publisher().send("<h1>Report</h1>", subscribers=subscribers)

    assert result["skipped"] == 2
    assert result["sent"] == 0
    assert result.get("reason") == "no_api_key"


@pytest.mark.asyncio
async def test_publisher_empty_api_key_no_crash():
    """Publisher with empty API key does not raise, returns skipped result."""
    from app.pipeline.publisher import Publisher

    with patch("app.pipeline.publisher.settings") as mock_settings:
        mock_settings.resend_api_key = None
        result = await Publisher().send(
            "<h1>Report</h1>",
            subscribers=[{"id": 1, "email": "test@test.com", "name": "Test"}],
        )

    # Should not raise; returns a result dict
    assert isinstance(result, dict)
    assert result.get("sent", 0) == 0


@pytest.mark.asyncio
async def test_publisher_send_failure_counted_as_failed():
    """Individual send failures are counted but do not abort remaining sends."""
    from app.pipeline.publisher import Publisher

    subscribers = [
        {"id": 1, "email": "alice@test.com", "name": "Alice"},
        {"id": 2, "email": "bob@test.com", "name": "Bob"},
        {"id": 3, "email": "carol@test.com", "name": "Carol"},
    ]

    with (
        patch("app.pipeline.publisher.settings") as mock_settings,
        patch("app.pipeline.publisher.resend") as mock_resend,
    ):
        mock_settings.resend_api_key = "re_test_key"
        mock_resend.Emails.send.side_effect = [
            {"id": "msg_1"},
            Exception("SMTP error"),
            {"id": "msg_3"},
        ]
        result = await Publisher().send("<h1>Report</h1>", subscribers=subscribers)

    assert result["sent"] == 2
    assert result["failed"] == 1


@pytest.mark.asyncio
async def test_publisher_no_subscribers_returns_zero():
    """Publisher with empty subscriber list returns all-zero result without error."""
    from app.pipeline.publisher import Publisher

    with patch("app.pipeline.publisher.settings") as mock_settings:
        mock_settings.resend_api_key = "re_test_key"
        result = await Publisher().send("<h1>Report</h1>", subscribers=[])

    assert result["sent"] == 0
    assert result["failed"] == 0
