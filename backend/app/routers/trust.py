"""Trust Challenge page."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.services import trust

router = APIRouter(prefix="/api/trust", tags=["trust challenge"])


class Answer(BaseModel):
    session_id: str = Field(min_length=4, max_length=64)
    round: str
    item_id: str
    choice: str  # trust | dont_trust


@router.get("/items")
async def items():
    return await trust.items()


@router.post("/answers")
def answer(body: Answer, db: Session = Depends(get_db)):
    try:
        trust.record(db, body.session_id, body.round, body.item_id, body.choice)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {"saved": True}


@router.get("/score/{session_id}")
def score(session_id: str, db: Session = Depends(get_db)):
    return trust.session_score(db, session_id)


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    return trust.summary(db)
