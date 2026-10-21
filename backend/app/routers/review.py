"""Reviewer pages: the queue, one item in detail, decisions, the golden set."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import GoldenItem, ReviewItem, Run
from app.services import review
from app.services.workflow import run_to_dict

router = APIRouter(prefix="/api/review", tags=["review"])


class Decision(BaseModel):
    action: str  # approve | correct | reject
    reason: str = Field(default="", max_length=500)
    corrected_answer: str = Field(default="", max_length=2000)
    reviewer: str = "Daniel Ng"


@router.get("/queue")
def queue(status: str = "pending", db: Session = Depends(get_db)):
    q = select(ReviewItem, Run).join(Run, Run.id == ReviewItem.run_id).order_by(ReviewItem.id.desc())
    if status != "all":
        q = q.where(ReviewItem.status == status)
    return [
        {**review.review_to_dict(item), "question": run.question, "verdict": run.final_verdict,
         "first_verdict": run.original_verdict, "retried": run.retried, "user_name": run.user_name}
        for item, run in db.execute(q).all()
    ]


@router.get("/items/{item_id}")
def item_detail(item_id: int, db: Session = Depends(get_db)):
    item = db.get(ReviewItem, item_id)
    if item is None:
        raise HTTPException(404, "Review item not found")
    return {"item": review.review_to_dict(item), "run": run_to_dict(db.get(Run, item.run_id))}


@router.post("/items/{item_id}/decide")
def decide(item_id: int, body: Decision, db: Session = Depends(get_db)):
    item = db.get(ReviewItem, item_id)
    if item is None:
        raise HTTPException(404, "Review item not found")
    try:
        review.decide(db, item, body.action, body.reason, body.reviewer, body.corrected_answer)
    except review.ReviewError as e:
        raise HTTPException(400, str(e)) from e
    return {"item": review.review_to_dict(item), "run": run_to_dict(db.get(Run, item.run_id))}


@router.get("/golden")
def golden(db: Session = Depends(get_db)):
    return [
        {"id": g.id, "created_at": g.created_at.isoformat(), "question": g.question, "details": g.details,
         "correct_answer": g.correct_answer, "source_docs": g.source_docs, "review_id": g.review_id}
        for g in db.scalars(select(GoldenItem).order_by(GoldenItem.id.desc()))
    ]
