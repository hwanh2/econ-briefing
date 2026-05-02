from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Report, Subscriber
from app.schemas import ReportListResponse, ReportResponse

router = APIRouter()


@router.get("/reports", response_model=List[ReportListResponse])
def list_reports(db: Session = Depends(get_db)):
    return db.query(Report).order_by(Report.date.desc()).all()


@router.get("/reports/{report_id}", response_model=ReportResponse)
def get_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.post("/reports/{report_id}/send")
async def send_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if not report.content_html and not report.content_md:
        raise HTTPException(status_code=400, detail="Report has no content")

    subscribers = db.query(Subscriber).filter(Subscriber.active == True).all()
    subscriber_dicts = [
        {"id": s.id, "email": s.email, "name": s.name}
        for s in subscribers
    ]

    if report.content_html:
        report_html = report.content_html
        report_text = report.content_md or ""
    else:
        report_text = report.content_md
        report_html = f"<pre style='font-family:sans-serif;white-space:pre-wrap'>{report_text}</pre>"

    from app.pipeline.publisher import Publisher
    result = await Publisher().send(
        report_html=report_html,
        report_text=report_text,
        report_id=report.id,
        subscribers=subscriber_dicts,
        db=db,
    )
    return result
