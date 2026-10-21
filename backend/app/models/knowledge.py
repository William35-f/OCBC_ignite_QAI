"""Knowledge base tables: documents (with retriever on/off) and known conflicts."""
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Document(Base):
    """One knowledge-base document. Content lives in the markdown file;
    this row stores metadata plus the admin-controlled retriever switch."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    version: Mapped[str] = mapped_column(String)
    topic: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)  # current | superseded
    effective_date: Mapped[str] = mapped_column(String)
    superseded_by: Mapped[str | None] = mapped_column(String, nullable=True)
    owner: Mapped[str] = mapped_column(String, default="")
    required_details: Mapped[list] = mapped_column(JSON, default=list)
    path: Mapped[str] = mapped_column(String, default="")
    # False = excluded from OCBC AI's retriever (set by the "Apply fix" button)
    retriever_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Conflict(Base):
    """A pair of documents that state different values for the same field.
    Computed once when the knowledge base is loaded."""

    __tablename__ = "conflicts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic: Mapped[str] = mapped_column(String)
    field: Mapped[str] = mapped_column(String)
    doc_a: Mapped[str] = mapped_column(String)
    value_a: Mapped[str] = mapped_column(String)
    doc_b: Mapped[str] = mapped_column(String)
    value_b: Mapped[str] = mapped_column(String)
