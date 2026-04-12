from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Report
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
