import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import openai as _openai

from app.pipeline.editor import Editor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_article(index: int = 0) -> dict:
    return {
        "title": f"Article {index}",
        "title_ko": f"기사 {index}",
        "url": f"https://example.com/{index}",
        "source": "reuters",
        "published": "2024-01-01T00:00:00+00:00",
        "snippet": f"Snippet {index}",
        "content_ko": f"내용 {index}",
        "score": 9 - index,
        "sector": "macro",
    }


def _mock_openai_response(content: str) -> MagicMock:
    message = MagicMock()
    message.content = content

    choice = MagicMock()
    choice.message = message

    response = MagicMock()
    response.choices = [choice]
    return response


def _llm_result(articles: list[dict]) -> str:
    return json.dumps({
        "summary": "오늘 시장은 연준 금리 동결 소식으로 혼조세를 보였습니다.",
        "articles": [
            {"index": i, "impact": "HIGH" if i == 0 else "MEDIUM", "key_point": f"핵심 포인트 {i}"}
            for i in range(len(articles))
        ],
    })


def _patch_client(return_value=None, side_effect=None):
    mock_completion = AsyncMock(return_value=return_value, side_effect=side_effect)

    mock_chat = MagicMock()
    mock_chat.completions.create = mock_completion

    mock_client = MagicMock()
    mock_client.chat = mock_chat

    return patch("app.pipeline.editor.openai.AsyncOpenAI", return_value=mock_client), mock_completion


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_compose_basic_structure():
    """compose() returns dict with all required keys."""
    articles = [_make_article(0), _make_article(1)]
    response = _mock_openai_response(_llm_result(articles))

    patcher, _ = _patch_client(return_value=response)
    with patcher:
        editor = Editor()
        result = await editor.compose(articles)

    assert "title" in result
    assert "date" in result
    assert "summary" in result
    assert "content_md" in result
    assert "content_html" in result
    assert "articles" in result
    assert result["articles"] == articles


@pytest.mark.asyncio
async def test_compose_title_format():
    """Title follows '경제 브리핑 — YYYY.MM.DD' format."""
    articles = [_make_article(0)]
    response = _mock_openai_response(_llm_result(articles))

    patcher, _ = _patch_client(return_value=response)
    with patcher:
        editor = Editor()
        result = await editor.compose(articles)

    import re
    assert re.match(r"경제 브리핑 — \d{4}\.\d{2}\.\d{2}", result["title"])


@pytest.mark.asyncio
async def test_compose_markdown_structure():
    """Markdown report contains expected sections."""
    articles = [_make_article(0), _make_article(1)]
    response = _mock_openai_response(_llm_result(articles))

    patcher, _ = _patch_client(return_value=response)
    with patcher:
        editor = Editor()
        result = await editor.compose(articles)

    md = result["content_md"]
    assert "## 오늘의 핵심" in md
    assert "기사 0" in md
    assert "기사 1" in md
    assert "reuters" in md
    assert "https://example.com/0" in md


@pytest.mark.asyncio
async def test_compose_impact_tags():
    """Markdown contains impact tags (HIGH/MEDIUM/LOW)."""
    articles = [_make_article(0), _make_article(1)]
    response = _mock_openai_response(_llm_result(articles))

    patcher, _ = _patch_client(return_value=response)
    with patcher:
        editor = Editor()
        result = await editor.compose(articles)

    md = result["content_md"]
    assert "[HIGH]" in md
    assert "[MEDIUM]" in md


@pytest.mark.asyncio
async def test_compose_html_conversion():
    """content_html is non-empty HTML converted from markdown."""
    articles = [_make_article(0)]
    response = _mock_openai_response(_llm_result(articles))

    patcher, _ = _patch_client(return_value=response)
    with patcher:
        editor = Editor()
        result = await editor.compose(articles)

    html = result["content_html"]
    assert "<h1" in html or "<h2" in html
    assert "<" in html and ">" in html


@pytest.mark.asyncio
async def test_compose_summary_from_llm():
    """summary field comes from LLM output."""
    articles = [_make_article(0)]
    response = _mock_openai_response(_llm_result(articles))

    patcher, _ = _patch_client(return_value=response)
    with patcher:
        editor = Editor()
        result = await editor.compose(articles)

    assert result["summary"] == "오늘 시장은 연준 금리 동결 소식으로 혼조세를 보였습니다."
    assert result["summary"] in result["content_md"]


@pytest.mark.asyncio
async def test_compose_empty_articles():
    """Empty articles list returns empty report without calling LLM."""
    patcher, mock_create = _patch_client()
    with patcher:
        editor = Editor()
        result = await editor.compose([])

    assert result["summary"] == ""
    assert result["content_md"] == ""
    assert result["content_html"] == ""
    assert result["articles"] == []
    mock_create.assert_not_called()


@pytest.mark.asyncio
async def test_compose_llm_failure_raises():
    """RuntimeError is raised when LLM call fails."""
    articles = [_make_article(0)]

    patcher, _ = _patch_client(side_effect=_openai.OpenAIError("API error"))
    with patcher:
        editor = Editor()
        with pytest.raises(RuntimeError, match="Editor LLM call failed"):
            await editor.compose(articles)


@pytest.mark.asyncio
async def test_compose_llm_invalid_json_raises():
    """RuntimeError is raised when LLM returns invalid JSON."""
    articles = [_make_article(0)]
    response = _mock_openai_response("not valid json {{{")

    patcher, _ = _patch_client(return_value=response)
    with patcher:
        editor = Editor()
        with pytest.raises(RuntimeError, match="Editor LLM call failed"):
            await editor.compose(articles)


@pytest.mark.asyncio
async def test_compose_key_point_in_markdown():
    """핵심: key_point appears in each article section."""
    articles = [_make_article(0)]
    response = _mock_openai_response(_llm_result(articles))

    patcher, _ = _patch_client(return_value=response)
    with patcher:
        editor = Editor()
        result = await editor.compose(articles)

    assert "**핵심**: 핵심 포인트 0" in result["content_md"]
