"""Step 7 - the human review queue (one queue for every reason)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ReviewItem, Run
from app.services.audit import log_event

# Most serious first: used to pick the "main flag" shown in the queue table
FLAG_PRIORITY = [
    "outdated_source", "contradicted", "missing_exception", "quote_mismatch",
    "unable_to_verify", "unsupported", "partly_supported", "figure_mismatch", "no_citation",
    "citation_not_found", "conflict_older_source", "part_not_answered", "part_partly_answered",
]


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
