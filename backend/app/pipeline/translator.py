import asyncio
import json
import openai

from app.config import settings


KOREAN_SOURCES = {"hankyung", "mk"}

SYSTEM_PROMPT = """\
당신은 경제 전문 번역가입니다. 영어 경제 뉴스를 자연스러운 한국어로 번역하세요.

용어 규칙:
- Fed/Federal Reserve → 연준
- rate hike → 금리 인상
- rate cut → 금리 인하
- Treasury → 미 국채
- yield → 수익률
- inflation → 인플레이션
- CPI → 소비자물가지수
- GDP → 국내총생산
- bull market → 강세장
- bear market → 약세장

JSON 출력: {"title_ko": "...", "content_ko": "..."}"""


class Translator:
    def __init__(self):
        self._client = openai.AsyncOpenAI(api_key=settings.openai_api_key)

    async def translate(self, article: dict) -> dict:
        """Translate a single article. Adds title_ko and content_ko fields."""
        result = dict(article)

        # Korean outlets: passthrough without LLM
        if article.get("source") in KOREAN_SOURCES:
            result["title_ko"] = article.get("title", "")
            result["content_ko"] = article.get("snippet", "")
            return result

        title = article.get("title", "")
        snippet = article.get("snippet", "")
        user_message = f"제목: {title}\n본문: {snippet}"

        translated = await self._call_llm(user_message)
        if translated is None:
            # Graceful fallback: return original text
            result["title_ko"] = title
            result["content_ko"] = snippet
        else:
            result["title_ko"] = translated.get("title_ko", title)
            result["content_ko"] = translated.get("content_ko", snippet)

        return result

    async def translate_batch(self, articles: list[dict]) -> list[dict]:
        """Translate multiple articles in parallel."""
        return await asyncio.gather(*[self.translate(a) for a in articles])

    async def _call_llm(self, user_message: str) -> dict | None:
        try:
            response = await self._client.chat.completions.create(
                model="gpt-4o-mini",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
            )
            raw = response.choices[0].message.content
            parsed = json.loads(raw)
            if "title_ko" in parsed and "content_ko" in parsed:
                return parsed
            return None
        except (json.JSONDecodeError, KeyError, IndexError, openai.OpenAIError):
            return None
