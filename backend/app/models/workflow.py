"""Workflow log tables: one Run per employee question, plus an event log."""
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def now() -> datetime:
    return datetime.now()


class Run(Base):
    """Everything that happened to one question, from prompt to final answer.
    The original answer is never overwritten; a retry is stored separately."""

    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)
    source: Mapped[str] = mapped_column(String, default="chat")  # chat | retest | eval
    user_name: Mapped[str] = mapped_column(String, default="Rachel Lim")

    # Step 1-2: prompt and prompt check
    question: Mapped[str] = mapped_column(Text)
    details: Mapped[dict] = mapped_column(JSON, default=dict)  # answers to follow-up chips
    prompt_check: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    topic: Mapped[str | None] = mapped_column(String, nullable=True)

    # Progress shown on the "Checking..." state
    status: Mapped[str] = mapped_column(String, default="new")  # new | needs_details | running | done | error
    stage: Mapped[str] = mapped_column(String, default="")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Step 3-5: original answer and its checks
    original_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_checks: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    original_verdict: Mapped[str | None] = mapped_column(String, nullable=True)

    # Step 5b: one retry (Amber only)
    retried: Mapped[bool] = mapped_column(Boolean, default=False)
    retry_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_checks: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    retry_verdict: Mapped[str | None] = mapped_column(String, nullable=True)

    # Outcome
    final_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_verdict: Mapped[str | None] = mapped_column(String, nullable=True)
    routed_to: Mapped[str | None] = mapped_column(String, nullable=True)  # employee | review

    # Step 6: employee action
    employee_action: Mapped[str | None] = mapped_column(String, nullable=True)  # used | reported
    report_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    employee_action_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class EventLog(Base):
    """Append-only audit trail: every step writes an event with a timestamp."""

    __tablename__ = "event_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("runs.id"), nullable=True)
    actor: Mapped[str] = mapped_column(String, default="system")
    event: Mapped[str] = mapped_column(String)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
