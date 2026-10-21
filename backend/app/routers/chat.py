"""Employee chat: ask a question, answer follow-up chips, poll the run."""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import Run
from app.schemas.workflow import AskRequest, DetailsRequest
from app.services import workflow
from app.services.demo import SCENARIOS

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _get_run(db: Session, run_id: int) -> Run:
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(404, "Run not found")
    return run


@router.get("/scenarios")
def scenarios():
    return SCENARIOS


@router.post("/ask")
async def ask(body: AskRequest, background: BackgroundTasks, db: Session = Depends(get_db)):
    run = await workflow.start_run(db, body.question, body.details)
    if run.status == "running":
        background.add_task(workflow.process_run, run.id)
    return workflow.run_to_dict(run)


@router.post("/runs/{run_id}/details")
async def give_details(run_id: int, body: DetailsRequest, background: BackgroundTasks, db: Session = Depends(get_db)):
    run = _get_run(db, run_id)
    if run.status != "needs_details":
        raise HTTPException(409, "This question is not waiting for details")
    run = await workflow.add_details(db, run, body.details)
    if run.status == "running":
        background.add_task(workflow.process_run, run.id)
    return workflow.run_to_dict(run)


@router.get("/runs/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db)):
    return workflow.run_to_dict(_get_run(db, run_id))


class ReportRequest(BaseModel):
    reason: str = Field(default="", max_length=300)


@router.post("/runs/{run_id}/use")
def use_answer(run_id: int, db: Session = Depends(get_db)):
    run = _get_run(db, run_id)
    if run.status != "done":
        raise HTTPException(409, "The answer is not ready yet")
    return workflow.run_to_dict(workflow.record_employee_action(db, run, "used"))


@router.post("/runs/{run_id}/report")
def report_problem(run_id: int, body: ReportRequest, db: Session = Depends(get_db)):
    run = _get_run(db, run_id)
    if run.status != "done":
        raise HTTPException(409, "The answer is not ready yet")
    return workflow.run_to_dict(workflow.record_employee_action(db, run, "reported", body.reason.strip()))
