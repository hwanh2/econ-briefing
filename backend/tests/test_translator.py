import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.pipeline.translator import Translator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_article(source="reuters", title="Fed raises rates", snippet="The Federal Reserve raised rates.") -> dict:
    return {
        "title": title,
        "url": "https://example.com/1",
        "source": source,
        "published": "2024-01-01T00:00:00+00:00",
        "snippet": snippet,
    }


def _mock_openai_response(content: str) -> MagicMock:
    message = MagicMock()
    message.content = content

    choice = MagicMock()
    choice.message = message

    response = MagicMock()
    response.choices = [choice]
    return response


def _patch_client(return_value=None, side_effect=None):
    """Return a context manager that patches openai.AsyncOpenAI."""
    mock_completion = AsyncMock(return_value=return_value, side_effect=side_effect)

    mock_chat = MagicMock()
    mock_chat.completions.create = mock_completion

    mock_client = MagicMock()
    mock_client.chat = mock_chat

    return patch("app.pipeline.translator.openai.AsyncOpenAI", return_value=mock_client), mock_completion


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_translate_english_article():
    """translate() calls LLM and returns article with title_ko and content_ko."""
    translated_content = json.dumps({"title_ko": "연준 금리 인상", "content_ko": "연준이 금리를 인상했습니다."})
    response = _mock_openai_response(translated_content)

    patcher, mock_create = _patch_client(return_value=response)
    with patcher:
        translator = Translator()
        result = await translator.translate(_make_article(source="reuters"))

    assert result["title_ko"] == "연준 금리 인상"
    assert result["content_ko"] == "연준이 금리를 인상했습니다."
    # Original fields preserved
    assert result["url"] == "https://example.com/1"
    assert result["source"] == "reuters"
    mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_translate_korean_source_hankyung():
    """hankyung source is passed through without calling LLM."""
    article = _make_article(source="hankyung", title="한국 금리 동결", snippet="한국은행이 금리를 동결했습니다.")

    patcher, mock_create = _patch_client()
    with patcher:
        translator = Translator()
        result = await translator.translate(article)

    assert result["title_ko"] == "한국 금리 동결"
    assert result["content_ko"] == "한국은행이 금리를 동결했습니다."
    mock_create.assert_not_called()


@pytest.mark.asyncio
async def test_translate_korean_source_mk():
    """mk source is passed through without calling LLM."""
    article = _make_article(source="mk", title="MK 경제 뉴스", snippet="MK 뉴스 내용입니다.")

    patcher, mock_create = _patch_client()
    with patcher:
        translator = Translator()
        result = await translator.translate(article)

    assert result["title_ko"] == "MK 경제 뉴스"
    assert result["content_ko"] == "MK 뉴스 내용입니다."
    mock_create.assert_not_called()


@pytest.mark.asyncio
async def test_translate_batch_parallel():
    """translate_batch() translates multiple articles and returns all results."""
    articles = [
        _make_article(source="reuters", title=f"Article {i}", snippet=f"Snippet {i}")
        for i in range(3)
    ]
    translated_content = json.dumps({"title_ko": "번역된 제목", "content_ko": "번역된 내용"})
    response = _mock_openai_response(translated_content)

    patcher, mock_create = _patch_client(return_value=response)
    with patcher:
        translator = Translator()
        results = await translator.translate_batch(articles)

    assert len(results) == 3
    for result in results:
        assert "title_ko" in result
        assert "content_ko" in result
    # LLM called once per article
    assert mock_create.call_count == 3


@pytest.mark.asyncio
async def test_translate_batch_mixed_sources():
    """translate_batch() skips LLM for Korean sources."""
    articles = [
        _make_article(source="reuters"),
        _make_article(source="hankyung", title="한경 기사", snippet="한경 내용"),
        _make_article(source="mk", title="MK 기사", snippet="MK 내용"),
    ]
    translated_content = json.dumps({"title_ko": "번역 제목", "content_ko": "번역 내용"})
    response = _mock_openai_response(translated_content)

    patcher, mock_create = _patch_client(return_value=response)
    with patcher:
        translator = Translator()
        results = await translator.translate_batch(articles)

    assert len(results) == 3
    # Only 1 LLM call (reuters); hankyung and mk are passed through
    assert mock_create.call_count == 1
    assert results[1]["title_ko"] == "한경 기사"
    assert results[2]["title_ko"] == "MK 기사"


@pytest.mark.asyncio
async def test_translate_api_failure_returns_original():
    """On API failure, translate() returns article with original text as _ko fields."""
    import openai as _openai

    article = _make_article(source="reuters", title="Fed raises rates", snippet="The Fed raised rates.")

    patcher, mock_create = _patch_client(side_effect=_openai.OpenAIError("API error"))
    with patcher:
        translator = Translator()
        result = await translator.translate(article)

    assert result["title_ko"] == "Fed raises rates"
    assert result["content_ko"] == "The Fed raised rates."
    assert result["url"] == "https://example.com/1"


@pytest.mark.asyncio
async def test_translate_invalid_json_returns_original():
    """On invalid JSON response, translate() falls back to original text."""
    response = _mock_openai_response("not valid json {{{")

    patcher, _ = _patch_client(return_value=response)
    with patcher:
        translator = Translator()
        result = await translator.translate(_make_article(source="cnbc", title="Market Update", snippet="Markets up."))

    assert result["title_ko"] == "Market Update"
    assert result["content_ko"] == "Markets up."


@pytest.mark.asyncio
async def test_translate_missing_ko_fields_returns_original():
    """If LLM response JSON lacks title_ko/content_ko, fall back to original."""
    response = _mock_openai_response(json.dumps({"unexpected_key": "value"}))

    patcher, _ = _patch_client(return_value=response)
    with patcher:
        translator = Translator()
        result = await translator.translate(_make_article(source="reuters", title="Test", snippet="Test snippet"))

    assert result["title_ko"] == "Test"
    assert result["content_ko"] == "Test snippet"
