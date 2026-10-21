"""Human review queue and the golden set of approved answers."""
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.workflow import now


class ReviewItem(Base):
    __tablename__ = "review_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    # Why it is in the queue: red | amber_after_retry | reported
    queue_reason: Mapped[str] = mapped_column(String)
    main_flag: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String, default="pending")  # pending | approved | corrected | rejected
    reviewer: Mapped[str | None] = mapped_column(String, nullable=True)
    corrected_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class GoldenItem(Base):
    """A reviewer-approved question/answer pair, used by "Run retest"."""

    __tablename__ = "golden_set"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    question: Mapped[str] = mapped_column(Text)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    correct_answer: Mapped[str] = mapped_column(Text)
    source_docs: Mapped[list] = mapped_column(JSON, default=list)
    review_id: Mapped[int | None] = mapped_column(ForeignKey("review_items.id"), nullable=True)
