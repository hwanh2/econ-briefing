import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.pipeline.curator import Curator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_articles(n: int = 10) -> list[dict]:
    return [
        {
            "title": f"Article {i}",
            "url": f"https://example.com/{i}",
            "source": "reuters",
            "published": "2024-01-01T00:00:00+00:00",
            "snippet": f"Snippet for article {i}.",
        }
        for i in range(n)
    ]


def _llm_response_content(selections: list[dict]) -> str:
    return json.dumps(selections)


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

    return patch("app.pipeline.curator.openai.AsyncOpenAI", return_value=mock_client), mock_completion


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_select_basic():
    """select() returns articles with score, reason, sector fields."""
    articles = _make_articles(10)
    llm_selections = [
        {"index": 0, "score": 9, "reason": "High impact", "sector": "macro"},
        {"index": 2, "score": 7, "reason": "Relevant", "sector": "finance"},
        {"index": 5, "score": 8, "reason": "Important", "sector": "tech"},
    ]
    response = _mock_openai_response(_llm_response_content(llm_selections))

    patcher, _ = _patch_client(return_value=response)
    with patcher:
        curator = Curator()
        result = await curator.select(articles, ["macro", "finance"])

    assert len(result) == 3
    for item in result:
        assert "score" in item
        assert "reason" in item
        assert "sector" in item
        assert "title" in item
        assert "url" in item


@pytest.mark.asyncio
async def test_select_sorted_by_score():
    """Results are sorted by score descending."""
    articles = _make_articles(10)
    llm_selections = [
        {"index": 1, "score": 5, "reason": "OK", "sector": "finance"},
        {"index": 3, "score": 9, "reason": "Top pick", "sector": "macro"},
        {"index": 7, "score": 7, "reason": "Good", "sector": "tech"},
    ]
    response = _mock_openai_response(_llm_response_content(llm_selections))

    patcher, _ = _patch_client(return_value=response)
    with patcher:
        curator = Curator()
        result = await curator.select(articles, ["macro"])

    scores = [r["score"] for r in result]
    assert scores == sorted(scores, reverse=True)
    assert scores[0] == 9


@pytest.mark.asyncio
async def test_select_caps_at_8():
    """At most 8 articles are returned even if LLM returns more."""
    articles = _make_articles(15)
    llm_selections = [
        {"index": i, "score": 10 - i, "reason": "reason", "sector": "macro"}
        for i in range(12)
    ]
    response = _mock_openai_response(_llm_response_content(llm_selections))

    patcher, _ = _patch_client(return_value=response)
    with patcher:
        curator = Curator()
        result = await curator.select(articles, ["macro"])

    assert len(result) <= 8


@pytest.mark.asyncio
async def test_select_empty_input():
    """select() with empty articles returns empty list without calling LLM."""
    patcher, mock_create = _patch_client()
    with patcher:
        curator = Curator()
        result = await curator.select([], ["macro"])

    assert result == []
    mock_create.assert_not_called()


@pytest.mark.asyncio
async def test_select_json_error_retries_then_returns_empty():
    """select() retries once on JSON parse error and returns empty on second failure."""
    import openai as _openai

    patcher, mock_create = _patch_client(side_effect=_openai.OpenAIError("API error"))
    with patcher:
        curator = Curator()
        result = await curator.select(_make_articles(5), ["macro"])

    assert result == []
    # Called twice: first attempt + one retry
    assert mock_create.call_count == 2


@pytest.mark.asyncio
async def test_select_invalid_json_returns_empty():
    """select() handles invalid JSON gracefully."""
    response = _mock_openai_response("not valid json {{{")

    patcher, mock_create = _patch_client(return_value=response)
    with patcher:
        curator = Curator()
        result = await curator.select(_make_articles(5), ["macro"])

    assert result == []
    assert mock_create.call_count == 2


@pytest.mark.asyncio
async def test_select_out_of_bounds_index_skipped():
    """Articles with out-of-bounds index in LLM response are skipped."""
    articles = _make_articles(3)
    llm_selections = [
        {"index": 0, "score": 9, "reason": "Good", "sector": "macro"},
        {"index": 99, "score": 8, "reason": "Out of range", "sector": "finance"},
        {"index": -1, "score": 7, "reason": "Negative", "sector": "tech"},
    ]
    response = _mock_openai_response(_llm_response_content(llm_selections))

    patcher, _ = _patch_client(return_value=response)
    with patcher:
        curator = Curator()
        result = await curator.select(articles, ["macro"])

    assert len(result) == 1
    assert result[0]["url"] == "https://example.com/0"


@pytest.mark.asyncio
async def test_select_llm_response_wrapped_in_dict():
    """select() handles LLM response wrapped in a dict key (e.g. {"articles": [...]})."""
    articles = _make_articles(5)
    llm_selections = [
        {"index": 1, "score": 8, "reason": "Relevant", "sector": "finance"},
    ]
    wrapped = json.dumps({"articles": llm_selections})
    response = _mock_openai_response(wrapped)

    patcher, _ = _patch_client(return_value=response)
    with patcher:
        curator = Curator()
        result = await curator.select(articles, ["finance"])

    assert len(result) == 1
    assert result[0]["sector"] == "finance"
