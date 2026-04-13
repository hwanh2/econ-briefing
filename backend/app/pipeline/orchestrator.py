import asyncio
import json
import logging
import time
from datetime import date
from pathlib import Path

from app.pipeline.sourcer import Sourcer
from app.pipeline.curator import Curator
from app.pipeline.translator import Translator
from app.pipeline.editor import Editor
from app.pipeline.publisher import Publisher

logger = logging.getLogger(__name__)

DEFAULT_SECTORS = ["macro", "finance", "tech", "ai", "energy"]


class Orchestrator:
    async def run(self, sectors: list[str] = None) -> dict:
        sectors = sectors or DEFAULT_SECTORS
        today = date.today().isoformat()
        output_dir = Path("output") / today
        output_dir.mkdir(parents=True, exist_ok=True)

        timings = {}
        result = {"date": today, "sectors": sectors, "timings": timings}

        # Step 1: Source
        raw_articles = await self._run_step(
            "sourcer",
            lambda: Sourcer().collect(),
            timings,
        )
        if raw_articles is None:
            return {**result, "error": "sourcer failed"}
        (output_dir / "raw_articles.json").write_text(
            json.dumps(raw_articles, ensure_ascii=False, indent=2)
        )
        result["raw_count"] = len(raw_articles)
        logger.info("Step 1 done: %d raw articles", len(raw_articles))

        # Step 2: Curate
        curated_articles = await self._run_step(
            "curator",
            lambda: Curator().select(raw_articles, sectors),
            timings,
        )
        if curated_articles is None:
            return {**result, "error": "curator failed"}
        (output_dir / "curated_articles.json").write_text(
            json.dumps(curated_articles, ensure_ascii=False, indent=2)
        )
        result["curated_count"] = len(curated_articles)
        logger.info("Step 2 done: %d curated articles", len(curated_articles))

        # Step 3: Translate
        translated_articles = await self._run_step(
            "translator",
            lambda: Translator().translate_batch(curated_articles),
            timings,
        )
        if translated_articles is None:
            return {**result, "error": "translator failed"}
        (output_dir / "translated_articles.json").write_text(
            json.dumps(translated_articles, ensure_ascii=False, indent=2)
        )
        result["translated_count"] = len(translated_articles)
        logger.info("Step 3 done: %d translated articles", len(translated_articles))

        # Step 4: Edit / compose
        report = await self._run_step(
            "editor",
            lambda: Editor().compose(translated_articles),
            timings,
        )
        if report is None:
            return {**result, "error": "editor failed"}
        (output_dir / "report.md").write_text(report.get("content_md", ""))
        (output_dir / "report.html").write_text(report.get("content_html", ""))
        logger.info("Step 4 done: report composed")

        # Step 5: Save to DB
        report_id = None
        try:
            t0 = time.perf_counter()
            report_id = self._save_to_db(report)
            timings["db_save"] = round(time.perf_counter() - t0, 3)
            result["report_id"] = report_id
            logger.info("Step 5 done: report saved (id=%s)", report_id)
        except Exception as exc:
            logger.error("DB save failed: %s", exc)
            result["db_error"] = str(exc)

        # Step 6: Publish
        try:
            t0 = time.perf_counter()
            subscribers = self._get_active_subscribers()
            publish_result = await Publisher().send(
                report_html=report.get("content_html", ""),
                report_id=report_id,
                subscribers=subscribers,
                db=None,
            )
            timings["publisher"] = round(time.perf_counter() - t0, 3)
            result["publish"] = publish_result
            logger.info("Step 6 done: publish result %s", publish_result)
        except Exception as exc:
            logger.error("Publisher failed: %s", exc)
            result["publish_error"] = str(exc)

        return result

    async def _run_step(self, name: str, fn, timings: dict):
        t0 = time.perf_counter()
        try:
            value = fn()
            if asyncio.iscoroutine(value):
                value = await value
            timings[name] = round(time.perf_counter() - t0, 3)
            return value
        except Exception as exc:
            timings[name] = round(time.perf_counter() - t0, 3)
            logger.error("Step %s failed: %s", name, exc)
            return None

    def _save_to_db(self, report: dict) -> int:
        from app.database import SessionLocal
        from app.models import Report, ReportArticle

        db = SessionLocal()
        try:
            db_report = Report(
                date=date.today(),
                title=report.get("title"),
                content_md=report.get("content_md"),
                content_html=report.get("content_html"),
            )
            db.add(db_report)
            db.commit()
            db.refresh(db_report)

            for article in report.get("articles", []):
                ra = ReportArticle(
                    report_id=db_report.id,
                    title=article.get("title_ko") or article.get("title"),
                    source=article.get("source"),
                    original_url=article.get("url"),
                    summary_ko=article.get("content_ko"),
                    score=article.get("score"),
                    sector=article.get("sector"),
                )
                db.add(ra)
            db.commit()
            return db_report.id
        finally:
            db.close()

    def _get_active_subscribers(self) -> list[dict]:
        from app.database import SessionLocal
        from app.models import Subscriber

        db = SessionLocal()
        try:
            rows = db.query(Subscriber).filter(Subscriber.active == True).all()
            return [{"id": s.id, "email": s.email, "name": s.name} for s in rows]
        finally:
            db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result = asyncio.run(Orchestrator().run())
    print(json.dumps(result, ensure_ascii=False, indent=2))
