import json
from datetime import date
import markdown as md
import openai

from app.config import settings


SYSTEM_PROMPT = """\
당신은 경제 브리핑 에디터입니다.
번역된 경제 기사 목록을 받아 독자를 위한 브리핑을 작성하세요.

다음 JSON을 출력하세요:
{
  "summary": "오늘의 핵심 요약 (1-2문장)",
  "articles": [
    {
      "index": 0,
      "impact": "HIGH",
      "key_point": "이 기사의 핵심 포인트 (1-2줄)"
    }
  ]
}

impact 기준:
- HIGH: 시장/경제에 즉각적인 중대한 영향
- MEDIUM: 중요하지만 간접적인 영향
- LOW: 참고 수준의 정보"""


class Editor:
    def __init__(self):
        self._client = openai.AsyncOpenAI(api_key=settings.openai_api_key)

    async def compose(self, articles: list[dict]) -> dict:
        """Compose a report from translated articles. Returns report dict."""
        today = date.today().strftime("%Y.%m.%d")
        title = f"경제 브리핑 — {today}"

        if not articles:
            return {
                "title": title,
                "date": today,
                "summary": "",
                "content_md": "",
                "content_html": "",
                "articles": [],
            }

        llm_result = await self._call_llm(articles)
        if llm_result is None:
            raise RuntimeError("Editor LLM call failed")

        summary = llm_result.get("summary", "")
        article_meta = {item["index"]: item for item in llm_result.get("articles", [])}

        content_md = self._build_markdown(title, today, summary, articles, article_meta)
        content_html = md.markdown(content_md, extensions=["extra"])

        return {
            "title": title,
            "date": today,
            "summary": summary,
            "content_md": content_md,
            "content_html": content_html,
            "articles": articles,
        }

    def _build_markdown(
        self,
        title: str,
        today: str,
        summary: str,
        articles: list[dict],
        article_meta: dict,
    ) -> str:
        lines = [
            f"# 📊 경제 브리핑 — {today}",
            "",
            "## 오늘의 핵심",
            f"> {summary}",
            "",
            "---",
            "",
        ]

        for i, article in enumerate(articles):
            meta = article_meta.get(i, {})
            impact = meta.get("impact", "MEDIUM")
            key_point = meta.get("key_point", "")
            title_ko = article.get("title_ko") or article.get("title", "")
            source = article.get("source", "")
            url = article.get("url", "")
            content_ko = article.get("content_ko") or article.get("snippet", "")

            lines += [
                f"## {i + 1}. [{impact}] {title_ko}",
                f"**출처**: {source} | [원문 보기]({url})",
                "",
                content_ko,
                "",
                f"**핵심**: {key_point}",
                "",
                "---",
                "",
            ]

        return "\n".join(lines)

    async def _call_llm(self, articles: list[dict]) -> dict | None:
        user_lines = []
        for i, a in enumerate(articles):
            title_ko = a.get("title_ko") or a.get("title", "")
            content_ko = a.get("content_ko") or a.get("snippet", "")
            user_lines.append(f"[{i}] {title_ko}\n{content_ko[:300]}")
        user_message = "\n\n".join(user_lines)

        try:
            response = await self._client.chat.completions.create(
                model="gpt-4o",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
            )
            raw = response.choices[0].message.content
            parsed = json.loads(raw)
            if "summary" in parsed and "articles" in parsed:
                return parsed
            return None
        except (json.JSONDecodeError, KeyError, IndexError, openai.OpenAIError):
            return None
