"""The Q AI workflow for one question (a Run).

  Step 1-2  start_run / add_details : prompt check, follow-up chips      (in the request)
  Step 3-5  process_run             : OCBC AI answers, Q AI checks it    (in the background)

The frontend polls the run to show the "Checking..." step labels.
"""
import asyncio
import logging
from datetime import datetime

from sqlalchemy.orm import Session, object_session

from app.core.config import settings
from app.core.db import SessionLocal
from app.models import Run
from app.services import ocbc_ai
from app.services.audit import log_event
from app.services.checks.runner import run_checks
from app.services.prompt_check import run_prompt_check
from app.services.review import enqueue, latest_review, review_to_dict
from app.services.self_correction import build_feedback, what_changed
from app.services.verdict import route

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

            # Step 4: checks A, B and C in parallel
            await _set_stage(db, run, "Checking rules, sources and intent")
            checks = await run_checks(answer, run.question, run.details or {}, pc.get("parts", []), run.topic)
            run.original_checks = checks
            log_event(db, "answer_checked", run.id, verdict=checks["verdict"],
                      flags=[f["type"] for f in checks["flags"]])

            # Step 5: verdict and routing
            await _set_stage(db, run, "Deciding verdict")
            run.original_verdict = checks["verdict"]
            if route(checks["verdict"], retried=False) == "retry":
                await _self_correct(db, run, answer, checks)
            else:
                _finish(db, run, answer, checks, retried=False)
            db.commit()
        except Exception as e:  # keep the error visible on the chat page
            log.exception("Run %s failed", run_id)
            db.rollback()
            run.status, run.stage, run.error = "error", "Something went wrong", str(e)[:500]
            log_event(db, "run_failed", run.id, error=run.error)
            db.commit()


async def _self_correct(db: Session, run: Run, answer: str, checks: dict) -> None:
    """Step 5b: one retry for an Amber answer, then Steps 4 and 5 again."""
    pc = run.prompt_check or {}
    feedback, flagged, _ = build_feedback(checks)
    run.retried, run.retry_feedback = True, feedback
    log_event(db, "retry_requested", run.id, flagged=flagged)

    await _set_stage(db, run, "Self-correcting: OCBC AI tries once more")
    retry, context = await ocbc_ai.generate_answer(
        db, run.question, run.details or {}, pc.get("search_query", run.question), pc.get("parts", []),
        feedback=feedback, previous_answer=answer, flagged=flagged,
    )
    run.retry_answer, run.retry_context = retry, context
    log_event(db, "ocbc_retried", run.id, answer=retry)

    await _set_stage(db, run, "Re-checking the corrected answer")
    retry_checks = await run_checks(retry, run.question, run.details or {}, pc.get("parts", []), run.topic)
    run.retry_checks, run.retry_verdict = retry_checks, retry_checks["verdict"]
    log_event(db, "retry_checked", run.id, verdict=retry_checks["verdict"],
              flags=[f["type"] for f in retry_checks["flags"]])
    _finish(db, run, retry, retry_checks, retried=True)


def _finish(db: Session, run: Run, answer: str, checks: dict, retried: bool) -> None:
    """Apply the routing rule. Q AI never edits the answer: the employee sees it as written."""
    verdict = checks["verdict"]
    where = route(verdict, retried)
    if where == "retry":  # cannot happen when retried=True: the retry limit is one
        raise RuntimeError("retry requested twice")
    run.final_answer, run.final_verdict, run.routed_to = answer, verdict, where
    if where == "review" and run.source == "chat":  # retest / eval runs never go to the queue
        reason = "red" if verdict == "Red" else "amber_after_retry"
        enqueue(db, run, reason, checks)
    run.status, run.stage = "done", "Done"
    log_event(db, "run_finished", run.id, verdict=verdict, routed_to=where)


def record_employee_action(db: Session, run: Run, action: str, reason: str = "") -> Run:
    """Step 6 buttons: "Use answer" (logged) or "Report a problem" (goes to review)."""
    run.employee_action, run.report_reason, run.employee_action_at = action, reason or None, datetime.now()
    log_event(db, f"employee_{action}", run.id, actor=run.user_name, reason=reason)
    if action == "reported":
        enqueue(db, run, "reported", run.retry_checks or run.original_checks)
    db.commit()
    return run


def run_to_dict(run: Run) -> dict:
    """What the frontend receives for one run, including any review decision."""
    db = object_session(run)
    review = review_to_dict(latest_review(db, run.id)) if db is not None else None
    return {
        "review": review,
        "report_reason": run.report_reason,
        "source": run.source,
        "user_name": run.user_name,
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
        "retry_feedback": run.retry_feedback,
        "retry_answer": run.retry_answer,
        "retry_checks": run.retry_checks,
        "retry_verdict": run.retry_verdict,
        "what_changed": what_changed(run.original_answer, run.retry_answer)
        if run.original_answer and run.retry_answer else [],
        "final_answer": run.final_answer,
        "final_verdict": run.final_verdict,
        "routed_to": run.routed_to,
        "employee_action": run.employee_action,
    }
