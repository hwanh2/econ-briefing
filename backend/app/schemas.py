from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, EmailStr


# Subscriber schemas
class SubscriberCreate(BaseModel):
    email: str
    name: Optional[str] = None
    sectors: Optional[List[str]] = None


class SubscriberUpdate(BaseModel):
    name: Optional[str] = None
    sectors: Optional[List[str]] = None
    active: Optional[bool] = None


class SubscriberResponse(BaseModel):
    id: int
    email: str
    name: Optional[str]
    sectors: Optional[List[str]]
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# Article schemas
class ArticleResponse(BaseModel):
    id: int
    report_id: int
    title: Optional[str]
    source: Optional[str]
    original_url: Optional[str]
    summary_ko: Optional[str]
    translation: Optional[str]
    score: Optional[float]
    sector: Optional[str]

    model_config = {"from_attributes": True}


# Report schemas
class ReportListResponse(BaseModel):
    id: int
    date: date
    title: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportResponse(BaseModel):
    id: int
    date: date
    title: Optional[str]
    content_md: Optional[str]
    content_html: Optional[str]
    created_at: datetime
    articles: List[ArticleResponse] = []

    model_config = {"from_attributes": True}
