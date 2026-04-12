from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey, Date
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
from app.database import Base


class Subscriber(Base):
    __tablename__ = "subscribers"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)
    sectors = Column(ARRAY(String), nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    delivery_logs = relationship("DeliveryLog", back_populates="subscriber")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, nullable=False)
    title = Column(String, nullable=True)
    content_md = Column(Text, nullable=True)
    content_html = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    articles = relationship("ReportArticle", back_populates="report")
    delivery_logs = relationship("DeliveryLog", back_populates="report")


class ReportArticle(Base):
    __tablename__ = "report_articles"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    title = Column(String, nullable=True)
    source = Column(String, nullable=True)
    original_url = Column(String, nullable=True)
    summary_ko = Column(Text, nullable=True)
    translation = Column(Text, nullable=True)
    score = Column(Float, nullable=True)
    sector = Column(String, nullable=True)

    report = relationship("Report", back_populates="articles")


class DeliveryLog(Base):
    __tablename__ = "delivery_logs"

    id = Column(Integer, primary_key=True, index=True)
    subscriber_id = Column(Integer, ForeignKey("subscribers.id"), nullable=False)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, nullable=True)  # 'sent', 'failed', 'skipped'

    subscriber = relationship("Subscriber", back_populates="delivery_logs")
    report = relationship("Report", back_populates="delivery_logs")
