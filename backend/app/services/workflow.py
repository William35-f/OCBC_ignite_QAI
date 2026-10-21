"""The Q AI workflow for one question (a Run).

  Step 1-2  start_run / add_details : prompt check, follow-up chips      (in the request)
  Step 3-5  process_run             : OCBC AI answers, Q AI checks it    (in the background)

The frontend polls the run to show the "Checking..." step labels.
"""
import asyncio
import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.models import Run
from app.services import ocbc_ai
from app.services.audit import log_event
from app.services.prompt_check import run_prompt_check

log = logging.getLogger(__name__)


async def _set_stage(db: Session, run: Run, stage: str) -> None:
    run.stage = stage
    db.commit()
    if settings.step_delay_seconds:
        await asyncio.sleep(settings.step_delay_seconds)


async def _prompt_check(db: Session, run: Run) -> Run:
    pc = await run_prompt_check(run.question, run.details or {})
    run.prompt_check = pc
    run.topic = pc["topic"]
    run.details = pc["details_used"]
    log_event(db, "prompt_checked", run.id, **{k: pc[k] for k in ("parts", "missing_details", "search_query", "correction_notes")})
    if pc["missing_details"]:
        run.status, run.stage = "needs_details", "Waiting for your answer"
    else:
        run.status, run.stage = "running", "Queued"
    db.commit()
    return run


async def start_run(db: Session, question: str, details: dict | None = None, user_name: str = "Rachel Lim",
                    source: str = "chat") -> Run:
    """Step 1-2: save the question and run the prompt check."""
    run = Run(question=question.strip(), details=details or {}, user_name=user_name, source=source,
              status="checking_prompt", stage="Checking your question")
    db.add(run)
    db.commit()
    log_event(db, "question_asked", run.id, actor=user_name, question=run.question, details=run.details)
    return await _prompt_check(db, run)


async def add_details(db: Session, run: Run, details: dict) -> Run:
    """The employee clicked a follow-up chip: merge the answer and re-check the prompt."""
    run.details = {**(run.details or {}), **details}
    log_event(db, "details_given", run.id, actor=run.user_name, details=details)
    return await _prompt_check(db, run)


async def process_run(run_id: int) -> None:
    """Steps 3-5 for one run, in the background, with its own DB session."""
    with SessionLocal() as db:
        run = db.get(Run, run_id)
        if run is None or run.status != "running":
            return
        try:
            pc = run.prompt_check or {}
            await _set_stage(db, run, "OCBC AI is answering")
            answer, context = await ocbc_ai.generate_answer(
                db, run.question, run.details or {}, pc.get("search_query", run.question), pc.get("parts", [])
            )
            run.original_answer, run.original_context = answer, context
            log_event(db, "ocbc_answered", run.id, answer=answer,
                      retrieved=[f"{c['label']} {c['section_label']}" for c in context])

            # Steps 4-5 (checks and verdict) are added in phase 3
            run.final_answer = answer
            run.routed_to = "employee"
            run.status, run.stage = "done", "Done"
            log_event(db, "run_finished", run.id, routed_to=run.routed_to)
            db.commit()
        except Exception as e:  # keep the error visible on the chat page
            log.exception("Run %s failed", run_id)
            db.rollback()
            run.status, run.stage, run.error = "error", "Something went wrong", str(e)[:500]
            log_event(db, "run_failed", run.id, error=run.error)
            db.commit()


def run_to_dict(run: Run) -> dict:
    """What the frontend receives for one run."""
    return {
        "id": run.id,
        "created_at": run.created_at.isoformat(),
        "question": run.question,
        "details": run.details or {},
        "status": run.status,
        "stage": run.stage,
        "error": run.error,
        "prompt_check": run.prompt_check,
        "topic": run.topic,
        "original_answer": run.original_answer,
        "original_checks": run.original_checks,
        "original_verdict": run.original_verdict,
        "retried": run.retried,
        "retry_answer": run.retry_answer,
        "retry_checks": run.retry_checks,
        "retry_verdict": run.retry_verdict,
        "final_answer": run.final_answer,
        "final_verdict": run.final_verdict,
        "routed_to": run.routed_to,
        "employee_action": run.employee_action,
    }
