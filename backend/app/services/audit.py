"""Audit trail helper: every workflow step writes a timestamped event."""
from sqlalchemy.orm import Session

from app.models import EventLog


def log_event(db: Session, event: str, run_id: int | None = None, actor: str = "system", **data) -> None:
    db.add(EventLog(run_id=run_id, actor=actor, event=event, data=data))
