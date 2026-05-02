import asyncio
from datetime import date

import resend

from app.config import settings


class Publisher:
    async def send(
        self,
        report_html: str,
        report_text: str = None,
        report_id: int = None,
        subscribers: list[dict] = None,
        db=None,
    ) -> dict:
        subscribers = subscribers or []

        if not settings.resend_api_key:
            return {
                "sent": 0,
                "failed": 0,
                "skipped": len(subscribers),
                "reason": "no_api_key",
            }

        resend.api_key = settings.resend_api_key
        subject = f"📊 경제 브리핑 — {date.today().strftime('%Y.%m.%d')}"
        sent = 0
        failed = 0

        for sub in subscribers:
            params = {
                "from": "Econ Briefing <briefing@resend.dev>",
                "to": [sub["email"]],
                "subject": subject,
                "html": report_html,
            }
            if report_text:
                params["text"] = report_text

            try:
                await asyncio.to_thread(resend.Emails.send, params)
                sent += 1
                self._log_delivery(db, sub, report_id, "sent")
            except Exception as exc:
                import logging
                logging.getLogger(__name__).warning("Email send failed for %s: %s", sub["email"], exc)
                failed += 1
                self._log_delivery(db, sub, report_id, "failed")

        return {"sent": sent, "failed": failed, "skipped": 0}

    def _log_delivery(self, db, subscriber, report_id, status):
        if db is None or report_id is None:
            return
        try:
            from app.models import DeliveryLog

            log = DeliveryLog(
                subscriber_id=subscriber.get("id"),
                report_id=report_id,
                status=status,
            )
            db.add(log)
            db.commit()
        except Exception:
            db.rollback()
