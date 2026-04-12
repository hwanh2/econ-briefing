import json
import openai

from app.config import settings


SYSTEM_PROMPT_TEMPLATE = """\
당신은 경제 뉴스 에디터입니다.
구독자 관심 섹터: {sectors}

아래 기사 목록에서 읽을 가치가 높은 순서대로 5~8개를 선별하세요.
각 기사에 1-10 스코어와 선정 이유를 달아주세요.
섹터도 지정하세요: macro, finance, tech, ai, energy, realestate, politics, startup

JSON 출력: [{{"index": 0, "score": 9, "reason": "...", "sector": "macro"}}, ...]"""


class Curator:
    def __init__(self):
        self._client = openai.AsyncOpenAI(api_key=settings.openai_api_key)

    async def select(self, articles: list[dict], sectors: list[str]) -> list[dict]:
        """Score and select articles using LLM. Returns curated articles sorted by score."""
        if not articles:
            return []

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(sectors=", ".join(sectors))

        user_lines = []
        for i, a in enumerate(articles):
            user_lines.append(
                f"[{i}] {a.get('title', '')} ({a.get('source', '')}) - {a.get('snippet', '')[:200]}"
            )
        user_message = "\n".join(user_lines)

        selections = await self._call_llm(system_prompt, user_message)
        if selections is None:
            # Retry once
            selections = await self._call_llm(system_prompt, user_message)
        if selections is None:
            return []

        result = []
        for item in selections:
            idx = item.get("index")
            if idx is None or not (0 <= idx < len(articles)):
                continue
            article = dict(articles[idx])
            article["score"] = item.get("score", 0)
            article["reason"] = item.get("reason", "")
            article["sector"] = item.get("sector", "")
            result.append(article)

        result.sort(key=lambda x: x["score"], reverse=True)
        return result[:8]

    async def _call_llm(self, system_prompt: str, user_message: str) -> list[dict] | None:
        try:
            response = await self._client.chat.completions.create(
                model="gpt-4o",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )
            raw = response.choices[0].message.content
            parsed = json.loads(raw)
            # Accept either a bare list or {"articles": [...]} wrapper
            if isinstance(parsed, list):
                return parsed
            for value in parsed.values():
                if isinstance(value, list):
                    return value
            return None
        except (json.JSONDecodeError, KeyError, IndexError, openai.OpenAIError):
            return None
