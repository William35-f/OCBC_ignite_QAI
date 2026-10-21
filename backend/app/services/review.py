"""Step 7 - the human review queue (one queue for every reason).

The queue holds Red answers, Amber answers that failed their one retry,
and answers an employee reported. A reviewer approves, corrects or rejects
each one, always with a reason. Approved and corrected answers go into the
golden set, which "Run retest" uses later.
"""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import GoldenItem, ReviewItem, Run
from app.services.audit import log_event
from app.services.knowledge_base import get_kb
from app.services.text import parse_citations

# Most serious first: used to pick the "main flag" shown in the queue table
FLAG_PRIORITY = [
    "outdated_source", "contradicted", "missing_exception", "quote_mismatch",
    "unable_to_verify", "unsupported", "partly_supported", "figure_mismatch", "no_citation",
    "citation_not_found", "conflict_older_source", "part_not_answered", "part_partly_answered",
]
DECISIONS = {"approve": "approved", "correct": "corrected", "reject": "rejected"}


class ReviewError(ValueError):
    pass


def main_flag(checks: dict | None) -> str:
    types = {f["type"] for f in (checks or {}).get("flags", [])}
    return next((t for t in FLAG_PRIORITY if t in types), "")


def enqueue(db: Session, run: Run, queue_reason: str, checks: dict | None = None) -> ReviewItem:
    """Add a run to the review queue (once per run while pending)."""
    existing = db.scalar(select(ReviewItem).where(ReviewItem.run_id == run.id, ReviewItem.status == "pending"))
    if existing:
        return existing
    item = ReviewItem(run_id=run.id, queue_reason=queue_reason, main_flag=main_flag(checks))
    db.add(item)
    db.flush()
    log_event(db, "sent_to_review", run.id, queue_reason=queue_reason, main_flag=item.main_flag)
    return item


def latest_review(db: Session, run_id: int) -> ReviewItem | None:
    return db.scalar(select(ReviewItem).where(ReviewItem.run_id == run_id).order_by(ReviewItem.id.desc()))


def source_docs_for(answer: str, run: Run) -> list[str]:
    """Which documents back a golden answer: its own citations if it has any,
    otherwise the current documents Q AI used as evidence (the newer side of
    any known conflict only)."""
    kb = get_kb()
    labels = []
    for c in parse_citations(answer):
        d = kb.doc_by_label(c.doc_label)
        if d and d.label not in labels:
            labels.append(d.label)
    if labels:
        return labels
    checks = run.retry_checks or run.original_checks or {}
    older = {c.doc_b for c in kb.conflicts}
    ids = [e["doc_id"] for s in checks.get("sentences", []) for e in s.get("evidence", [])]
    ids += [d for f in checks.get("flags", []) if f["type"] == "missing_exception" for d in f.get("doc_ids", [])]
    for doc_id in ids:
        d = kb.doc(doc_id)
        if d and d.status == "current" and d.id not in older and d.label not in labels:
            labels.append(d.label)
    return labels


def decide(db: Session, item: ReviewItem, action: str, reason: str, reviewer: str,
           corrected_answer: str = "") -> ReviewItem:
    if item.status != "pending":
        raise ReviewError("This item has already been reviewed")
    if action not in DECISIONS:
        raise ReviewError("Action must be approve, correct or reject")
    if len(reason.strip()) < 3:
        raise ReviewError("A reason is required")
    run = db.get(Run, item.run_id)
    if action == "correct":
        corrected_answer = corrected_answer.strip()
        if not corrected_answer:
            raise ReviewError("Write the corrected answer")
        if corrected_answer == (run.final_answer or "").strip():
            raise ReviewError("The correction is the same as the answer: use Approve instead")

    item.status = DECISIONS[action]
    item.reviewer = reviewer
    item.decision_reason = reason.strip()
    item.corrected_answer = corrected_answer if action == "correct" else None
    item.decided_at = datetime.now()
    log_event(db, "review_decided", run.id, actor=reviewer, decision=item.status, reason=item.decision_reason,
              corrected_answer=item.corrected_answer)

    # Approved or corrected answers become part of the golden set
    if action in ("approve", "correct"):
        answer = corrected_answer if action == "correct" else run.final_answer
        db.add(GoldenItem(
            question=run.question, details=run.details or {}, correct_answer=answer,
            source_docs=source_docs_for(answer, run), review_id=item.id,
        ))
        log_event(db, "golden_added", run.id, actor=reviewer)
    db.commit()
    return item


def review_to_dict(item: ReviewItem | None) -> dict | None:
    if item is None:
        return None
    return {
        "id": item.id,
        "run_id": item.run_id,
        "created_at": item.created_at.isoformat(),
        "queue_reason": item.queue_reason,
        "main_flag": item.main_flag,
        "status": item.status,
        "reviewer": item.reviewer,
        "corrected_answer": item.corrected_answer,
        "decision_reason": item.decision_reason,
        "decided_at": item.decided_at.isoformat() if item.decided_at else None,
    }
