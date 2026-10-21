"""Record-and-improve tables: applied fixes, retests, eval results, Trust Challenge, settings."""
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.workflow import now


class FixAction(Base):
    """A fix the admin applied (e.g. retire a document). Only counts as done
    once a retest passes afterwards."""

    __tablename__ = "fix_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    kind: Mapped[str] = mapped_column(String)  # retire_document
    target: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="applied")  # applied | verified
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class RetestRun(Base):
    __tablename__ = "retest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    results: Mapped[list] = mapped_column(JSON, default=list)


class TrustResult(Base):
    """One Trust / Don't trust click in the Trust Challenge."""

    __tablename__ = "trust_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    session_id: Mapped[str] = mapped_column(String)
    round: Mapped[str] = mapped_column(String)  # A (text only) | B (with evidence)
    item_id: Mapped[str] = mapped_column(String)
    choice: Mapped[str] = mapped_column(String)  # trust | dont_trust
    correct: Mapped[bool] = mapped_column(Boolean)


class AppSetting(Base):
    """Runtime settings changed on the Settings page (key -> JSON value)."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)
