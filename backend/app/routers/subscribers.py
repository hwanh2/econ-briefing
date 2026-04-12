from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Subscriber
from app.schemas import SubscriberCreate, SubscriberResponse, SubscriberUpdate

router = APIRouter()


@router.post("/subscribers", response_model=SubscriberResponse, status_code=201)
def create_subscriber(body: SubscriberCreate, db: Session = Depends(get_db)):
    existing = db.query(Subscriber).filter(Subscriber.email == body.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    subscriber = Subscriber(**body.model_dump())
    db.add(subscriber)
    db.commit()
    db.refresh(subscriber)
    return subscriber


@router.get("/subscribers", response_model=List[SubscriberResponse])
def list_subscribers(db: Session = Depends(get_db)):
    return db.query(Subscriber).all()


@router.get("/subscribers/{subscriber_id}", response_model=SubscriberResponse)
def get_subscriber(subscriber_id: int, db: Session = Depends(get_db)):
    subscriber = db.query(Subscriber).filter(Subscriber.id == subscriber_id).first()
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    return subscriber


@router.put("/subscribers/{subscriber_id}", response_model=SubscriberResponse)
def update_subscriber(subscriber_id: int, body: SubscriberUpdate, db: Session = Depends(get_db)):
    subscriber = db.query(Subscriber).filter(Subscriber.id == subscriber_id).first()
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(subscriber, field, value)
    db.commit()
    db.refresh(subscriber)
    return subscriber


@router.delete("/subscribers/{subscriber_id}", status_code=204)
def delete_subscriber(subscriber_id: int, db: Session = Depends(get_db)):
    subscriber = db.query(Subscriber).filter(Subscriber.id == subscriber_id).first()
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    db.delete(subscriber)
    db.commit()
