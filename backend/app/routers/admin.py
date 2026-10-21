"""Admin dashboard: numbers, fix suggestions, Apply fix, Run retest, audit log, eval results."""
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.models import RetestRun
from app.services import improve

router = APIRouter(prefix="/api/admin", tags=["admin"])


class RetireRequest(BaseModel):
    doc_id: str


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    return improve.dashboard(db)


@router.get("/suggestions")
def suggestions(db: Session = Depends(get_db)):
    return improve.suggestions(db)


@router.post("/fixes/retire")
def apply_retire(body: RetireRequest, db: Session = Depends(get_db)):
    try:
        improve.retire(db, body.doc_id)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    return {"ok": True, "suggestions": improve.suggestions(db)}


@router.post("/retest")
async def retest(db: Session = Depends(get_db)):
    return improve.retest_to_dict(await improve.run_retest(db))


@router.get("/retest/latest")
def latest_retest(db: Session = Depends(get_db)):
    return improve.retest_to_dict(db.scalar(select(RetestRun).order_by(RetestRun.id.desc())))


@router.get("/activity")
def activity(db: Session = Depends(get_db)):
    return improve.activity(db)


@router.get("/eval")
def eval_results():
    """Results of the last `python -m app.eval` run (data/eval/results.json)."""
    path = settings.eval_dir / "results.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


@router.post("/eval/run")
async def run_eval_now():
    """Same as `python -m app.eval`, started from the dashboard."""
    from app.eval import run_eval

    return await run_eval()
